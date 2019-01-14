#!/usr/bin/python

"""
Nightmare Fuzzing Project samples finder
@author: joxean
@author: Hardik Shah, @hardik05
added option "isBinary", if it is set to 1 give header value as hex, useful to find various binary file. 
if isBinary is 0 then string match will be used to match header value.
added option "urlCount" this will specify how many urls to get from google search.

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
MAX_SIZE = 1024 * 1024

#-----------------------------------------------------------------------
def log(msg):
  print "[%s] %s" % (time.asctime(), msg)

#-----------------------------------------------------------------------
class CSamplesFinder:
  def __init__(self):
    pass

  def find(self, ext, magic, folder,isBinary,count,search=""):
    ext = str(ext)
    magic = str(magic)
    folder = str(folder)
    isBinary = int(isBinary)
    count = str(count)
    curCount = 0

    socket.setdefaulttimeout(30)
    url = "https://www.google.com/search?q=filetype:%s+%s+-facebook.com&num=%s" % (ext, search,count)
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
          curCount = curCount + 1
          try:
            file_data = str(opener.open(href).read(MAX_SIZE+1))
            if len(file_data) > MAX_SIZE:
              log("Discarding file as it's bigger than maximum size (%d kbs)" % (MAX_SIZE/1024))

            #compare hex bytes for header rather then strings hardik shah
            #print(isBinary)
            if isBinary == 1:
              #print "binary file"
              FileHeader = file_data[:4].encode('hex')
              log(FileHeader)
              if magic != FileHeader:
                log("Discarding file as it doesn't start with %s (starts with %s)" % (repr(magic), repr(file_data[:5])))
                continue
            else:
              #print "non binary file."
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
    print "Total Files Processed:",curCount
#-----------------------------------------------------------------------
def main(ext, magic, directory,isBinary,count):
  finder = CSamplesFinder()
  finder.find(ext, magic, directory,isBinary,count)

#-----------------------------------------------------------------------
def usage():
  print "Usage:", sys.argv[0], "extension magic_header folder isBinary urlCount"

if __name__ == "__main__":
  if len(sys.argv) != 6:
    usage()
  else:
    main(sys.argv[1], sys.argv[2], sys.argv[3],sys.argv[4],sys.argv[5])
