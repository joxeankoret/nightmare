#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Nightmare Fuzzing Project
@author: joxean
"""

import os
import sys

from hashlib import md5

from random import randint
from subprocess import check_output

#-----------------------------------------------------------------------
class CZzufReplacer:
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

  def replace(self, output):
    # Mutate it with a random seed for zzuf
    seed = randint(0, 0xFFFFFFFF)
    new_buf = check_output(["zzuf", "-s", str(seed), "cat", self.input])

    diff = self.get_diff(open(self.input, "rb").read(), new_buf)

    # And, finally, write the output file
    f = open(output, "wb")
    f.write(new_buf)
    f.close()

    # ...and the .diff file too
    f = open(output + ".diff", "wb")
    f.write("# Original file created by 'Zzuf Mutator' was %s\n" % self.input)
    f.write("\n".join(diff))
    f.close()

#-----------------------------------------------------------------------
def main(input_file, output_file):
  replacer = CZzufReplacer(input_file)
  replacer.replace(output_file)

#-----------------------------------------------------------------------
def usage():
  print "Usage:", sys.argv[0], "<input file> <output file>"

if __name__ == "__main__":
  if len(sys.argv) != 3:
    usage()
  else:
    main(sys.argv[1], sys.argv[2])

