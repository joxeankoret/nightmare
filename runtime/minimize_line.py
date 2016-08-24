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
from minimize_bindiff import CGenericBinaryDiffMinimizer

try:
  from lib.interfaces import vtrace_iface, gdb_iface, asan_iface, pykd_iface
  has_pykd = True
except ImportError:
  has_pykd = False
  from lib.interfaces import vtrace_iface, gdb_iface, asan_iface

#-----------------------------------------------------------------------
class CLineMinimizer(CGenericBinaryDiffMinimizer):
  def __init__(self, cfg, section):
    CGenericBinaryDiffMinimizer.__init__(self, cfg, section)
    self.strip_empty_lines = True

    self.read_configuration()
  
  def read_configuration(self):
    CGenericBinaryDiffMinimizer.read_configuration(self)
    try:
      self.line_per_line = bool(self.parser.get(self.section, 'line-per-line'))
    except:
      self.line_per_line = False
    
    try:
      self.lines_to_rip = int(self.parser.get(self.section, 'lines-to-rip'))
    except:
      self.lines_to_rip = 1

    try:
      self.lines_percent = int(self.parser.get(self.section, 'lines-percent'))
    except:
      self.lines_percent = 10
    
    try:
      self.crash_path = self.parser.get(self.section, 'crash-path')
    except:
      self.crash_path = None
    
    try:
      self.infinite_loop = self.parser.get(self.section, 'crash-path')
    except:
      self.infinite_loop = False

  def read_template(self, template):
    l = open(template, "rb").readlines()
    if self.strip_empty_lines:
      tmp = []
      for line in l:
        if line in ["\n", "\r\n"]:
          continue
        tmp.append(line)
      l = tmp
    self.template = l

  def minimize(self, template, outdir):
    self.read_template(template)

    log("Performing line-level test case minimization")
    start_at = os.getenv("NIGHTMARE_ITERATION")
    if start_at is not None:
      start_at = int(start_at)
      log("Starting from iteration %d\n" % start_at)
    else:
      start_at = 0

    self.do_try(outdir, start_at)

  def crash_file_exists(self):
    if self.crash_path is not None:
      return os.listdir(self.crash_path) > 0
    return False

  def remove_crash_path(self):
    if self.crash_path is not None:
      for f in os.listdir(self.crash_path):
        print "Removing", os.path.join(self.crash_path, f)
        os.remove(os.path.join(self.crash_path, f))

  def do_try(self, outdir, start_at=0):
    """ Try to remove a random number of lines iterating from the first
        line to the last one a number of times. Basically, we calculate
        a total number of lines to remove between 1 line and 10%. If the
        number of lines removed produces a test-case that still crashes,
        remove the lines from the template, otherwise, drop the changes 
        and move to the next line.

        IDEAS: Remove all empty lines before starting?
    """
    orig_lines = len(self.template)

    current_line = 0
    iteration = 0
    loops = 0
    while 1:
      self.minimized = False
      total_lines = len(self.template)
      log("Starting loop %d" % loops)
      current_line = 0

      for i in range(len(self.template)):
        self.last_crash = None

        self.read_configuration()
        log("Minimizing, iteration %d..." % iteration)
        iteration += 1
        temp_file = tempfile.mktemp(suffix=self.extension)
        lines = self.template

        if current_line >= len(lines):
          break

        if loops == 0 and not self.line_per_line:
          # Rip a random number of lines between 1 and self.lines_percent
          # but only at the very first iteration (when we remove most of
          # the stuff).
          val = (total_lines-current_line)*self.lines_percent/100
          if val == 0:
            val = 1

          lines_to_rip = random.randint(1, val)
          log("Removing %d line(s) (maximum of %d%%)" % (lines_to_rip, self.lines_percent))
        else:
          # For the likely final run remove only one line per try (or
          # whatever is specified in the configuration file)
          lines_to_rip = self.lines_to_rip
          log("Removing %d line(s)" % lines_to_rip)

        lines = lines[:current_line] + lines[current_line+lines_to_rip:]
        buf = "".join(lines)

        with open(temp_file, "wb") as f:
          f.write(buf)

        try:
          for key in self.env:
            os.putenv(key, self.env[key])

          self.remove_crash_path()

          if i % self.pre_iterations == 0:
            if self.pre_command is not None:
              log("Running pre-command %s" % self.pre_command)
              os.system(self.pre_command)

          if self.command.find("@@") == -1:
            cmd = "%s %s" % (self.command, temp_file)
          else:
            cmd = self.command.replace("@@", temp_file)
          ret = self.execute_command(cmd, self.timeout)

          if i % self.post_iterations == 0:
            if self.post_command is not None:
              log("Running post-command %s" % self.post_command)
              os.system(self.post_command)

          if ret in RETURN_SIGNALS or (self.signal is not None and ret == self.signal) or \
             self.crash_file_exists():
            self.template = lines
            log("Process crashed as expected...")
            buf = "".join(self.template)
            if not os.path.exists(outdir):
              log("Directory %s does not exists, creating it..." % outdir)
              os.mkdir(outdir)

            filename = os.path.join(outdir, "last_minimized%d%s" % (os.getpid(), self.extension))
            with open(filename, "wb") as f:
              f.write(buf)
            log("Last minimized test case %s written to disk." % filename)

            if self.should_notify_crash():
              # TODO: Write a temporary file and put an enqueue the crash
              self.put_new_crash(buf)
          else:
            current_line += 1

          self.remove_crash_path()
        finally:
          os.remove(temp_file)

      loops += 1

      if len(self.template) == total_lines:
        log("File minimized from %d line(s) to %d line(s)" % (orig_lines, len(self.template)))
        buf = "".join(self.template)
        filename = sha1(buf).hexdigest()
        filename = os.path.join(outdir, "%s%s" % (filename, self.extension))
        with open(filename, "wb") as f:
          f.write(buf)
        log("Minimized test case %s written to disk." % filename)
        self.minimized = True
        break
