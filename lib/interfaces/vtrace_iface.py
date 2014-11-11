#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Debugger interface using VTrace for Nightmare Fuzzing Project.
Created on Sat May 11 17:56:06 2013
@author: joxean
"""

import os
import sys
import base64
import threading
from capstone import *

sys.path.append("../")
sys.path.append("../lib")
sys.path.append("../lib/interfaces")

from crash_data import CCrashData

from vtrace import vtrace

# Default timeout
timeout = 90

#-----------------------------------------------------------------------
# Constants and tables
signal_name_table = {
  1: "SIGHUP",
  2: "SIGINT",
  3: "SIGQUIT",
  4: "SIGILL",
  6: "SIGABRT",
  8: "SIGFPE",
  9: "SIGKILL",
  10: "SIGUSR1",
  11: "SIGSEGV",
  12: "SIGUSR2",
  13: "SIGPIPE",
  14: "SIGALRM",
  15: "SIGTERM",
  16: "SIGUSR1",
  21: "SIGTTIN",
  22: "SIGTTOU",
  23: "SIGSTOP",
  24: "SIGTSTP",
  25: "SIGCONT",
  26: "SIGTTIN",
  27: "SIGTTOU",
  30: "SIGUSR1",
  31: "SIGUSR2"}

NOT_EXPLOITABLE = 0
EXPLOITABLE = 1
MAYBE_EXPLOITABLE = 2

#-----------------------------------------------------------------------
def signal_to_name(signal):
  """Convert a signal number to its string representation.

  Keyword arguments:
  signal -- number of the signal as returned by wait
  """

  if signal_name_table.has_key(signal):
    return signal_name_table[signal]
  return "Unknown"

#-----------------------------------------------------------------------
def get_permision_str(val):
  ret = ""
  if val & 4: # read
    ret += "r"
  else:
    ret += "-"
  if val & 2: # write
    ret += "w"
  else:
    ret += "-"
  if val & 1: # exec
    ret += "x"
  else:
    ret += "-"
  return ret

#-----------------------------------------------------------------------
def is_exploitable(val):
  if val == NOT_EXPLOITABLE:
    return "Unknown"
  elif val == EXPLOITABLE:
    return "Exploitable"
  elif val == MAYBE_EXPLOITABLE:
    return "Probably exploitable"

#-----------------------------------------------------------------------
def win32_exc_to_name(val):
  if val == 0xc0000005:
    return "ACCESS_VIOLATION"
  elif val == 0x0:
    return "READ_VIOLATION"
  elif val == 0x1:
    return "WRITE_VIOLATION"
  elif val == 0xc0000094:
    return "EXCEPTION_INT_DIVIDE_BY_ZERO"
  elif val == 0xc0000096:
    return "EXCEPTION_PRIV_INSTRUCTION"
  elif val == 0xc000001d:
    return "EXCEPTION_ILLEGAL_INSTRUCTION"
  else:
    return "Unknown"

#-----------------------------------------------------------------------
def kill_process(tr, kill=True):
  try:
    if kill:
      tr.kill()
    else:
      tr.detach()
  except:
    pass

#-----------------------------------------------------------------------
def sig2name(sig):
  if os.name == "nt":
    return win32_exc_to_name(sig)
  else:
    return signal_to_name(sig)

#-----------------------------------------------------------------------
COMMON_REGS = ["rax", "rbx", "rcx", "rdx", "rsi", "rdi", "rbp", "rsp", "rip"]

#-----------------------------------------------------------------------
def main(args):
  crash_data_dict = None
  tr = vtrace.getTrace()
  
  global timeout
  if os.getenv("NIGHTMARE_TIMEOUT"):
    timeout = float(os.getenv("NIGHTMARE_TIMEOUT"))

  if args[0] in ["--attach", "-A"]:
    if len(args) == 1:
      usage()
      sys.exit(1)
    else:
      pid = int(args[1])
      # Schedule a timer to detach from the process after some seconds
      timer = threading.Timer(timeout, kill_process, (tr, False, ))
      timer.start()
      tr.attach(pid)
  else:    
    # Schedule a timer to kill the process after 5 seconds
    timer = threading.Timer(timeout, kill_process, (tr, True, ))
    timer.start()
    tr.execute(" ".join(args))
    tr.run()

  signal = tr.getCurrentSignal()
  signal_name = signal_to_name(signal)
  ignore_list = ["Unknown", "SIGUSR1", "SIGUSR2", "SIGTTIN", "SIGPIPE", "SIGINT"]
  while signal is None or signal_name in ignore_list:
    signal = tr.getCurrentSignal()
    signal_name = signal_to_name(signal)
    try:
      tr.run()
    except:
      break

  timer.cancel()
  # Don't do anything else, the process is gone
  if os.name != "nt" and not tr.attached:
    return None

  if signal is not None:
    print tr, hex(signal)
    print " ".join(sys.argv)
    crash_name = os.getenv("NFP_INFO_CRASH")

    # Create the object to store all the crash data
    crash_data = CCrashData(tr.getProgramCounter(), sig2name(signal))
    if crash_name is None:
      crash_name = "info.crash"
    #f = open(crash_name, "wb")

    exploitability_reason = None
    if os.name != "nt" and signal == 4:
      # Due to illegal instruction
      exploitable = EXPLOITABLE
      exploitability_reason = "Illegal instruction"
    elif os.name == "nt" and signal in [0xc0000096, 0xc000001d]:
      # Due to illegal or privileged instruction
      exploitable = EXPLOITABLE
      if signal == 0xc000001d:
        exploitability_reason = "Illegal instruction"
      else:
        exploitability_reason = "Privileged instruction"
    else:
      exploitable = NOT_EXPLOITABLE

    crash_data.add_data("process", "pid", tr.getPid())
    if os.name == "nt":
      print "Process %d crashed with exception 0x%x (%s)" % (tr.getPid(), signal, win32_exc_to_name(signal))
    else:
      print "Process %d crashed with signal %d (%s)" % (tr.getPid(), signal, signal_to_name(signal))

    i = 0
    for t in tr.getThreads():
      i += 1
      crash_data.add_data("threads", "%d" % i, t)

    stack_trace = tr.getStackTrace()
    total = len(stack_trace)
    i = 0
    for x in stack_trace:
      i += 1
      sym = tr.getSymByAddr(x[0], exact=False)
      if sym is None:
        sym = ""
      
      crash_data.add_data("stack trace", "%d" % i, [x[0], str(sym)])
      total -= 1

    regs = tr.getRegisterContext().getRegisters()
    for reg in regs:
      crash_data.add_data("registers", reg, regs[reg])
      if reg.startswith("r"):
        line = reg.ljust(5) + "%016x" % regs[reg]
        try:
          mem = tr.readMemory(regs[reg], 32)
          mem = base64.b64encode(mem)
          crash_data.add_data("registers memory", reg, mem)
          line += "\t" + repr(mem)
        except:
          pass

    for reg in COMMON_REGS:
      if reg in regs:
        if reg in crash_data.data["registers memory"]:
          print reg, hex(regs[reg]), repr(base64.b64decode(crash_data.data["registers memory"][reg]))
        else:
          print reg, hex(regs[reg])
    print

    total_around = 40
    if 'rip' in regs or 'rsp' in regs or 'rbp' in regs:
      if len("%08x" % regs['rip']) > 8 or len("%08x" % regs['rsp']) > 8 or len("%08x" % regs['rbp']) > 8:
        mode = CS_MODE_64
      else:
        mode = CS_MODE_32
    else:
      mode = CS_MODE_32

    md = Cs(CS_ARCH_X86, mode)
    md.skipdata = True
    pc = tr.getProgramCounter()
    crash_mnem = None
    crash_ops = None
    try:
      pc_mem = tr.readMemory(pc-total_around/2, total_around)
      offset = regs["rip"]-total_around/2

      ret = []
      found = False
      for x in md.disasm(pc_mem, 0):
        line = "%016x %s %s" % ((offset + x.address), x.mnemonic, x.op_str)
        crash_data.add_data("disassembly", offset + x.address, "%s %s" %(x.mnemonic, x.op_str))
        if offset + x.address == pc:
          crash_data.disasm = [x.address + offset, "%s %s" %(x.mnemonic, x.op_str)]
          line += "\t\t<--------- CRASH"
          print line
          found = True
        ret.append(line)

      if not found:
        offset = pc = tr.getProgramCounter()
        pc_mem = tr.readMemory(pc, total_around)
        for x in md.disasm(pc_mem, 0):
          line = "%016x %s %s" % ((offset + x.address), x.mnemonic, x.op_str)
          if offset + x.address == pc:
            line += "\t\t<--------- CRASH"
            crash_data.disasm = [x.address + offset, "%s %s" % (x.mnemonic, x.op_str)]
          print line
    except:
      # Due to invalid memory at $PC
      if signal != 6:
        exploitable = True
        exploitability_reason = "Invalid memory at program counter"
      print "Exception:", sys.exc_info()[1]

    if crash_mnem:
      if crash_mnem in ["call", "jmp"] or \
         crash_mnem.startswith("jmp") or \
         crash_mnem.startswith("call"):
        if crash_ops.find("[") > -1:
          # Due to jump/call with a register that maybe controllable
          exploitable = EXPLOITABLE
          exploitability_reason = "Jump or call with a probably controllable register"
      elif crash_mnem.startswith(".byte"):
        # Due to illegal instruction
        exploitable = MAYBE_EXPLOITABLE
        exploitability_reason = "Illegal instruction"
      elif crash_mnem.startswith("in") or \
           crash_mnem.startswith("out") or \
           crash_mnem in ["hlt", "iret", "clts", "lgdt", "lidt",
                                     "lldt", "lmsw", "ltr", "cli", "sti"]:
        if crash_mnem != "int":
          # Due to privileged instruction (which makes no sense in user-land)
          exploitable = MAYBE_EXPLOITABLE
          exploitability_reason = "Privileged instruction"

    #print >>f
    #print >>f, "Maps:"
    i = 0
    for m in tr.getMemoryMaps():
      i += 1
      line = "%016x %s %s %s" % (m[0], str(m[1]).rjust(8), get_permision_str(m[2]), m[3])
      crash_data.add_data("memory maps", "%d" % i, m)
      #print >>f, line

    #print >>f
    if exploitable > 0:
      crash_data.exploitable = is_exploitable(exploitable)
      crash_data.add_data("exploitability", "reason", exploitability_reason)
      #print >>f, "Exploitable: %s. %s." % (is_exploitable(exploitable), exploitability_reason)
    else:
      #print >>f, "Exploitable: Unknown."
      pass

    crash_data_buf = crash_data.dump_json()
    crash_data_dict = crash_data.dump_dict()
    print "Yep, we got a crash! \o/"
    print
    #print "Dumping JSON...."
    #print crash_data_buf
    #print 

  if tr.attached:
    try:
      tr.kill()
    except:
      pass
  try:
    tr.release()
  except:
    pass

  return crash_data_dict

def usage():
  print "Usage:", sys.argv[0], "<arguments>"

if __name__ == "__main__":
  if len(sys.argv) == 1:
    usage()
  else:
    main(sys.argv[1:])
