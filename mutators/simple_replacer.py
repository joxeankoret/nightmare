#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Nightmare Fuzzing Project
This mutator creates a ZIP file with various mutated files inside.
@author: joxean
"""

import os
import sys
import random

#-----------------------------------------------------------------------
class CSimpleReplacer:
  def __init__(self, input):
    self.input = input
  
  def replace(self, output):
    buf = open(self.input, "rb").read()

    # Randomly select a character to replace
    char = chr(random.randint(0, 255))

    # Randomly select a place to replace skipping a possible header of
    # 20 bytes.
    if len(buf) > 20:
      place = random.randint(20, len(buf))
    else:
      place = random.randint(0, len(buf))
    
    # Randomly select the maximum size to replace from a maximum of 256
    # bytes
    size = random.randint(1, 256)

    # And, finally, write the output file
    new_buf = buf[:place] + char*size + buf[place+size:]
    f = open(output, "wb")
    f.write(new_buf)
    f.close()

    # ...and the .diff file too
    f = open(output + ".diff", "wb")
    f.write("# Original file created by 'Simple Replace Mutator' was %s\n" % self.input)
    f.write("%d,%d" % (place, size))
    f.close()

#-----------------------------------------------------------------------
def main(input_file, output_file):
  replacer = CSimpleReplacer(input_file)
  replacer.replace(output_file)

#-----------------------------------------------------------------------
def usage():
  print "Usage:", sys.argv[0], "<input file> <output file>"

if __name__ == "__main__":
  if len(sys.argv) != 3:
    usage()
  else:
    main(sys.argv[1], sys.argv[2])

