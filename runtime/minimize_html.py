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

from html_fragments import CHtml5Fragmenter

try:
  from lib.interfaces import vtrace_iface, gdb_iface, asan_iface, pykd_iface
  has_pykd = True
except ImportError:
  has_pykd = False
  from lib.interfaces import vtrace_iface, gdb_iface, asan_iface

#-----------------------------------------------------------------------
class CHTMLRewriter:
  def __init__(self):
    self.fragmenter = None
    self.has_js = False
    self.vars_added = False

  def add_javascript(self, tag):
    l = []
    for line in tag.text.split("\n"):
      if line != "":
        l.append(line)

    return l

  def fragment(self, buf):
    self.fragmenter = CHtml5Fragmenter()
    self.fragmenter.parse_buffer(buf)
    return self.fragmenter.fragments

  def rewrite(self, buf, skip_tags=0):
    fragments = self.fragment(buf)

    l = []
    tags = []
    total_skipped = 0
    removed = False

    log("Skipping a total of %d tags" % skip_tags)
    for tag in fragments:
      if total_skipped >= skip_tags and not removed:
        log("*** Removing tag %s" % tag.name)
        removed = True
        continue

      total_skipped += 1
      tag_src = "<%s" % tag.name
      if tag.name != "script":
        for attr in tag.attrs:
          tag_src += ' %s="%s"' % (attr, tag.attrs[attr])
      tag_src += ">"
      l.append(tag_src)

      if tag.text is not None and tag.text != "\n" and tag.name != "script":
        for tmp_line in tag.text.split("\n"):
          if tmp_line != "":
            l.append(tmp_line)
      elif tag.name == "script":
        self.has_js = True
        l.extend(self.add_javascript(tag))

      if tag.name in ["script", "link"] or tag.closed:
        l.append("</%s>" % tag.name)
      else:
        tags.append(tag)

    while len(tags) > 0:
      tag = tags.pop()
      if not tag:
        break

      l.append("</%s>" % tag.name)

    if not removed:
      return False
    return l

#-----------------------------------------------------------------------
class CHtmlMinimizer(CGenericBinaryDiffMinimizer):
  def __init__(self, cfg, section):
    CGenericBinaryDiffMinimizer.__init__(self, cfg, section)
    self.strip_empty_lines = True

    self.read_configuration()
  
  def read_configuration(self):
    CGenericBinaryDiffMinimizer.read_configuration(self)
    try:
      self.line_per_line = bool(self.parser.get(self.section, 'tag-per-tag'))
    except:
      self.line_per_line = False

    try:
      self.lines_to_rip = int(self.parser.get(self.section, 'tags-to-rip'))
    except:
      self.lines_to_rip = 1

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

    log("Performing html-tag-level test case minimization")
    start_at = os.getenv("NIGHTMARE_ITERATION")
    if start_at is not None:
      start_at = int(start_at)
      log("Starting from iteration %d\n" % start_at)
    else:
      start_at = 0

    log("Phase #1: HTML tags simplification")
    self.do_try_html(outdir, start_at)

    # Phase #2, CSS minimization
    # Phase #3, JavaScript minimization
    # Phase #4, HTML properties minimization?

  def crash_file_exists(self):
    if self.crash_path is not None:
      return os.listdir(self.crash_path) > 0
    return False

  def remove_crash_path(self):
    if self.crash_path is not None:
      for f in os.listdir(self.crash_path):
        print "Removing", os.path.join(self.crash_path, f)
        os.remove(os.path.join(self.crash_path, f))

  def get_html_buffer(self, lines, skip_tags):
    log("Rewriting HTML...")
    rewriter = CHTMLRewriter()
    ret = rewriter.rewrite("\n".join(lines), skip_tags)
    if not ret:
      return None, None

    lines = ret
    log("Total line(s) %d" % len(lines))

    return "".join(lines), lines

  def launch_target(self, temp_file, lines, outdir):
    try:
      crashed = False

      for key in self.env:
        os.putenv(key, self.env[key])

      self.remove_crash_path()

      if self.pre_command is not None:
        log("Running pre-command %s" % self.pre_command)
        os.system(self.pre_command)

      if self.command.find("@@") == -1:
        cmd = "%s %s" % (self.command, temp_file)
      else:
        cmd = self.command.replace("@@", temp_file)
      ret = self.execute_command(cmd, self.timeout)

      if self.post_command is not None:
        log("Running post-command %s" % self.post_command)
        os.system(self.post_command)

      if ret in RETURN_SIGNALS or (self.signal is not None and ret == self.signal) or \
         self.crash_file_exists():
          
        crashed = True
        self.template = lines
        log("Process crashed as expected...")
        buf = "\n".join(self.template)
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

      self.remove_crash_path()
    finally:
      os.remove(temp_file)
    
    return crashed

  def do_try(self, outdir, start_at=0):
    raise Exception("FUCK YOU")

  def do_try_html(self, outdir, start_at=0):
    orig_lines = len(self.template)

    iteration = 0
    loops = 0
    
    skip_tags = 0
    while 1:
      self.minimized = False
      total_lines = len(self.template)
      log("Starting loop %d" % loops)

      for i in range(len(self.template)):
        self.last_crash = None

        self.read_configuration()
        log("Minimizing, iteration %d..." % iteration)
        iteration += 1
        temp_file = tempfile.mktemp(suffix=self.extension)
        lines = self.template
        buf, lines = self.get_html_buffer(lines, skip_tags)
        if buf is None:
          log("Done minimizing...")
          break

        with open(temp_file, "wb") as f:
          f.write(buf)

        crashed = self.launch_target(temp_file, lines, outdir)
        if not crashed:
          log("Process did not crash, skipping one tag...")
          skip_tags += 1

      loops += 1

      if len(self.template) == total_lines:
        log("File minimized from %d line(s) to %d line(s)" % (orig_lines, len(self.template)))
        buf = "\n".join(self.template)
        filename = sha1(buf).hexdigest()
        filename = os.path.join(outdir, "%s%s" % (filename, self.extension))
        with open(filename, "wb") as f:
          f.write(buf)
        log("Minimized test case %s written to disk." % filename)
        self.minimized = True
        break
