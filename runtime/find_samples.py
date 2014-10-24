#!/usr/bin/python

"""
Nightmare Fuzzing Project samples finder
@author: joxean
"""

import os
import sys
import time
import socket
import urllib2

from hashlib import sha1
from urllib import unquote

from BeautifulSoup import BeautifulSoup

#-----------------------------------------------------------------------
MAX_SIZE = 1024*1024*2

#-----------------------------------------------------------------------
def log(msg):
  print "[%s] %s" % (time.asctime(), msg)

#-----------------------------------------------------------------------
class CSamplesFinder:
  def __init__(self):
    pass
  
  def find(self, ext, magic, folder, search=""):
    ext = str(ext)
    magic = str(magic)
    folder = str(folder)

    socket.setdefaulttimeout(30)
    url = "https://www.google.com/search?q=filetype:%s+%s+-facebook.com&num=100" % (ext, search)
    opener = urllib2.build_opener()
    opener.addheaders = [('User-agent', 'Mozilla/5.0')]
    r = opener.open(url)
    buf = r.read()
    soup = BeautifulSoup(buf)
    for a in soup.findAll("a", href=True):
      href = a["href"]
      if href.find("webcache.googleusercontent.com") > -1:
        continue
      if href.find("url?q=") > -1:
        pos = href.find("&")
        if pos > -1:
          href = unquote(href[7:pos])
          log("Downloading %s..." % href)
          try:
            file_data = str(opener.open(href).read(MAX_SIZE+1))
            if len(file_data) > MAX_SIZE:
              log("Discarding file as it's bigger than maximum size (%d kbs)" % (MAX_SIZE/1024))
            if not file_data.startswith(magic):
              log("Discarding file as it doesn't start with %s (starts with %s)" % (repr(magic), repr(file_data[:5])))
              continue

            file_hash = sha1(file_data).hexdigest()
            f = open(os.path.join(folder, file_hash) + "." + ext, "wb")
            f.write(file_data)
            f.close()
            log("File %s saved" % file_hash)
          except KeyboardInterrupt:
            log("Aborted")
            return
          except:
            log("Error: %s" % str(sys.exc_info()[1]))

#-----------------------------------------------------------------------
def main(ext, magic, directory):
  finder = CSamplesFinder()
  finder.find(ext, magic, directory)

#-----------------------------------------------------------------------
def usage():
  print "Usage:", sys.argv[0], "extension magic_header folder"

if __name__ == "__main__":
  if len(sys.argv) != 4:
    usage()
  else:
    main(sys.argv[1], sys.argv[2], sys.argv[3])
