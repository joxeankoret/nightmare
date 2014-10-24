#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Nightmare Fuzzing Project
@author: joxean
"""

import os
import sys
import time
import thread

from config import DEBUG

#-----------------------------------------------------------------------
def log(msg):
  print "[%s %d:%d] %s" % (time.asctime(), os.getpid(), thread.get_ident(), msg)
  sys.stdout.flush()

#-----------------------------------------------------------------------
def debug(msg):
  if DEBUG:
    log(msg)
