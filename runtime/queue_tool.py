#!/usr/bin/python

import os
import sys
import json
import base64
import tempfile

from nfp_log import log
from nfp_queue import get_queue

#-----------------------------------------------------------------------
class CFileQueuer:
  def __init__(self, tube_prefix):
    if tube_prefix.endswith("-samples"):
      log("Notice: Removing '-samples' suffix from the queue name")
      tube_prefix = tube_prefix.replace("-samples", "")

    self.tube_prefix = tube_prefix
    self.q = get_queue(watch=False, name="%s-samples" % tube_prefix)

  def put(self, filename):
    temp_file = tempfile.mktemp()
    
    try:
      buf = open(filename, "rb").read()
      
      with open(temp_file, "wb") as f:
        f.write(buf)

      json_buf = json.dumps([base64.b64encode(buf), temp_file])
      self.q.put(json_buf)
      l = "File '%s' put in queue %s as temporary file '%s'"
      log(l % (filename, self.tube_prefix, temp_file))
    except:
      raise
      os.remove(temp_file)

#-----------------------------------------------------------------------
def list_queues():
  q = get_queue(watch=False, name="default")
  for tube in q.tubes():
    if tube not in ["default"]:
      line = "Tube %s, total of %d job(s)"
      try:
        print line % (tube, q.stats_tube(tube)["current-jobs-ready"])
      except:
        sys.stderr.write("Error reading tube %s: %s\n" % (tube, str(sys.exc_info()[1])))
        sys.stderr.flush()

#-----------------------------------------------------------------------
def empty_queue():
  if len(sys.argv) == 2:
    print "Command '-e' needs a queue to empty."
  else:
    tube = sys.argv[2]
    q = get_queue(watch=True, name=tube)

    while 1:
      job = q.reserve(1)
      if not job:
        break
      job.delete()

#-----------------------------------------------------------------------
def check_command(cmd):
  if cmd == "-l":
    list_queues()
  elif cmd == "-h":
    usage()
  elif cmd == "-e":
    empty_queue()
  else:
    print "Unknown command %s" % repr(cmd)
    usage()

#-----------------------------------------------------------------------
VALID_COMMANDS = ["-l", "-e", "-h"]
def usage():
  print "Usage:", sys.argv[0], "[<queue name> <filename> | [-l|-h|-e <queue name>]]"
  print
  print "Options:"
  print "-e             Empty queue <queue>"
  print "-l             List all existing queues."
  print "-h             Show this help."
  print
  print "Specify a 'queue name' and a 'filename' to put a file in a queue."

#-----------------------------------------------------------------------
def main(queue, filename):
  queuer = CFileQueuer(queue)
  queuer.put(filename)

if __name__ == "__main__":
  if len(sys.argv) in [2, 3] and sys.argv[1] in VALID_COMMANDS:
    check_command(sys.argv[1])
  elif len(sys.argv) != 3:
    usage()
  else:
    main(sys.argv[1], sys.argv[2])
