#!/usr/bin/python

"""
Radamsa HTTP server, part of the Nightmare fuzzing project.
Copyright (c) 2016, Joxean Koret

Description:

While radamsa offers a way to listen for network connections, there is
no way to tell what seed we want to use for that specific request. Due
to this reason, reproducibility is a bit more complex. This server needs
both a file extension and a seed in order to serve a sample, forcing to
always have a way to reproduce test-cases. Also, likely due to a bug in
Python using subprocess.check_output with radamsa, for some unknown
reason, may cause weird problems (for example, Python might receive the
SIGSTP signal while or after executing the radamsa command). As so, I 
think it's better to have a separate component that you can just query
instead of having to add that logic into your CGI or whatever fuzzer
you wrote.

How to use it:

At the server-side, run a command similar to this one:

$ python radamsa_server.py <port>

At the client-side, perform a HTTP query similar to this one:

$ curl http://server:port/file_extension?seed=value

That's all!
"""

import re
import os
import web

from subprocess import check_output, CalledProcessError

#-----------------------------------------------------------------------
urls = (
  '/(.*)', 'index'
)

current_dir = os.path.dirname(os.path.realpath(__file__))
BASE_PATH = os.path.realpath(os.path.join(current_dir, "../samples"))

#-----------------------------------------------------------------------
class index:
  def GET(self, extension):
    i = web.input(seed=None)
    if i.seed is None:
      return "No seed specified"
    
    if not re.match("[a-z0-9]+", extension, re.IGNORECASE):
      return "Invalid extension"
    
    path = os.path.join(BASE_PATH, extension)
    if not os.path.exists(path) or not os.path.isdir(path):
      return "Extension not found"
    
    cmd = ["radamsa", "-r", path, "-s", i.seed]
    try:
      buf = check_output(cmd)
    except CalledProcessError as e:
      buf = e.output

    return buf

if __name__ == "__main__":
  app = web.application(urls, globals())
  app.run()

