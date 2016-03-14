#!/usr/bin/python

import re
import sys

from cStringIO import StringIO

#-----------------------------------------------------------------------
class CAsanParser:
  def __init__(self):
    self.reset()

  def reset(self):
    self.reason = None
    self.pc = None
    self.bp = None
    self.sp = None
    self.stack_trace = []
    self.additional = []

  def extract_reason(self, line):
    pattern = "ERROR: AddressSanitizer: (.*) on (unknown address|address) (0x[a-f0-9]+).*(pc) (0x[a-f0-9]+).*(bp|sp) (0x[a-f0-9]+).*(bp|sp) (0x[a-f0-9]+)"
    ret = re.findall(pattern, line, re.IGNORECASE)
    if len(ret) > 0:
      ret = ret[0]

      self.reason = ret[0]
      self.address = ret[2]
      self.pc = ret[4]
      if ret[5] == "bp":
        self.bp = ret[6]
      else:
        self.sp = ret[6]

      if ret[7] == "sp":
        self.sp = ret[8]
      else:
        self.bp = ret[8]

      if self.reason in ["SEGV", "ABRT"]:
        self.reason = "SIG%s" % self.reason

      self.pc = int(self.pc, 16)
      self.bp = int(self.bp, 16)
      self.sp = int(self.sp, 16)

  def add_to_stack_trace(self, line):
    pattern = "#\d+ (0x[a-f0-9]+)( in | )(.*)"
    ret = re.findall(pattern, line, re.IGNORECASE)
    if len(ret) > 0:
      ret = ret[0]
      self.stack_trace.append([int(ret[0], 16), ret[2]])

  def add_stack_separator(self, line):
    self.stack_trace.append([0xFFFFFFFF, line])

  def add_summary(self, line):
    self.additional.append(line)

  def parse(self, lines):
    new_stack = False
    summary = False

    for line in lines:
      line = line.strip("\n").strip("\r")

      if line == "":
        if len(self.stack_trace) > 0:
          new_stack = True
        continue

      if line.startswith("=="):
        if line.find("ERROR: AddressSanitizer:") > -1:
          if self.reason is not None:
            raise "Crash reason already known!"
          self.extract_reason(line)
      elif line.find("SUMMARY: AddressSanitizer: ") > -1:
        summary = True
        self.add_summary(line)
        continue
      elif summary:
        self.add_summary(line)
        continue
      elif new_stack:
        new_stack = False
        self.add_stack_separator(line)
        continue

      if self.reason is not None:
        if line.startswith("    #"):
          self.add_to_stack_trace(line)

  def parse_file(self, filename):
    lines = open(filename, "rb").readlines()
    return self.parse(lines)

  def parse_buffer(self, buf):
    sio = StringIO(buf)
    return self.parse(sio.readlines())

#-----------------------------------------------------------------------
def usage():
  print "Usage:", sys.argv[0], "<asan report>"

#-----------------------------------------------------------------------
def main(filename):
  parser = CAsanParser()
  parser.parse_file(filename)
  
  import pprint
  print "STACK TRACE(s)"
  pprint.pprint(parser.stack_trace)
  print "SUMMARY"
  pprint.pprint(parser.additional)

if __name__ == "__main__":
  if len(sys.argv) == 1:
    usage()
  else:
    main(sys.argv[1])
