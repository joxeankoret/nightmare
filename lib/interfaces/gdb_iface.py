#!/usr/bin/gdb -P
# -*- coding: utf-8 -*-
"""
GDB 7.4 debugging interface for Nightmare Fuzzing Project
Created on Sat May 18 10:23:14 2013
@author: joxean
"""

import os
import sys
import gdb
import thread
import threading

class CGDBInterface(object):
  def __init__(self, program, arguments, thread):
    self.program = program
    self.args = arguments
    self.thread = thread

  def stop_handler(self, event):
    print "STOP", event
    print "SAMPLE FILE", self.args
    print dir(event)
    gdb.execute("x /i $pc")
    gdb.execute("i r")
    gdb.execute("backtrace 20")
    self.thread.cancel()

  def run(self):
    gdb.events.stop.connect(self.stop_handler)
    gdb.execute("file " + self.program)
    gdb.execute("r " + self.args)

def kill_myself():
  print "!!!!!!!!!!!!!!!!!!"
  print "! Killing myself !"
  print "!!!!!!!!!!!!!!!!!!"
  thread.interrupt_main()

def main():
  t = threading.Timer(10, kill_myself)
  t.start()

  iface = CGDBInterface(os.getenv("NIGHTMARE_PROGRAM"), os.getenv("NIGHTMARE_ARGS"), t)
  iface.thread = t
  iface.run()

def usage():
  print "Usage:", sys.argv[0], "<program> <file>"

if __name__ == "__main__":
  main()
