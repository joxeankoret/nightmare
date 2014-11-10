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
import zipfile
import tempfile

from melkor_mutator import main as melkor_replace

#-----------------------------------------------------------------------
class CMultipleMelkorMutator:
  def __init__(self, samples_path, total, output_zip):
    self.samples_path = samples_path
    self.total = total
    self.output_zip = output_zip

  def mutate(self):
    with zipfile.ZipFile(self.output_zip, "w") as fuzz_zip:
      fuzz_zip.comment = "NIGHTMARE"
      for i in range(self.total):
        name = tempfile.mktemp()
        while 1:
          template = random.choice(os.listdir(self.samples_path))
          template = os.path.join(self.samples_path, template)
          if os.path.isfile(template):
            break
          continue
        
        melkor_replace(template, name)
        try:
          fuzz_zip.write(name)
          
          # Add also the .diff file if it was created:
          if os.path.exists(name + ".diff"):
            fuzz_zip.write(name + ".diff")
            os.remove(name + ".diff")
          os.remove(name)
        except:
          print "Error:", sys.exc_info()[1]

#-----------------------------------------------------------------------
def main(path, number, output):
  mutator = CMultipleMelkorMutator(path, int(number), output)
  mutator.mutate()

#-----------------------------------------------------------------------
def usage():
  print "Usage:", sys.argv[0], "samples_path #samples output_zip"

if __name__ == "__main__":
  if len(sys.argv) != 4:
    usage()
  else:
    main(sys.argv[1], sys.argv[2], sys.argv[3])
