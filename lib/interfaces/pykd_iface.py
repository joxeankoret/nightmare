#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Windbg debugging interface for Nightmare Fuzzing Project (using pykd)
Created on December 2015
@author: joxean
"""

import re
import os
import sys
import time

import pykd
import psutil

from _winreg import *
from threading import Thread, Timer

dir_name = os.path.dirname(os.path.realpath(__file__))
sys.path.append(os.path.join(dir_name, ".."))
sys.path.append(os.path.join(dir_name, "../lib"))
sys.path.append(os.path.join(dir_name, "../../runtime"))

from nfp_log import log
from crash_data import CCrashData

#-------------------------------------------------------------------------------
PYKD2 = 'pykd_0_2_x'
PYKD3 = 'pykd_0_3_x'

#-------------------------------------------------------------------------------
class ExceptionHandler(pykd.eventHandler):
  def __init__(self):
    pykd.eventHandler.__init__(self)
    self.count = 0
    self.exception_occurred = False
    self.interesting_exceptions = {0x80000001: "GUARD_PAGE_VIOLATION",
                                   0x80000005: "BUFFER_OVERFLOW",
                                   0xC0000005: "ACCESS_VIOLATION",
                                   0xC000001D: "ILLEGAL_INSTRUCTION",
                                   0xC0000144: "UNHANDLED_EXCEPTION",
                                   0xC0000409: "STACK_BUFFER_OVERRUN",
                                   0xC0000602: "UNKNOWN_EXCEPTION",
                                   0xC00000FD: "STACK_OVERFLOW",
                                   0XC000009D: "PRIVILEGED_INSTRUCTION"}
    self.exception_info = None
    self.crash_data = None

  def is_first_chance(self, exceptInfo):
    exc_code = self.get_exception_code(exceptInfo)
    if exc_code in self.interesting_exceptions.keys():
      return False

    if 'FirstChance' in dir(exceptInfo):
      ret = exceptInfo.FirstChance
    else:
      ret = exceptInfo.firstChance
    return ret

  def get_exception_code(self, ei):
    if 'ExceptionCode' in dir(ei):
      return ei.ExceptionCode
    else:
      return ei.exceptionCode

  def onException(self, exceptInfo):
    if not self.is_first_chance(exceptInfo):
      exc_code = self.get_exception_code(exceptInfo)
      if exc_code in self.interesting_exceptions:
        exc_msg = self.interesting_exceptions[exc_code]
      else:
        exc_msg = "Exception 0x%08x" % exc_code

      self.exception_info = (exc_code, exc_msg, exceptInfo)
      self.exception_occurred = True
      return pykd.eventResult.Break
    return pykd.eventResult.NoChange

#-------------------------------------------------------------------------------
class CWinDbgInterface(object):
  def __init__(self, program, timeout, mode=32, windbg_path=None, exploitable_path=None):
    reload(pykd)
    self.id = None
    self.mode = mode
    self.program = program
    self.exploitable_path = None
    self.windbg_path = windbg_path
    self.exploitable_path = exploitable_path

    try:
      self.handler = ExceptionHandler()
    except:
      self.handler = None
    self.minidump_path = None
    #self.minidump_path = r"C:\minidumps\\"

    if windbg_path is None:
      self.resolve_windbg_path()

    self.regs = {}
    self.stack = []
    self.pc_register = None
    self.disassembly = None
    self.exploitability = "Unknown"
    
    self.do_stop = False
    self.timer = None

    if str(timeout).lower() == "auto":
      self.timeout = timeout
    else:
      self.timeout = int(timeout)
    
    self.pykd_version = self.get_pykd_version()

  def resolve_windbg_path(self):
    try:
      reg = ConnectRegistry(None,HKEY_LOCAL_MACHINE)
      key = OpenKey(reg, r"SOFTWARE\Microsoft\Microsoft SDKs\Windows")
      if key:
        for i in range(QueryInfoKey(key)[0]):
          value = EnumKey(key, i)
          if value:
            full_key = r"SOFTWARE\Microsoft\Microsoft SDKs\Windows\\" + value
            key2 = OpenKey(reg, full_key)
            if key2:
              name = QueryValueEx(key2, "ProductName")
              name = name[0]
              if name and name.startswith("Microsoft Windows SDK for Windows"):
                vals = QueryValueEx(key2, "InstallationFolder")
                val = vals[0]
                if val is not None:
                  log("Found installation path at %s" % val)
                  self.windbg_path = val
                  break
              CloseKey(key2)
      CloseKey(key)
    except WindowsError:
      print "Cannot resolve Windows SDKs path:", sys.exc_info()[1]
      print "Did you install Windows SDKs for Windows?"
    except:
      print "Cannot resolve Windows SDKs path:", sys.exc_info()[1]

  def parse_registers(self, regs):
    ret = re.findall("([a-z]{1}[a-z0-9]{1,})=([a-f0-9]+)", regs)
    tmp_regs = []
    for reg in ret:
      reg, val = reg
      self.regs[reg] = val
      tmp_regs.append([reg, val])

    if "rip" in self.regs:
      self.pc = int(self.regs["rip"], 16)
      self.pc_register = "rip"
    elif "eip" in self.regs:
      self.pc = int(self.regs["eip"], 16)
      self.pc_register = "eip"
    elif "pc" in self.regs:
      self.pc = int(self.regs["pc"], 16)
      self.pc_register = "pc"
    else:
      raise Exception("Cannot find the program counter register!")

    # Create the CCrashData object and fill registers and disassembly
    # data
    self.crash_data = CCrashData(self.pc, self.signal)

    # Extract the disassembly line from the "r" command
    lines = regs.split("\n")
    last_line = lines[len(lines)-2]
    dis = re.findall("[a-z0-9]{1,} [a-z0-9]{2,} (.*)", last_line)
    self.disasm = None
    if dis is not None and len(dis) > 0:
      self.disasm = dis[0].strip(" ")

    # ...and add it to the CCrashData object
    self.crash_data.disasm = [self.pc, self.disasm]

    # Add the registers in the order shown by WinDbg
    for reg in tmp_regs:
      reg, val = reg
      self.crash_data.add_data("registers", reg, int(val, 16))

  def parse_stack(self, stack):
    lines = stack.split("\n")
    i = 0
    for line in lines:
      fields = re.findall("([a-f0-9]+) ([a-f0-9]+) (.*)", line)
      if len(fields) > 0:
        addr, func = fields[0][1], fields[0][2]
        if addr.strip("-") == "":
          addr = "FFFFFFFF"
          if self.mode == 64:
            addr += addr
          addr = "0x%s" % addr
        self.stack.append([addr, func])
        self.crash_data.add_data("stack trace", "%d" %i, [int(addr, 16), func])
        i += 1

  def disasm_around(self):
    try:
      lines = pykd.dbgCommand("u %s-c L12" % self.pc_register)
      for line in lines.split("\n"):
        tmp = re.findall("([a-f0-9]{1,}) ([a-f0-9]{2,}) (.*)", line)
        if len(tmp) > 0:
          line = tmp[0]

          addr = line[0]
          dis = line[2]
          self.crash_data.add_data("disassembly", int(addr, 16), dis)
    except:
      log("Error in disasm_around: %s" % str(sys.exc_info()[1]))

  def create_crash_data(self, regs, stack, exploitable):
    regs = regs.replace("`", "")
    stack = stack.replace("`", "")

    self.signal = self.handler.exception_info[1]
    self.parse_registers(regs)
    self.parse_stack(stack)
    self.parse_exploitable(exploitable)
    self.disasm_around()
  
  def parse_exploitable(self, exploitable):
    self.exploitability = "Unknown"
    if exploitable is not None:
      s = "Exploitability Classification: "
      l = exploitable.split("\n")
      for line in l:
        pos = line.find(s)
        if pos > -1:
          self.exploitability = line[pos+len(s):]
          self.crash_data.exploitable = self.exploitability
          break
      
      last_line = l[len(l)-2]
      self.exploitability_reason = last_line
      self.crash_data.add_data("exploitability", "reason", \
                               self.exploitability_reason)

  def timeout_func(self):
    log("Timeout (%d seconds), killing the target..." % self.timeout)
    self.do_stop = True
    try:
      pykd.breakin()
    except:
      # A race condition might happen in the timeout function and in 
      # such cases we must ignore the error.
      pass

  def check_cpu(self):
    while True:
      try:
        if self.pid is None:
          time.sleep(0.2)
          continue

        proc = psutil.Process(self.pid)
        if proc is None:
          break

        cpu = 0
        l = []
        for x in xrange(20):
          tmp = int(proc.cpu_percent(interval=0.1))
          cpu += tmp
          l.append(tmp)

        if cpu is not None and (cpu <= 100 or l.count(0) > 10):
          log("CPU at 0%, killing")
          self.do_stop = True
          pykd.breakin()
          break
        else:
          time.sleep(0.5)
      except psutil.NoSuchProcess:
        self.do_stop = True
        break

  def get_pykd_version(self):
    """  
    Gets the pykd version number 2 or 3.
    Returns: pykd version number
    """
    version = pykd.version  
    version_number = int(version.replace(',', '.').replace(' ', '').split('.')[1])  
    if version_number == 3:  
      return PYKD3
    elif version_number == 2:  
      return PYKD2
    return None

  def get_pid(self):
    if self.pykd_version == PYKD3:
      return pykd.getProcessSystemID()
    return pykd.getCurrentProcessId()

  def start_process(self):
    if not "ProcessDebugOptions" in dir(pykd):
      self.id = pykd.startProcess(self.program, debugChildren=True)
    else:
      self.id = pykd.startProcess(self.program, pykd.ProcessDebugOptions.DebugChildren)
    return self.id

  def run(self):
    self.do_stop = False
    try:
      self.id = self.start_process()
      self.pid = self.get_pid()
    except:
      log("Error launching process! %s" % str(sys.exc_info()[1]))
      return None

    if self.handler is None:
      self.handler = ExceptionHandler()

    if self.timeout is not None:
      if str(self.timeout).lower() == "auto":
        self.thread = Thread(target=self.check_cpu)
        self.thread.start()
      else:
        self.timer = Timer(self.timeout, self.timeout_func)
        self.timer.start()

    while not self.handler.exception_occurred and not self.do_stop:
      try:
        pykd.go()
      except:
        break

    if self.do_stop:
      try:
        pykd.dbgCommand(".kill")
      except:
        log("Exception killing target: %s" % str(sys.exc_info()[1]))
      return None

    if self.timer is not None:
      self.timer.cancel()

    ret = None
    if self.handler.exception_occurred:
      try:
        pykd.breakin()
        pykd.breakin()
      except:
        pass

      tmp = pykd.dbgCommand("k 1")
      if tmp.find("Wow64NotifyDebugger") > -1:
        pykd.dbgCommand(".effmach x86")

      registers = pykd.dbgCommand("r")
      stack_trace = pykd.dbgCommand("k")

      exploitable = None
      msec_path = None
      if self.exploitable_path is None:
        if self.mode == 32:
          msec_path = os.path.join(self.windbg_path, r"Debuggers\x86\winext")
        elif self.mode == 64:
          msec_path = os.path.join(self.windbg_path, r"Debuggers\x64\winext")
        elif self.mode == "arm":
          msec_path = os.path.join(self.windbg_path, r"Debuggers\arm\winext")
        else:
          raise Exception("Unknown mode %s, known ones are 32, 64 or 'arm'." % self.mode)
      else:
        msec_path = self.exploitable_path

      if msec_path is not None:
        full_msec_path = os.path.join(msec_path, r"msec.dll")
        if os.path.exists(full_msec_path):
          try:
            msec_handle = pykd.loadExt(full_msec_path)
            commandOutput = pykd.callExt(msec_handle, "exploitable", "")
            exploitable = commandOutput
          except:
            log("Error loading extension: " + str(sys.exc_info()[1]))

      try:
        if self.minidump_path is not None:
          pykd.dbgCommand(r".dump /m /u %s\\" % self.minidump_path)
          log("*** Minidump written at %s" % self.minidump_path)
      except:
        log("!!! Error saving minidump:" + str(sys.exc_info()[1]))

      ret = self.create_crash_data(registers, stack_trace, exploitable)
      
      print pykd.dbgCommand("k 10")
      print pykd.dbgCommand("r")
      print exploitable
      try:
        pykd.killAllProcesses()
      except:
        log("Error killing processes: " + str(sys.exc_info()[1]))

      crash_data_buf = self.crash_data.dump_json()
      ret = self.crash_data.dump_dict()

      print
      print "Yep, we got a crash! \o/"
      print

    return ret

#-------------------------------------------------------------------------------
def main(args, timeout, mode=32, windbg_path=None, exploitable_path=None):
  prog = " ".join(args)
  iface = CWinDbgInterface(prog, timeout, mode=mode, windbg_path=windbg_path, exploitable_path=exploitable_path)
  if exploitable_path is not None:
    iface.exploitable_path = exploitable_path
  return iface.run()

#-------------------------------------------------------------------------------
def usage():
  print "Usage:", sys.argv[0], "<program> <file>"

if __name__ == "__main__":
  if len(sys.argv) == 1:
    usage()
  else:
    main(sys.argv[1:])
