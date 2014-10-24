#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Nightmare Fuzzing Project
@author: joxean
"""

import beanstalkc

from config import QUEUE_HOST, QUEUE_PORT

#-----------------------------------------------------------------------
def get_queue(name, watch=False):
  q = beanstalkc.Connection(host=QUEUE_HOST, port=QUEUE_PORT)
  if watch:
    q.watch(name)
  else:
    q.use(name)
  return q
