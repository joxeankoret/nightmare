#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Nightmare Fuzzing Project
This mutator creates an intelligently mutated MachO file
@author: joxean
"""

import os
import sys
import random

from macholib.MachO import MachO

#-----------------------------------------------------------------------
RANDOM_STRS = [chr(c) for c in range(0, 255)]
def get_random_str():
  size = random.randint(0, 16384)
  return random.choice(RANDOM_STRS * size)

#-----------------------------------------------------------------------
def get_random_value(t):
  if str(t) == "<class 'macholib.ptypes.p_uint32'>":
    return random.randint(0, 0xFFFFFFFF)
  elif str(t) == "<class 'macholib.ptypes.p_int32'>":
    return random.randint(-2147483648, 2147483647)
  elif str(t) == "<class 'macholib.ptypes.p_uint64'>":
    return random.randint(0, 0xFFFFFFFFFFFFFFFF)
  elif str(t) == "<class 'macholib.ptypes.p_int64'>":
    return random.randint(-9223372036854775808, 9223372036854775808)
  elif str(t) == "<class 'macholib.ptypes.p_str16'>":
    return repr(get_random_str())
  else:
    raise Exception("Unknown type %s" % str(t))

#-----------------------------------------------------------------------
SUPPORTED_FIELD_TYPES = ["<class 'macholib.ptypes.p_uint32'>",
                         "<class 'macholib.ptypes.p_int32'>",
                         "<class 'macholib.ptypes.p_uint64'>",
                         "<class 'macholib.ptypes.p_int64'>"]
BANNED_FIELDS = ["magic"]

#-----------------------------------------------------------------------
class CMachoFuzzer:
  def __init__(self):
    self.macho = None
    self.fuzz_properties = ["headers"]
    self.fuzz_sub_properties = {"headers":["header", "commands", "headers"]}
    
    self.changes = []
    self.change_list = []

  def do_fuzz_headers(self):
    # Select a random header
    header = random.choice(self.macho.headers)
    idx = self.macho.headers.index(header)
    self.changes.append(["Header %d" % idx])
    prop = random.choice(self.fuzz_sub_properties["headers"])

    if prop == "header":
      fields = random.choice(header.header._fields_)
      field = fields[0]
      
      change_name = "header %d field %s" % (idx, field)
      if change_name in self.change_list or field in BANNED_FIELDS:
        #print "Ignoring already applied change %s" % change_name
        del self.changes[len(self.changes)-1]
        return

      self.changes[len(self.changes)-1].append("Field %s" % field)
      l = "header.header.%s = %d" % (field, get_random_value(fields[1]))
      exec(l)
      
      self.change_list.append(change_name)
    elif prop == "commands":
      cmd = random.choice(header.commands)
      idx = header.commands.index(cmd)
      self.changes[len(self.changes)-1].append("Command %d" % idx)
      
      subidx = random.randint(0, len(cmd)-1)
      subcmd = cmd[subidx]

      if '_fields_' in dir(subcmd):
        if len(subcmd._fields_) > 0:
          fields = random.choice(subcmd._fields_)
          field = fields[0]
          self.changes[len(self.changes)-1].append("Field %s" % field)
          str_type = str(type(eval("subcmd.%s" % field)))
          if str_type in SUPPORTED_FIELD_TYPES:
            l = "subcmd.%s = " % field
            l += str(get_random_value(fields[1]))
            exec(l)
          else:
            #print "Ignoring unsupported field type", str_type, field
            del self.changes[len(self.changes)-1]
        else:
          print "Ignoring empty subcmd", subcmd
          del self.changes[len(self.changes)-1]
      elif type(subcmd) is str:
        #print "Ignoring unsupported (by macholib) string sub-command"
        del self.changes[len(self.changes)-1]
      else:
        print type(subcmd), subcmd
        if type(subcmd) is list and len(subcmd) > 0:
          field = random.choice(subcmd)
          subidx = subcmd.index(field)
          self.changes[len(self.changes)-1].append("List element %d" % subcmd.index(field))

          fields = random.choice(field._fields_)
          field_name = fields[0]
          self.changes[len(self.changes)-1].append("Field %s" % field_name)

          l = "field.%s = " % field_name
          l += str(get_random_value(fields[1]))
          exec(l)
        else:
          del self.changes[len(self.changes)-1]
      #self.changes[len(self.changes)-1].append("Sub-command %d" % sub_idx)
    elif prop == "headers":
      del self.changes[len(self.changes)-1]
      #print "Not yet supported headers"
      #raise Exception("Implement headers")
    else:
      del self.changes[len(self.changes)-1]

  def do_fuzz_internal(self):
    assert(self.macho is not None)
    
    element = random.choice(self.fuzz_properties)
    if element == "headers":
      self.do_fuzz_headers()
    else:
      raise Exception("Unknown element to fuzz %s" % repr(element))

  def fuzz(self, filename, output_filename):
    self.macho = MachO(filename)

    changes = random.randint(1, 25)
    for i in range(changes*5):
      self.do_fuzz_internal()
      if len(self.change_list) == changes:
        break

    # Copy the contents of the original file to the output file
    f = open(output_filename, "wb+")
    f.write(open(filename, "rb").read())
    f.close()

    # Update it's contents
    f = open(output_filename, "rb+")
    self.macho.write(f)
    f.close()

    # And write the .diff file
    f = open(output_filename + ".diff", "wb")
    f.write("# Original file created by 'MachO Mutator' was %s\n" % filename)
    for change in self.changes:
      print "# CHANGE: %s" % ", ".join(change)
      f.write("# CHANGE: %s\n" % ", ".join(change))
    f.close()
    
    os.system("radiff2 %s %s" % (filename, output_filename))

#-----------------------------------------------------------------------
def usage():
  print "Usage:", sys.argv[0], "<input file> <output file>"

#-----------------------------------------------------------------------
def main(input_file, output_file):
  fuzzer = CMachoFuzzer()
  fuzzer.fuzz(input_file, output_file)

if __name__ == "__main__":
  if len(sys.argv) != 3:
    usage()
  else:
    main(sys.argv[1], sys.argv[2])

