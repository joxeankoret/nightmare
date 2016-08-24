#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
GDB debugging interface for Nightmare Fuzzing Project
Created on 2015
@author: joxean
"""

import os
import re
import sys
import time

from tempfile import mkstemp

dir_name = os.path.dirname(os.path.realpath(__file__))
sys.path.append(os.path.join(dir_name, ".."))
sys.path.append(os.path.join(dir_name, "../lib"))
sys.path.append(os.path.join(dir_name, "../../runtime"))

from crash_data import CCrashData
from nfp_process import TimeoutCommand

#-----------------------------------------------------------------------
# Default timeout
timeout = 10

buf = None

#-----------------------------------------------------------------------
class CGDBInterface(object):
  def __init__(self, program, gdb_commands = None):
    global dir_name
    global timeout

    self.buf = None
    self.program = program
    if gdb_commands is None:
      self.gdb_commands = os.path.join(dir_name, "commands.gdb")
    else:
      self.gdb_commands = gdb_commands

    if os.getenv("NIGHTMARE_TIMEOUT"):
      timeout = float(os.getenv("NIGHTMARE_TIMEOUT"))
    self.timeout = timeout

    self.pc = None
    self.stack = []
    self.signal = None
    self.disasm = None
    self.disasm_around = []
    self.registers = {}
    self.exploitability_reason = None
    self.exploitability = None

  def read_signal(self, line):
    pos1 = len("Program received signal ")
    pos2 = line.find(",")
    if pos2 > -1:
      signal = line[pos1:pos2]
      print "Received signal %s\n" % signal
      self.signal = signal

  def parse_pc(self, pc):
    addr = pc.split(" ")[1]
    
    addr_pos = addr.find(":")
    if addr_pos > -1:
      addr = addr[:addr_pos]

    pos = pc.find(":\t")
    disasm = None

    if pos > -1:
      disasm = pc[pos+2:]
      disasm = disasm.strip(" ").strip("\n").strip("\n")

    try:
      self.pc = addr
      self.pc = int(self.pc, 16)
    except:
      pass

    self.disasm = disasm

  def parse_registers(self, regs):
    for line in regs:
      data = re.findall("(\w+)\W+(.*)\\t", line)
      if not data:
        continue
      
      data = data[0]
      reg = data[0]

      try:
        addr = int(data[1], 16)
      except:
        addr = data[1]
        raise

      self.registers[reg] = addr

  def parse_stack(self, stack):
    pc = True
    for line in stack:
      line = line.strip("\r").strip("\n")
      l = line.split(" ")
      l = l[1:]
      
      for i in range(5):
        if l[i] == "":
          continue
        break

      if not pc:
        try:
          addr = l[i]
          addr = int(addr, 16)
        except:
          pass
      else:
        addr = self.pc
        pc = False

      func = " ".join(l[i+1:])
      self.stack.append([addr, func])

  def parse_disasm(self, disasm):
    for line in disasm:
      pc_crash = False
      if line.startswith("=> "):
        pc_crash = True
        line = line.replace("=> ", "   ")

      ret = re.findall("(\w+) (.*)", line)

      if ret:
        ret = ret[0]
        try:
          addr = ret[0]
          addr = int(addr, 16)
        except:
          pass
        
        data = ret[1]
        self.disasm_around.append([addr, data])

  def set_exploitability(self, exploitability, exploitability_desc):
    self.exploitability = exploitability
    self.exploitability_reason = exploitability_desc

  def parse_dump(self, lines):
    found_crash_start = False
    if len(lines) <= 8:
      return

    for i in range(len(lines)):
      line = lines[i]
      line = line.strip("\r").strip("\n")

      # Ignore various informative messages like thread switching
      if line.startswith("["):
        continue

      # The 1st thing we need to find is the signal message
      if self.signal is None:
        if line.startswith("Program received signal"):
          self.read_signal(line)
        continue

      # Skip until the following message is found
      if line == "@@@START-OF-CRASH":
        found_crash_start = True
        continue

      if found_crash_start:
        if line == "@@@PROGRAM-COUNTER":
          pc = lines[i+1]
          self.parse_pc(pc)
          # Skip the line with the $PC information
          i += 1
        elif line.startswith("@@@EXPLOITABLE"):
          i += 1
          exploitability = None
          exploitability_desc = None
          # Get all the lines with registers data
          while i < len(lines):
            line = lines[i]
            line = line.strip("\r").strip("\n")

            if line.startswith("Description:"):
              exploitability_desc = line[len("Description:")+1:]
            elif line.startswith("Exploitability Classification:"):
              exploitability = line[len("Exploitability Classification:")+1:]

            i += 1
            if line.startswith("@@@"):
              break
          print
          # And fill the internal dictionary with the register values
          self.set_exploitability(exploitability, exploitability_desc)
        elif line.startswith("@@@REGISTERS"):
          i += 1
          regs = []
          # Get all the lines with registers data
          while i < len(lines):
            line = lines[i]
            line = line.strip("\r").strip("\n")

            i += 1
            if line.startswith("@@@"):
              break
            print line
            regs.append(line)
          print
          # And fill the internal dictionary with the register values
          self.parse_registers(regs)
        elif line.startswith("@@@START-OF-STACK-TRACE"):
          i += 1
          stack = []
          # Get all the lines with registers data
          j = 0
          while i < len(lines):
            line = lines[i]
            line = line.strip("\r").strip("\n")

            i += 1
            if line.startswith("@@@END-OF-STACK-TRACE"):
              i += 1
              break
            
            j += 1
            if j <= 5:
              print line
            stack.append(line)

          print
          self.parse_stack(stack)
          continue
        elif line.startswith("@@@START-OF-DISASSEMBLY-AT-PC"):
          i += 1
          disasm = []
          # Get all the disassembly lines
          while i < len(lines):
            line = lines[i]
            line = line.strip("\r").strip("\n")

            i += 1
            if line.startswith("@@@END-OF-DISASSEMBLY-AT-PC"):
              i += 1
              break
            print line
            disasm.append(line)
          self.parse_disasm(disasm)
          continue
        elif line.startswith("@@@END-OF-CRASH"):
          # Finished!
          break

  def run(self):
    global buf

    os.putenv("LANG", "C")
    
    logfile = mkstemp()[1]
    try:
      cmd = '/bin/bash -c "/usr/bin/gdb -q --batch --command=%s --args %s" 2>/dev/null > %s'
      cmd %= (self.gdb_commands, self.program, logfile)
      print cmd
      print "Running %s" % cmd

      cmd_obj = TimeoutCommand(cmd)
      cmd_obj.shell = True
      cmd_obj.run(self.timeout)
      
      buf = open(logfile, "rb").readlines()
      self.parse_dump(buf)

      if self.signal:
        crash_data = CCrashData(self.pc, self.signal)
        i = 0
        for stack in self.stack:
          crash_data.add_data("stack trace", "%d" % i, stack)
          i += 1

        for reg in self.registers:
          crash_data.add_data("registers", reg, self.registers[reg])

        crash_data.add_data("disassembly", int(self.pc), self.disasm)
        for dis in self.disasm_around:
          if type(dis[0]) in (int,long) or dis[0].isdigit():
            crash_data.add_data("disassembly", dis[0], dis[1])
        crash_data.disasm = [self.pc, self.disasm]
        
        if self.exploitability is not None:
          crash_data.exploitable = self.exploitability
        
        if self.exploitability_reason is not None:
          crash_data.add_data("exploitability", "reason", self.exploitability_reason)

        crash_data_buf = crash_data.dump_json()
        crash_data_dict = crash_data.dump_dict()

        print
        print "Yep, we got a crash! \o/"
        print

        return crash_data_dict

      return
    finally:
      os.remove(logfile)

#-----------------------------------------------------------------------
def main(args, gdb_commands=None):
  if args[0] in ["--attach", "-A"]:
    raise Exception("GDB interface doesn't support attaching")
  else:
    prog = args
    if type(args) is list:
      prog = " ".join(args)

  iface = CGDBInterface(prog, gdb_commands=gdb_commands)
  return iface.run()

#-----------------------------------------------------------------------
def usage():
  print "Usage:", sys.argv[0], "<program> <file>"

if __name__ == "__main__":
  if len(sys.argv) == 1:
    usage()
  else:
    main(sys.argv[1:])
