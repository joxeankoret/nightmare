#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Nightmare Fuzzing Project
@author: joxean
"""

import sys
import threading
import subprocess

from multiprocessing import Process, cpu_count

from nfp_log import log, debug

#-----------------------------------------------------------------------
# Dict of return codes to signals that we're interested on.
RETURN_SIGNALS = {}
RETURN_SIGNALS[138] = "SIGBUS"
RETURN_SIGNALS[139] = "SIGSEGV"
RETURN_SIGNALS[136] = "SIGFPE"
RETURN_SIGNALS[134] = "SIGABRT"
RETURN_SIGNALS[133] = "SIGTRAP"
RETURN_SIGNALS[132] = "SIGILL"
RETURN_SIGNALS[143] = "SIGTERM"

#-----------------------------------------------------------------------
def process_manager(total_procs, target, args, wait_time=0.2):
  """ Always maintain a total of @total_procs running @target and
     waiting for each thread to finish @wait_time second(s). """
  procs = []
  debug("Maximum number of processes in pool is %d" % total_procs)
  try:
    while 1:
      if len(procs) < total_procs:
        debug("Starting process %d" % (len(procs)+1))
        p = Process(target=target, args=args)
        p.start()
        procs.append(p)
        debug("Total of %d process(es) started" % len(procs))
      else:
        i = 0
        for p in list(procs):
          p.join(wait_time)
          if not p.is_alive():
            debug("Process finished, deleting and starting a new one...")
            del procs[i]
            continue
          i += 1
  except KeyboardInterrupt:
    pass

#-----------------------------------------------------------------------
class TimeoutCommand(object):
  """ Execute a command specified by @cmd and wait until a maximum of
      @timeout seconds. If the timeout is reached, the process is then
      killed. """
  def __init__(self, cmd):
    self.cmd = cmd
    self.process = None

  def run(self, timeout=60):
    def target():
      debug('Thread started')
      self.process = subprocess.Popen("exec %s" % self.cmd, shell=True)
      self.process.communicate()
      debug('Thread finished')

    thread = threading.Thread(target=target)
    thread.start()

    thread.join(timeout)
    if thread.is_alive():
      log('Terminating process after timeout (%d)' % timeout)
      self.process.terminate()
      self.process.kill()
      thread.join()
    self.process.wait()
    ret = self.process.returncode
    
    # A negative return code means a signal was received and the return
    # code is -1 * SIGNAL. Return the expected Unix return code.
    if ret is not None and ret < 0:
      ret = abs(ret) + 128
    return ret

#-----------------------------------------------------------------------
def do_nothing():
  try:
    import time
    print time.asctime()
    time.sleep(1)
  except KeyboardInterrupt:
    print "Aborted."

if __name__ == "__main__":
  process_manager(2, do_nothing, [], 1)
