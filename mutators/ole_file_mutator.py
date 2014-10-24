#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Nightmare Fuzzing Project
@author: joxean
"""

import os
import sys
import shutil
import random
import tempfile

from hashlib import md5
from subprocess import check_output

import OleFileIO_PL

#-----------------------------------------------------------------------
class COleFileIOReplacer:
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

  def mutate_data(self, data):
    filename = tempfile.mktemp()
    
    try:
      with open(filename, "wb") as f:
        f.write(data)
      
      new_buf = check_output(["radamsa", filename])
    except:
      print "*** Error getting output from radamsa?", sys.exc_info()[1]
      os.remove(filename)
    finally:
      os.remove(filename)

    if len(new_buf) < len(data):
      diff = len(data)-len(new_buf)
      new_buf += data[len(data)-diff:]
    elif len(new_buf) > len(data):
      new_buf = new_buf[:len(data)]
    return new_buf

  def replace(self, output):
    # Create a copy of the input file, we need it because of how the 
    # library OleFileIO_PL works
    shutil.copyfile(self.input, output)

    # Open the OLE2 document and select a random stream
    ole = OleFileIO_PL.OleFileIO(output, write_mode=True)
    dirs = ole.listdir()

    # Select a number of directories to mutate
    dones = []
    for i in xrange(random.randint(1, len(dirs))):
      # Select a random dir to modify ensuring we're not modifying the
      # same one again and again... Allow only 1 change per execution to
      # each directory
      random_dir = random.choice(ole.listdir())
      if random_dir in dones:
        continue

      dones.append(random_dir)
      data = ole.openstream(random_dir).read()

      # Get the newly mutated data
      new_data = self.mutate_data(data)

      # Write the new stream data
      ole.write_stream(random_dir, new_data)

    # Close the modified OLE document
    ole.close()

    # Lazy (but likely the best) way to generate the differences file
    diff = self.get_diff(open(self.input, "rb").read(), open(output, "rb").read())

    # And, finaly, write the .diff file too
    f = open(output + ".diff", "wb")
    f.write("# Original file created by 'OLE file mutator' was %s\n" % self.input)
    f.write("\n".join(diff))
    f.close()

#-----------------------------------------------------------------------
def main(input_file, output_file):
  replacer = COleFileIOReplacer(input_file)
  replacer.replace(output_file)

#-----------------------------------------------------------------------
def usage():
  print "Usage:", sys.argv[0], "<input file> <output file>"

if __name__ == "__main__":
  if len(sys.argv) != 3:
    usage()
  else:
    main(sys.argv[1], sys.argv[2])

