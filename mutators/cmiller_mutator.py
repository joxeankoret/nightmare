#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
Random mutator based on C. Miller 'algorithm' for Nightmare Fuzzing Project.
Pure python implementation compilleable with shedskin.
Created on Sun May 12 10:57:06 2013
@author: joxean

@notes: Can somebody explain to me how the algorithm is any different to
the algorithm used by zzuf? Instead of randomly flipping bits it changes
bytes, right? Anyway, I'll maintain the "cmiller" name...
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
    buf = bytearray(self.buf)
    fuzz_factor = 10 # 0.1% of the file
    # Original:
    numwrites = random.randrange(math.ceil((float(len(buf)) / fuzz_factor))+1)

    #print "Total of %d" % numwrites
    diff = []
    for j in range(numwrites):
      rbyte = random.randrange(256)
      rn = random.randrange(len(buf))
      buf[rn] = "%c" % rbyte
      diff.append(rn)
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
  f.write("# Original file created by 'CMiller Mutator' was %s\n" % template)
  f.write("\n".join(map(str,diff))) 
  f.close()

#-----------------------------------------------------------------------
def usage():
  print "Usage:", sys.argv[0], "<template> <output filename>"

if __name__ == "__main__":
  if len(sys.argv) != 3:
    usage()
  else:
    main(sys.argv[1], sys.argv[2])
