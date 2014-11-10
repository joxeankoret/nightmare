#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Nightmare Fuzzing Project
@author: joxean
"""

import os
import sys

from shutil import rmtree
from tempfile import mkdtemp

#-----------------------------------------------------------------------
class CMelkorMutator:
  def __init__(self, input):
    self.input = input

  def get_diff(self, inbuf, outbuf):
    ret = []
    b1 = bytearray(inbuf)
    b2 = bytearray(outbuf)
    for i in range(len(inbuf)):
      if b1[i] != b2[i]:
        ret.append(str(i))
    return ret

  def read_directory(self, tmpdir):
    base_file = os.path.basename(self.input)
    base_dir = os.path.join(tmpdir, "orcs_%s" % base_file)
    filename = os.path.join(base_dir, "Report_%s.txt" % base_file)
    additional = open(filename, "rb").readlines()
    
    filename = os.path.join(base_dir, "orc_0001")
    return open(filename, "rb").read(), additional

  def replace(self, output):
    tmpdir = mkdtemp()
    try:
      old_dir = os.getcwd()
      os.chdir(tmpdir)
      os.system("melkor -a -q -n 1 %s" % self.input)
      os.chdir(old_dir)

      new_buf, additional = self.read_directory(tmpdir)
      diff = self.get_diff(open(self.input, "rb").read(), new_buf)

      # And, finally, write the output file
      f = open(output, "wb")
      f.write(new_buf)
      f.close()

      # ...and the .diff file too
      f = open(output + ".diff", "wb")
      f.write("# Original file created by 'Melkor Mutator' was %s\n" % self.input)
      f.write("\n".join(diff))
      f.write("\n")
      for line in additional:
        line = line.strip("\r").strip("\n")
        f.write("# %s\n" % line)
      f.close()
    except:
      print "Exception: %s" % sys.exc_info()[1]
    finally:
      rmtree(tmpdir)

#-----------------------------------------------------------------------
def main(input_file, output_file):
  replacer = CMelkorMutator(input_file)
  replacer.replace(output_file)

#-----------------------------------------------------------------------
def usage():
  print "Usage:", sys.argv[0], "<input file> <output file>"

if __name__ == "__main__":
  if len(sys.argv) != 3:
    usage()
  else:
    main(sys.argv[1], sys.argv[2])

