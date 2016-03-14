#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
ASAN sanitizer based "debugging" interface for Nightmare Fuzzing Project
Created on 2016
@author: joxean
"""

import os
import re
import sys
import time

from asan_parser import CAsanParser

dir_name = os.path.dirname(os.path.realpath(__file__))
sys.path.append(os.path.join(dir_name, ".."))
sys.path.append(os.path.join(dir_name, "../lib"))
sys.path.append(os.path.join(dir_name, "../../runtime"))

from crash_data import CCrashData
from nfp_process import TimeoutCommand

#-----------------------------------------------------------------------
# Default timeout
timeout = 10

#-----------------------------------------------------------------------
class CAsanInterface(object):
  def __init__(self, program, asan_symbolizer_path):
    global timeout

    self.program = program
    self.asan_symbolizer_path = asan_symbolizer_path

    if os.getenv("NIGHTMARE_TIMEOUT"):
      timeout = float(os.getenv("NIGHTMARE_TIMEOUT"))

    self.timeout = timeout
    self.asan = CAsanParser()

  def run(self):
    os.putenv("LANG", "C")
    os.putenv("ASAN_SYMBOLIZER_PATH", self.asan_symbolizer_path)

    cmd = self.program
    print "Running %s" % cmd

    cmd_obj = TimeoutCommand(cmd)
    cmd_obj.run(self.timeout, get_output=True)

    buf = cmd_obj.stderr
    self.asan.parse_buffer(buf)

    if self.asan.reason is not None:
      crash_data = CCrashData(self.asan.pc, self.asan.reason)
      i = 0
      for line in self.asan.stack_trace:
        crash_data.add_data("stack trace", "%d" % i, (line[0], line[1]))
        i += 1

      crash_data.add_data("registers", "pc", self.asan.pc)
      crash_data.add_data("registers", "bp", self.asan.bp)
      crash_data.add_data("registers", "sp", self.asan.sp)

      crash_data.add_data("disassembly", int(self.asan.pc), "")
      j = 0
      for line in self.asan.additional:
        crash_data.add_data("information", j, line)
        j += 1
      crash_data.disasm = [self.asan.pc, ""]

      if not self.asan.reason.startswith("SIG"):
        crash_data.exploitable = "EXPLOITABLE"
      else:
        crash_data.exploitable = "UNKNOWN"

      crash_data.add_data("exploitability", "reason", self.asan.reason)

      crash_data_buf = crash_data.dump_json()
      crash_data_dict = crash_data.dump_dict()

      line = "Program received %s at PC 0x%x SP 0x%x BP 0x%x"
      print line % (self.asan.reason, self.asan.pc, self.asan.sp, self.asan.bp)
      print
      for i, line in enumerate(self.asan.stack_trace):
        if i > 10:
          break
        print "0x%08x %s" % (line[0], line[1])

      print
      print "Yep, we got a crash! \o/"
      print

      return crash_data_dict

    return

#-----------------------------------------------------------------------
def main(asan_symbolizer_path, args):
  prog = args
  if type(args) is list:
    prog = " ".join(args)

  iface = CAsanInterface(prog, asan_symbolizer_path=asan_symbolizer_path)
  return iface.run()

#-----------------------------------------------------------------------
def usage():
  print "Usage:", sys.argv[0], "<program> <file>"

if __name__ == "__main__":
  if len(sys.argv) < 3:
    usage()
  else:
    main(sys.argv[1], sys.argv[2:])
