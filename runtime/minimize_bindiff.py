#!/usr/bin/python

import os
import sys
import json
import zlib
import base64
import shutil
import random
import tempfile
import ConfigParser

from hashlib import sha1

from nfp_log import log
from nfp_queue import get_queue
from nfp_process import TimeoutCommand, RETURN_SIGNALS

try:
  from lib.interfaces import vtrace_iface, gdb_iface, asan_iface, pykd_iface
  has_pykd = True
except ImportError:
  has_pykd = False
  from lib.interfaces import vtrace_iface, gdb_iface, asan_iface

#-----------------------------------------------------------------------
class CGenericBinaryDiffMinimizer:
  def __init__(self, cfg, section):
    self.cfg = cfg
    self.section = section
    self.read_configuration()

    self.diff = []
    self.template = []
    self.crash = {}
    
    self.last_crash = None

  def read_diff(self, diff):
    with open(diff, "rb") as f:
      for line in f.readlines():
        # Ignore lines with comments
        if line.startswith("#"):
          continue
        line = line.strip("\n").strip("\r")
        if line.isdigit():
          self.diff.append(int(line))

  def read_template(self, template):
    self.template = bytearray(open(template, "rb").read())

  def read_crash(self, crash):
    tmp = bytearray(open(crash, "rb").read())
    self.crash = {}
    
    for pos in self.diff:
      self.crash[pos] = tmp[pos]

  def read_configuration(self):
    if not os.path.exists(self.cfg):
      raise Exception("Invalid configuration file given")

    parser = ConfigParser.SafeConfigParser()
    parser.optionxform = str
    parser.read(self.cfg)
    self.parser = parser

    if self.section not in parser.sections():
      raise Exception("Section %s does not exists in the given configuration file" % self.section)

    try:
      self.pre_command = parser.get(self.section, 'pre-command')
    except:
      # Ignore it, it isn't mandatory
      self.pre_command = None

    try:
      self.pre_iterations = int(parser.get(self.section, 'pre-iterations'))
    except:
      # Ignore it, it isn't mandatory
      self.pre_iterations = 1

    try:
      self.post_command = parser.get(self.section, 'post-command')
    except:
      # Ignore it, it isn't mandatory
      self.post_command = None

    try:
      self.post_iterations = int(parser.get(self.section, 'post-iterations'))
    except:
      # Ignore it, it isn't mandatory
      self.post_iterations = 1

    try:
      self.command = parser.get(self.section, 'command')
    except:
      raise Exception("No command specified in the configuration file for section %s" % self.section)
    
    try:
      self.extension = parser.get(self.section, 'extension')
    except:
      raise Exception("No extension specified in the configuration file for section %s" % self.section)

    try:
      self.timeout = parser.get(self.section, 'minimize-timeout')
    except:
      # Default timeout is 90 seconds
      self.timeout = 90
    
    if self.timeout.lower() != "auto":
      self.timeout = int(self.timeout)

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
      self.signal = int(parser.get(self.section, 'signal'))
    except:
      self.signal = None
    
    try:
      self.mode = parser.get(self.section, 'mode')
      if self.mode.isdigit():
        self.mode = int(self.mode)
    except:
      self.mode = 32

    try:
      self.windbg_path = parser.get(self.section, 'windbg-path')
    except:
      self.windbg_path = None

    try:
      self.exploitable_path = parser.get(self.section, 'exploitable-path')
    except:
      self.exploitable_path = None

    try:
      self.debugging_interface = parser.get(self.section, 'minimize-debugging-interface')
      if self.debugging_interface == "pykd":
        self.iface = pykd_iface
      elif self.debugging_interface == "gdb":
        self.iface = gdb_iface
      elif self.debugging_interface == "asan":
        self.iface = asan_iface
      else:
        self.iface = vtrace_iface
    except:
      self.debugging_interface = None
      self.iface = None

    try:
      self.asan_symbolizer_path = parser.get(self.section, 'asan-symbolizer-path')
    except:
      if self.debugging_interface == "asan":
        raise Exception("No asan-symbolizer-path specified in the configuration file for section %s" % self.section)

      self.asan_symbolizer_path = None

    # If the crash-tube is specified, put every single crash found while
    # minimizing a proof-of-concept.
    try:
      self.crash_tube = parser.get(self.section, 'crash-tube')
      self.crash_q = get_queue(self.crash_tube, False)
    except:
      self.crash_tube = None
      self.crash_q = None

    try:
      self.local_files = bool(parser.get(self.section, 'minimize-local-files'))
    except:
      # By default, consider we're minimizing in a box distinct to the
      # one were nfp_engine.py is running
      self.local_files = False

  def minimize(self, template, crash, diff, outdir):
    self.read_diff(diff)
    self.read_template(template)
    self.read_crash(crash)

    log("Performing test case minimization with a total of %d change(s)" % len(self.diff))
    start_at = os.getenv("NIGHTMARE_ITERATION")
    if start_at is not None:
      start_at = int(start_at)
      log("Starting from iteration %d\n" % start_at)
    else:
      start_at = 0

    self.do_try(outdir, start_at)

  def execute_command(self, cmd, timeout):
    ret = None
    if self.debugging_interface is None:
      cmd_obj = TimeoutCommand(cmd)
      ret = cmd_obj.run(timeout=self.timeout)
      if cmd_obj.stderr is not None:
        print cmd_obj.stderr
    else:
      self.iface.timeout = self.timeout
      if not has_pykd or self.iface != pykd_iface:
        if self.iface == asan_iface:
          crash = self.iface.main(asan_symbolizer_path=self.asan_symbolizer_path, args=cmd)
        else:
          crash = self.iface.main(cmd)
      else:
        # Avoid network timeouts and unnecessary delays when using pykd
        os.putenv("_NT_SYMBOL_PATH", "")
        crash = pykd_iface.main([cmd], timeout, mode=self.mode, windbg_path=self.windbg_path, exploitable_path=self.exploitable_path)

      if crash is not None:
        self.last_crash = crash
        ret = 0xC0000005 # Access violation in Windows

    return ret

  def should_notify_crash(self):
    return self.crash_tube is not None and \
           self.last_crash is not None

  def put_new_crash(self, buf):
    try:
      if self.local_files:
        # We can live the files somewhere on disk, nfp_engine.py is
        # running in the same machine
        filename = tempfile.mktemp()
        with open(filename, "wb") as f:
          f.write(buf)
        d = {os.path.abspath(filename):self.last_crash}
      else:
        # The minimizer is running in a box different to the one were
        # nfp_engine.py is running, put the whole file in the queue
        self.last_crash["has_file"] = True
        zbuf = base64.b64encode(zlib.compress(buf))
        d = {zbuf:self.last_crash}

      log("Putting the new crash in the queue...")
      self.crash_q.put(json.dumps(d))
    except:
      log("Error putting the new crash in the queue: %s" % (str(sys.exc_info()[1])))
      if self.local_files:
        os.remove(filename)

  def do_try(self, outdir, start_at=0):
    # Try to minimize to just one change
    current_change = 0
    minimized = False
    iteration = 0
    for i in range(len(self.diff)):
      self.last_crash = None
      for pos in self.diff:
        if start_at <= iteration:
          log("Minimizing, iteration %d (Max. %d)..." % (iteration, (len(self.diff)) * len(self.diff)))
          temp_file = tempfile.mktemp()
          buf = bytearray(self.template)
          if pos not in self.crash:
            continue
          
          buf[pos] = self.crash[pos]

          with open(temp_file, "wb") as f:
            f.write(buf)

          try:
            for key in self.env:
              os.putenv(key, self.env[key])

            if self.pre_command is not None:
              log("Running pre-command %s" % self.pre_command)
              os.system(self.pre_command)

            cmd = "%s %s" % (self.command, temp_file)
            ret = self.execute_command(cmd, self.timeout)

            if self.post_command is not None:
              log("Running post-command %s" % self.post_command)
              os.system(self.post_command)

            if ret in RETURN_SIGNALS or (self.signal is not None and ret == self.signal) or \
             self.crash_file_exists():
              log("Successfully minimized, caught signal %d (%s)!" % (ret, RETURN_SIGNALS[ret]))
              filename = sha1(buf).hexdigest()
              filename = os.path.join(outdir, "%s%s" % (filename, self.extension))
              shutil.copy(temp_file, filename)
              log("Minized test case %s written to disk." % filename)
              minimized = True

              if self.should_notify_crash():
                # TODO: Put the crash in the queue
                pass
              break
          finally:
            os.remove(temp_file)

        if minimized:
          break

        iteration += 1

      if minimized:
          break

      value = self.diff.pop()
      if value in self.crash:
        self.template[value] = self.crash[value]
        del self.crash[value]

    if not minimized:
      log("Sorry, could not minimize crashing file!")
