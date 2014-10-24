#-----------------------------------------------------------------------
# IDAPython crash analysis script for Nightmare Fuzzing Project
# Joxean Koret

import sys
from idaapi import *
from idautils import *

#-----------------------------------------------------------------------
REGISTERS_LIST = ["RAX", "RBX", "RCX", "RDX", "RSI", "RDI", "RBP",
                  "RSP", "RIP", "R8", "R9", "R10", "R11", "R12", "R13",
                  "R14", "R15", "EFL"]

#-----------------------------------------------------------------------
# class to take a copy of a segment_t
class Seg():
  def __init__(self, s):
    self.startEA = s.startEA
    self.endEA   = s.endEA
    self.perm  = s.perm
    self.bitness = s.bitness
  def __cmp__(self, other):
    return cmp(self.startEA, other.startEA)

#-----------------------------------------------------------------------
# each item described as:
# [ delta, [ opcode(s) ] ]
#FF10       call    d,[eax]
#FF5000       call    d,[eax][0]
#FF9044332211   call    d,[eax][011223344]
#FF1500000100   call    d,[000010000]
#FF9300000000   call    d,[ebx][0]
#FF10       call    d,[eax]
call_pattern = \
[
  [-2, [0xFF] ],
  [-3, [0xFF] ],
  [-5, [0xE8] ],
  [-6, [0xFF] ],
]

#-----------------------------------------------------------------------
def is_prev_insn_call(ea):
  """
  Given a return address, this function tries to check if previous
  instruction is a CALL instruction.
  """
  global call_pattern
  if ea == idaapi.BADADDR or ea < 10:
    return None

  for delta, opcodes in call_pattern:
    # assume caller's ea
    caller = ea + delta
    # get the bytes
    bytes = [x for x in GetDataList(caller, len(opcodes), 1)]
    # do we have a match? is it a call instruction?
    if bytes == opcodes and idaapi.is_call_insn(caller):
      return caller
  return None

#-----------------------------------------------------------------------
class Result:
  """
  Class holding the result of one call stack item
  Each call stack item instance has the following attributes:
    caller = ea of caller
    displ  = display string
    sp   = stack pointer
  """
  def __init__(self, caller, sp):
    self.caller = caller
    self.sp   = sp
    f = idaapi.get_func(caller)
    self.displ = "%08x: " % caller
    if f:
      self.displ += idc.GetFunctionName(caller)
      t = caller - f.startEA
      if t > 0: self.displ += "+" + hex(t)
    else:
      self.displ += hex(caller)
    self.displ += " [" + hex(sp) + "]"
    self.displ += " %s" % SegName(caller)

  def __str__(self):
    return self.displ

#-----------------------------------------------------------------------
def call_stack_walk(nn):
  # maybe this is the problem?
  PauseProcess()

  # get stack pointer
  sp = GetRegValue("RSP")
  print "sp 0x%016x" % sp
  seg = idaapi.getseg(sp)
  print seg
  if not seg:
    return (False, "Could not locate stack segment!")

  stack_seg = Seg(seg)
  word_size = 2 ** (seg.bitness + 1)
  callers = []
  sp = GetRegValue("RSP") - word_size
  while sp < stack_seg.endEA:
    sp += word_size
    ptr = GetDataList(sp, 1, word_size).next()
    seg = idaapi.getseg(ptr)
    # only accept executable segments
    if (not seg) or ((seg.perm & idaapi.SEGPERM_EXEC) == 0):
      continue
    # try to find caller
    caller = is_prev_insn_call(ptr)
    # we have no recognized caller, skip!
    if caller is None:
      continue

    # do we have a debug name that is near?
    if nn:
      ret = nn.find(caller)
      if ret:
        ea = ret[0]
        # function exists?
        f = idaapi.get_func(ea)
        if not f:
          # create function
          idc.MakeFunction(ea, idaapi.BADADDR)

    # get the flags
    f = idc.GetFlags(caller)
    # no code there?
    if not isCode(f):
      MakeCode(caller)

    callers.append(Result(caller, sp))
  #
  return (True, callers)

#-----------------------------------------------------------------------
def dump_data():
  crash_name = os.getenv("NFP_INFO_CRASH")
  if crash_name is None:
    crash_name = "info.crash"
  f = open(crash_name, "wb")
  print >>f, "Exception: pid=%d tid=%d ea=0x%x exc_code=0x%x exc_ea=0x%x exc_info=%s" % (
      GetEventPid(), GetEventTid(), GetEventEa(), GetEventExceptionCode() & idaapi.BADADDR,
      GetEventExceptionEa(), GetEventExceptionInfo())
  print >>f
  print >>f, "Disassembly"
  #print >>f, GetDisasm(ea)
  start_ea = GetEventEa()
  curr_ea = (start_ea - 32) & 0xFFFFFFFFFFFFFFF0
  MakeCode(curr_ea)
  while curr_ea < start_ea + 32:
    line = "%s:%08x %s" % (SegName(curr_ea), curr_ea, GetDisasm(curr_ea))
    if curr_ea == GetEventEa():
      line += "\t<--- CRASH"
    print >>f, line
    curr_ea += ItemSize(curr_ea)
  print >>f
  for reg in REGISTERS_LIST:
    print reg
    try:
      addr = GetRegValue(reg)
      line = "%s 0x%016x" % (reg, addr)
      buf = GetManyBytes(addr, 32)
      if buf:
        line = "%s\t%s" % (line, repr(buf))
      print >>f, line
    except:
      print >>f, "ERROR?", sys.exc_info()[1]

  print >>f
  print >>f, "Stack trace"
  # get all debug names
  dn = idaapi.get_debug_names(idaapi.cvar.inf.minEA, idaapi.cvar.inf.maxEA)
  # initiate a nearest name search (using debug names)
  nn = idaapi.NearestName(dn)
  ret, callstack = call_stack_walk(nn)
  if ret:
    for x in callstack:
      print >>f, x
      print x
    print >>f
  else:
    print >>f, callstack
  idaapi.qexit(0)

def main():
  while 1:
    event = GetDebuggerEvent(WFNE_SUSP|WFNE_CONT, 10)
    if event == EXCEPTION:
      dump_data()
      break
    elif event == TIMEOUT:
      print "Timeout"
      break
  idaapi.qexit(0)

if __name__ == "__main__":
  main()
