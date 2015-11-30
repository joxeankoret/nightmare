#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Crashing data, part of the Nightmare Fuzzing Project.
@author: joxean
"""

import json

#-----------------------------------------------------------------------
class CCrashData:
  """ Class used to store all the relevant crash information. """
  def __init__(self, pc, signal="Unknown", exploitable="Unknown",
               disasm=None):
    self.pc = pc
    self.signal = signal
    self.exploitable = exploitable
    self.disasm = disasm
    self.data = {}
    self.version = "2"

  def add_data(self, category, key, value):
    """ As all the crash data is relative to the target program, target
        operating system, etc... and this is information will largely
        differ between targets, we need to add a way to add distinct
        information. """
    try:
      self.data[category][key] = value
    except KeyError:
      self.data[category] = {key:value}

  def dump_dict(self):
    return {"pc": self.pc,
             "signal": self.signal,
             "exploitable": self.exploitable,
             "disasm": self.disasm,
             "additional": self.data,
             "version": self.version}

  def dump_json(self):
    return json.dumps(self.dump_dict())
  
  def dump(self, format):
    if self.format == "json":
      return self.dump_json()
    elif self.format == "dict":
      return self.dump_dict()
    elif self.format == "string":
      return str(self.dump_dict())
    raise Exception("Unsupported format")

#-----------------------------------------------------------------------
def main():	
	return 0

if __name__ == '__main__':
	main()
