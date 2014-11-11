#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Nightmare Fuzzing Project generic fuzzer
Generic application fuzzer
@author: joxean
"""

import os
import sys
import json
import base64
import tempfile
import ConfigParser

from multiprocessing import Process, cpu_count

sys.path.append("../")
sys.path.append("../runtime")

import config

from nfp_log import log, debug
from nfp_queue import get_queue
from nfp_process import process_manager
from lib.interfaces import vtrace_iface

#-----------------------------------------------------------------------
class CGenericFuzzer:
  def __init__(self, cfg, section):
    self.cfg = cfg
    self.section = section
    self.read_configuration()
  
    self.q = get_queue(name=self.tube_name, watch=True)
    self.delete_q = get_queue(name="delete", watch=False)
    self.crash_q = get_queue(name=self.crash_tube, watch=False)

    self.crash_info = None

  def read_configuration(self):
    if not os.path.exists(self.cfg):
      raise Exception("Invalid configuration file given")

    parser = ConfigParser.SafeConfigParser()
    parser.optionxform = str
    parser.read(self.cfg)

    if self.section not in parser.sections():
      raise Exception("Section %s does not exists in the given configuration file" % self.section)
    
    try:
      self.pre_command = parser.get(self.section, 'pre-command')
    except:
      # Ignore it, it isn't mandatory
      self.pre_command = None

    try:
      self.post_command = parser.get(self.section, 'post-command')
    except:
      # Ignore it, it isn't mandatory
      self.post_command = None

    try:
      self.command = parser.get(self.section, 'command')
    except:
      raise Exception("No command specified in the configuration file for section %s" % self.section)
    
    try:
      self.tube_name = parser.get(self.section, 'tube')
    except:
      raise
      raise Exception("No tube specified in the configuration file for section %s" % self.section)

    try:
      self.crash_tube = parser.get(self.section, 'crash-tube')
    except:
      self.crash_tube = "%s-crash" % self.tube_name
    
    try:
      self.extension = parser.get(self.section, 'extension')
    except:
      raise Exception("No extension specified in the configuration file for section %s" % self.section)
    
    try:
      self.timeout = parser.get(self.section, 'timeout')
    except:
      # Default timeout is 90 seconds
      self.timeout = 90
    
    try:
      environment = parser.get(self.section, 'environment')
      self.env = dict(parser.items(environment))
    except:
      self.env = {}
    
    try:
      self.cleanup = parser.get(self.section, 'cleanup-command')
    except:
      self.cleanup = None
    
    try:
      is_debug = parser.getboolean(self.section, 'debug')
      config.DEBUG = is_debug
    except:
      # Silently ignore the exception
      pass

  def launch_debugger(self, timeout, command, filename):
    log("Launching debugger with command %s" % " ".join([command, filename]))
    vtrace_iface.timeout = int(timeout)
    crash = vtrace_iface.main([command, filename])
    return crash

  def launch_sample(self, buf):
    # Re-read configuration each time we're running the fuzzer so the 
    # new changes are immediately applied.
    self.read_configuration()

    filename = tempfile.mktemp(suffix=self.extension)
    f = open(filename, "wb")
    f.write(buf)
    f.close()

    #os.putenv("NIGHTMARE_TIMEOUT", str(self.timeout))
    for key in self.env:
      debug("Setting environment variable %s=%s" % (key, self.env[key]))
      os.putenv(key, self.env[key])

    if self.pre_command is not None:
      os.system(self.pre_command)

    crash = None
    for i in range(0,3):
      try:
        crash = self.launch_debugger(self.timeout, self.command, filename)
        break
      except:
        log("Exception: %s" % sys.exc_info()[1])
        continue

    if self.post_command is not None:
      os.system(self.post_command)

    if crash is not None:
      self.crash_info = crash
      return True
    else:
      os.remove(filename)
    return False

  def fuzz(self):
    log("Launching fuzzer, listening in tube %s" % self.tube_name)
    while 1:
      value = self.q.stats_tube(self.tube_name)["current-jobs-ready"]
      debug("Total of %d job(s) in queue" % value)
      job = self.q.reserve()
      buf, temp_file = json.loads(job.body)
      buf = base64.b64decode(buf)

      debug("Launching sample %s..." % os.path.basename(temp_file))
      if self.launch_sample(buf):
        log("We have a crash, moving to %s queue..." % self.crash_tube)
        crash = self.crash_info
        d = {temp_file:self.crash_info}
        self.crash_q.put(json.dumps(d))
        self.crash_info = None

        log("$PC 0x%08x Signal %s Exploitable %s " % (crash["pc"], crash["signal"], crash["exploitable"]))
        if crash["disasm"] is not None:
          log("%08x: %s" % (crash["disasm"][0], crash["disasm"][1]))
      else:
        file_delete = os.path.basename(temp_file)
        self.delete_q.put(str(file_delete))
      
      if self.cleanup is not None:
        debug("Running clean-up command %s" % self.cleanup)
        os.system(self.cleanup)
        debug("Done")
      job.delete()

#-----------------------------------------------------------------------
def do_fuzz(cfg, section):
  try:
    fuzzer = CGenericFuzzer(cfg, section)
    fuzzer.fuzz()
  except KeyboardInterrupt:
    log("Aborted")
  except:
    log("Error: %s" % str(sys.exc_info()[1]))

#-----------------------------------------------------------------------
def main(cfg, section):
  procs = os.getenv("NIGHTMARE_PROCESSES")
  if procs is not None:
    process_manager(int(procs), do_fuzz, (cfg, section))
  else:
    try:
      fuzzer = CGenericFuzzer(cfg, section)
      fuzzer.fuzz()
    except:
      print "Error:", sys.exc_info()[1]

#-----------------------------------------------------------------------
def usage():
  print "Usage:", sys.argv[0], "<config file> <fuzzer>"
  print
  print "Environment variables:"
  print "NIGHTMARE_PROCESSES     Number of processes to run at the same time"
  print

if __name__ == "__main__":
  if len(sys.argv) != 3:
    usage()
  else:
    main(sys.argv[1], sys.argv[2])

