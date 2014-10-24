#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
Nightmare Fuzzing Project generic client/server fuzzer

Generic client/server fuzzer. It handles all the logic to start server
processes, debug them, restart them and launching clients against it.

@author: joxean
"""

import os
import sys
import time
import json
import base64
import tempfile
import ConfigParser

from multiprocessing import Process, Queue

sys.path.append("../")
sys.path.append("../runtime")

import config

from nfp_log import log, debug
from generic_fuzzer import CGenericFuzzer

#-----------------------------------------------------------------------
class CClientServerFuzzer(CGenericFuzzer):
  def __init__(self, cfg, section):
    CGenericFuzzer.__init__(self, cfg, section)

    self.client_command = None
    self.server_uid = 0
    self.server_gid = 0
    self.client_uid  = 1000
    self.client_gid = 1000
    
    # This is the server process
    self.p = None
    self.crash_info = None
    self.shared_queue = None

  def read_configuration(self):
    CGenericFuzzer.read_configuration(self)

    parser = ConfigParser.SafeConfigParser()
    parser.optionxform = str
    parser.read(self.cfg)

    try:
      self.client_command = parser.get(self.section, 'client-command')
    except:
      raise Exception("No client command specified in the configuration file for section %s" % self.section)

    try:
      self.server_uid = parser.get(self.section, 'server-uid')
    except:
      raise Exception("No server UID specified in the configuration file for section %s" % self.section)

    try:
      self.server_gid = parser.get(self.section, 'server-gid')
    except:
      raise Exception("No server GID specified in the configuration file for section %s" % self.section)

    try:
      self.client_uid = parser.get(self.section, 'client-uid')
    except:
      raise Exception("No client UID specified in the configuration file for section %s" % self.section)

    try:
      self.client_gid = parser.get(self.section, 'client-gid')
    except:
      raise Exception("No client GID specified in the configuration file for section %s" % self.section)

  def debug_server(self, shared_queue):
    self.read_configuration()

    uid = int(self.server_uid)
    if os.getuid() != uid:
      os.setresuid(uid, uid, uid)

    gid = int(self.server_gid)
    if os.getgid() != gid:
      os.setresgid(gid, gid, gid)

    for key in self.env:
      debug("Setting environment variable %s=%s" % (key, self.env[key]))
      os.putenv(key, self.env[key])

    if self.pre_command is not None:
      os.system(self.pre_command)

    crash = None
    for i in range(0,3):
      try:
        crash = self.launch_debugger(self.timeout, self.command, "")
        print "SERVER", 1
        break
      except:
        log("Exception: %s" % sys.exc_info()[1])
        raise
        continue

    print "SERVER", 2
    if self.post_command is not None:
      os.system(self.post_command)

    print "SERVER", 3, crash
    if crash is not None:
      print "SERVER, CRASH", crash
      self.crash_info = crash
      shared_queue.put(crash)
      print "SERVER, PUT"
      return True
    print "SERVER", 4, "AGUR?"
    return False

  def launch_client(self, shared_queue):
    self.read_configuration()

    gid = int(self.client_gid)
    if gid != os.getgid():
      os.setgid(gid)

    uid = int(self.client_uid)
    if uid != os.getuid():
      os.setuid(uid)

    value = self.q.stats_tube(self.tube_name)["current-jobs-ready"]
    debug("Total of %d job(s) in queue" % value)
    job = self.q.reserve()
    buf, temp_file = json.loads(job.body)
    buf = base64.b64decode(buf)
    debug("Launching sample %s..." % os.path.basename(temp_file))

    cmd = "%s %s" % (self.client_command, temp_file)
    ret = os.system(cmd)
    try:
      crash_info = shared_queue.get(timeout=1)
      print "AT CLIENT", crash_info
    except:
      print "AT CLIENT, except", sys.exc_info()[1]
      crash_info = None

    print "AT CLIENT, before check?", shared_queue
    if not shared_queue.empty():
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

  def fuzz(self):
    log("Launching client/server fuzzer, listening in tube %s" % self.tube_name)
    self.shared_queue = Queue()
    while 1:
      self.crash_info = None
      log("Launching server with command %s" % self.command)
      self.p = Process(target=self.debug_server, args=(self.shared_queue,))
      self.p.start()
      self.p.join(5)

      while self.p.is_alive():
        log("Running client")
        client = Process(target=self.launch_client, args=(self.shared_queue,))
        client.start()
        client.join()

      if self.crash_info is not None:
        log("Server crashed, yuppie!")
        print self.crash_info
      else:
        log("Server exited...")

#-----------------------------------------------------------------------
def main(cfg, fuzzer):
  fuzzer = CClientServerFuzzer(cfg, fuzzer)
  fuzzer.fuzz()

#-----------------------------------------------------------------------
def usage():
  print "Usage:", sys.argv[0], "<config file> <fuzzer>"

if __name__ == "__main__":
  if len(sys.argv) != 3:
    usage()
  else:
    main(sys.argv[1], sys.argv[2])
