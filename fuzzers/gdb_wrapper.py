#!/usr/bin/python

import re
import os
import sys
import time

from threading  import Thread
from subprocess import PIPE, Popen

try:
    from Queue import Queue, Empty
except ImportError:
    from queue import Queue, Empty  # python 3.x

#-----------------------------------------------------------------------
ON_POSIX = 'posix' in sys.builtin_module_names

#-----------------------------------------------------------------------
def enqueue_output(out, queue):
  for line in iter(out.readline, b''):
    if not queue:
      break
    queue.put(line)
  out.close()

#-----------------------------------------------------------------------
class CProgramWrapper:
  def __init__(self):
    self.t = None
    self.q = None
    self.p = None

    self.output_callback = None
    self.timeout_callback = None
    
    self.do_run = True

  def set_output_callback(self, cb):
    self.output_callback = cb

  def set_timeout_callback(self, cb):
    self.timeout_callback = cb

  def run(self, args):
    p = Popen(" ".join(args), stdout=PIPE, stdin=PIPE, bufsize=1, \
              shell=True, close_fds=ON_POSIX)
    q = Queue()
    t = Thread(target=enqueue_output, args=(p.stdout, q))
    t.daemon = True # thread dies with the program
    t.start()

    self.q = q
    self.p = p
    self.t = t
    
    self.loop()

  def read_line(self):
    try:
      line = self.q.get_nowait()
      if self.output_callback is not None:
        self.output_callback(self, line, self.p.stdin)
    except KeyboardInterrupt:
      return
    except Empty:
      if self.timeout_callback is not None:
        self.timeout_callback(self, self.p.stdin)

  def loop(self):
    while self.p.returncode is None:
      self.read_line()
      if not self.do_run:
        break

  def loop_until_empty(self):
    buf = ""
    while 1:
      try:
        line = self.q.get_nowait()
        buf += line
        if self.output_callback is not None:
          self.output_callback(self, line, self.p.stdin)
      except Empty:
        break
    return buf

  def read_until_empty(self):
    buf = ""
    while 1:
      try:
        line = self.q.get_nowait()
        buf += line
      except Empty:
        break
    return buf

#-----------------------------------------------------------------------
class CGdbWrapper:
  def __init__(self):
    self.wrapper = CProgramWrapper()
    self.inited = False
    self.started = False
    
    self.exit_callback = None
    self.exception_callback = None

  def output_callback(self, w, line, stdin):
    print line.strip("\r").strip("\n")
    if not self.inited and not self.started:
      self.inited = True
      w.do_run = False
      return

    if self.inited and self.started:
      if re.match("\[Inferior \d+ \(process \d+\) exited", line):
        if self.exit_callback is not None:
          self.exit_callback(self, line)
        stdin.write("quit\n")
        stdin.write("y\n")
        self.wrapper.p.kill()
        self.wrapper.p.returncode = -1
      elif re.match("Program received signal", line):
        signal = re.findall("Program received signal (.*), .*\.", line)[0]
        self.wrapper.read_line()
        if self.exception_callback is not None:
          self.exception_callback(self, signal, line)

  def timeout_callback(self, w, stdin):
    if self.inited and not self.started:
      self.started = True

  def set_exit_callback(self, cb):
    self.exit_callback = cb

  def set_exception_callback(self, cb):
    self.exception_callback = cb

  def start(self, prog):
    self.wrapper.set_output_callback(self.output_callback)
    self.wrapper.set_timeout_callback(self.timeout_callback)
    self.wrapper.run(prog)

  def send_command(self, arg, loop=True):
    self.wrapper.p.stdin.write("%s\n" % arg)
    time.sleep(0.1)
    if loop:
      print self.wrapper.loop_until_empty()

  def read_answer(self):
    return self.wrapper.read_until_empty()

  def run(self, args):
    self.wrapper.do_run = True
    self.send_command("r %s" % " ".join(args))
  
  def loop(self):
    self.wrapper.loop()

#-----------------------------------------------------------------------
def exit_callback(gdb, line):
  print "EXIT", gdb, line

#-----------------------------------------------------------------------
def exception_callback(gdb, signal, line):
  print("SIGNAL", signal)
  print(gdb, line)
  gdb.send_command("back", loop=False)
  answer = gdb.read_answer()
  print "ANSWER"
  print answer
  raw_input("?")

#-----------------------------------------------------------------------
def main(args):
  prog = []
  prog_args = []
  i = 0
  for arg in args:
    if arg == "--":
      prog_args = args[i+1:]
      break
    prog.append(arg)
    i += 1

  print("Program:", prog, "Arguments:", prog_args)

  gdb = CGdbWrapper()
  gdb.set_exception_callback(exception_callback)
  gdb.set_exit_callback(exit_callback)
  gdb.start(prog)
  gdb.send_command("set follow-fork-mode child")
  gdb.run(prog_args)
  gdb.loop()

#-----------------------------------------------------------------------
def usage():
  print("Usage:", sys.argv[0], "<command>")

if __name__ == "__main__":
  if len(sys.argv) < 3:
    usage()
  else:
    main(sys.argv[1:])
