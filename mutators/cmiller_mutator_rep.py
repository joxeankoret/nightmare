#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Random mutator based on C. Miller 'algorithm' for Nightmare Fuzzing Project.
Created on Sun May 12 10:57:06 2013
@author: joxean
"""

import sys
import math
import random

#-----------------------------------------------------------------------
class CCMillerMutator(object):
  def __init__(self, buf, skip=5):
    self.buf = buf
    self.skip = 5

  def mutate(self):
    buf = self.buf
    fuzz_factor = len(buf)/500.
    if fuzz_factor < 1:
      fuzz_factor = 1
    numwrites = random.randrange(math.ceil((float(len(buf)) / fuzz_factor)))+1
    #print "Total of %d" % numwrites
    diff = []
    for j in range(numwrites):
      rbyte = random.randrange(256)
      rn = random.randrange(len(buf))
      rtotal = random.randint(0, 16)
      c = "%c" % rbyte
      buf = buf[:rn-1] + c*rtotal + buf[rn+rtotal:]
      diff.append("%d, %d" % (rn, rtotal))
    return buf, diff

#-----------------------------------------------------------------------
def main(template, output):
  mut = CCMillerMutator(open(template, "rb").read())
  buf, diff = mut.mutate()

  f = open(output, "wb")
  f.write(buf)
  f.close()

  diff.sort()  
  f = open(output + ".diff", "wb")
  f.write("# Original file created by 'CMiller Mutator Rep' was %s\n" % template)
  f.write("\n".join(diff))
  f.close()

#-----------------------------------------------------------------------
def usage():
  print "Usage:", sys.argv[0], "<template> <output filename>"

if __name__ == "__main__":
  if len(sys.argv) != 3:
    usage()
  else:
    main(sys.argv[1], sys.argv[2])
