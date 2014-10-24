"""
Cobra RMI Framework

Cobra is a remote method invocation interface that is very "pythony".  It is
MUCH like its inspiration pyro, but slimmer and safer for things like threading
and object de-registration.  Essentially, cobra allows you to call methods from
and get/set attributes on objects that exist on a remote system.

"""
# Copyright (C) 2007 Invisigoth - See LICENSE file for details
import marshal
import imp
import sys
import os
import socket
from SocketServer import ThreadingTCPServer, BaseRequestHandler
from threading import currentThread,Thread,RLock
import cPickle as pickle
import urllib2
import struct
import types
import time
import errno
import traceback
try:
    import OpenSSL
    OpenSSLSysCallError = OpenSSL.SSL.SysCallError
except Exception, e:
#   print >> sys.stderr,  "OpenSSL not found: %s" % (e)
    class OpenSSLSysCallError(Exception): pass

daemon = None
verbose = False
version = "Cobra2"
COBRA_PORT=5656
COBRASSL_PORT=5653
cobra_retrymax = None # Optional *global* retry max count

# Message Types
COBRA_HELLO     = 0
COBRA_CALL      = 1
COBRA_GETATTR   = 2
COBRA_SETATTR   = 3
COBRA_ERROR     = 4
COBRA_GOODBYE   = 5


class CobraException(Exception):
    """Base for Cobra exceptions"""
    pass

class CobraClosedException(CobraException):
    """Raised when a connection is unexpectedly closed."""
    pass

class CobraRetryException(Exception):
    """Raised when the retrymax (if present) for a proxy object is exceeded."""
    pass

class CobraPickleException(Exception):
    """Raised when pickling fails."""
    pass

def connectSocket(host,port, ssl=False, sslVerify=False, sslKey=None, sslCert=None, timeout=None):
    """
    Make the long names go away....
    """
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    if timeout is not None:
        s.settimeout(timeout)

    # If ssl was requested, set up the ssl stuff and attach it to the socket
    if ssl or sslVerify or sslKey or sslCert:
        if verbose: print "SSL: Setting up SSL (client)"
        
        ctx = OpenSSL.SSL.Context(OpenSSL.SSL.SSLv3_METHOD)

        if sslVerify and (sslKey and sslCert):
            setSslVerify(ctx)

        setSslKey(ctx, sslKey)
        setSslCert(ctx, sslCert)

        s = OpenSSL.SSL.Connection(ctx, s)
        s.set_connect_state()

    s.connect((host, port))

    return s

def getCallerInfo():
    """
    This function may be used from *inside* a method being called
    by a remote caller.  It will return a tuple of host,port for the
    other side of the connection... use wisely ;)
    """
    return getattr(currentThread(),"__cobra_caller_info",None)

def getLocalInfo():
    """
    This function returns the local host,port combination being
    used in the socket servicing the current request
    """
    return getattr(currentThread(), "__cobra_local_info", None)

def setCallerInfo(callerinfo):
    """
    This is necissary because of crazy python method call
    name munging for thread attributes ;)
    """
    currentThread().__cobra_caller_info = callerinfo

def setLocalInfo(localinfo):
    currentThread().__cobra_local_info = localinfo

def newCobraSocket(thr, host, port, retrymax=None, ssl=False, sslVerify=False, sslKey=None, sslCert=None, timeout=None):
    """
    This is only used by *clients*
    """
    if verbose: print "CONNECTING TO:",host,port
    sock = connectSocket(host, port, ssl=ssl, sslVerify=sslVerify, sslKey=sslKey, sslCert=sslCert, timeout=timeout)
    s = CobraSocket(sock, client=True, retrymax=retrymax, ssl=ssl, sslVerify=sslVerify, sslKey=sslKey, sslCert=sslCert, timeout=timeout)
    thr.cobrasocks[(host,port)] = s
    return s

def getCobraSocket(proxy):
    thr = currentThread()
    if not hasattr(thr, "cobrasocks"):
        thr.cobrasocks = {}
    #FIXME possibly optimize host,port use...
    host = proxy.__dict__.get("__cobra_host","")
    port = proxy.__dict__.get("__cobra_port", 0)
    scheme = proxy.__dict__.get("__cobra_scheme","")
    timeout = proxy.__dict__.get("__cobra_timeout",None)
    s = thr.cobrasocks.get((host,port), None)
    if not s:
        rmax = proxy.__dict__.get("__cobra_retrymax", None)
        if scheme == "cobrassl":
            sslKey = proxy.__dict__.get("__cobra_key", None)
            sslCert = proxy.__dict__.get("__cobra_cert", None)
            sslVerify = proxy.__dict__.get("__cobra_verify", False)
            s = newCobraSocket(thr, host, port, retrymax=rmax, ssl=True, sslVerify=sslVerify, sslKey=sslKey, sslCert=sslCert, timeout=timeout)
        else:
            s = newCobraSocket(thr, host, port, retrymax=rmax, timeout=timeout)
    return s

def bumpCobraSocket(proxy):
    """
    Remove the socket for this proxy so the next
    call causes a new connection
    """
    host = proxy.__dict__["__cobra_host"]
    port = proxy.__dict__["__cobra_port"]
    currentThread().cobrasocks.pop((host,port), None)

class CobraMethod:
    def __init__(self, proxy, methname):
        self.proxy = proxy
        self.methname = methname

    def __call__(self, *args, **kwargs):
        name = self.proxy.__dict__["__cobra_name"]
        if verbose: print "CALLING:",name,self.methname,repr(args)[:20],repr(kwargs)[:20]
        csock = getCobraSocket(self.proxy)
        mtype, name, data = csock.cobraTransaction(COBRA_CALL, name, (self.methname, args, kwargs))
        if mtype == COBRA_CALL:
            return data

        if mtype == COBRA_ERROR:
            raise data

class CobraSocket:
    def __init__(self, sock, client=False, retrymax=None, ssl=False, sslVerify=False, sslKey=None, sslCert=None, timeout=None):
        self.client = client # Only the client reconnects
        self.socket = sock
        self.host,self.port = sock.getpeername()
        self.retries = 0
        self.retrymax = retrymax
        self.ssl = ssl
        self.sslVerify = sslVerify
        self.sslKey = sslKey
        self.sslCert = sslCert
        self.timeout = timeout
        if self.retrymax == None:
            self.retrymax = cobra_retrymax

    def getSockName(self):
        return self.socket.getsockname()

    def getPeerName(self):
        return self.socket.getpeername()

    def reConnect(self):
        """
        Handle the event where we need to reconnect
        """
        while self.retrymax is None or self.retries < self.retrymax:
            if verbose: sys.stderr.write("COBRA: Reconnection Attempt\n")
            try:
                self.socket = connectSocket(self.host, self.port, ssl=self.ssl, sslVerify=self.sslVerify, sslKey=self.sslKey, sslCert=self.sslCert, timeout=self.timeout)
                self.retries = 0
                return
            except Exception, e:
                time.sleep(2 ** self.retries)
                self.retries += 1
        raise CobraRetryException()

    def cobraTransaction(self, mtype, objname, data):
        """
        This is an API for clients to use.  It will retransmit
        a sendMessage() automagically on recpt of an exception
        in recvMessage()
        """
        while True:
            try:
                self.sendMessage(mtype, objname, data)
                return self.recvMessage()
            except CobraClosedException, e:
                self.reConnect()
            except socket.error, e:
                self.reConnect()
            except OpenSSLSysCallError, e:
                self.reConnect()

    def sendMessage(self, mtype, objname, data):
        """
        Send message is responsable for transmission of cobra messages,
        and socket reconnection in the event that the send fails for network
        reasons.
        """
        try:
            buf = pickle.dumps(data)
        except pickle.PickleError, e:
            raise CobraPickleException("The arguments/attributes must be pickleable: %s" % e)

        while True:
            try:
                s = self.socket
                s.sendall(''.join( (struct.pack("<LLL", mtype, len(objname), len(buf)), objname, buf)))
                return
            except socket.error, e:
                if e.args[0] == errno.EPIPE:
                    if not self.client:
                        raise CobraClosedException
                elif not self.client:
                    raise
                self.reConnect()
            except OpenSSLSysCallError, e:
                if not self.client:
                    raise
                self.reConnect()

    def recvMessage(self):
        """
        Returns tuple of mtype, objname, and data
        This method is *NOT* responsable for re-connection, because there
        is not context on the server side for what to send on re-connect.
        Client side uses of the CobraSocket object should use cobraTransaction
        to ensure re-tranmission of the request on reception errors.
        """
        s = self.socket
        hdr = self.recvExact(s, 12)
        mtype, nsize, dsize = struct.unpack("<LLL", hdr)
        name = self.recvExact(s, nsize)
        data = pickle.loads(self.recvExact(s, dsize))
        return (mtype, name, data)

    def recvExact(self, s, size):
        buf = ""
        while len(buf) != size:
            try:
                x = s.recv(size - len(buf))
            except OpenSSLSysCallError:
                # FIXME Hack for when a client disconnects from
                # a CobraSslDaemon ...
                x = ""
            if len(x) == 0:
                raise CobraClosedException("Socket closed in recvExact...")
            buf += x
        return buf

def tru(*args):
    return args[4]

def setSslVerify(ctx):
# FIXME: The verification stuff doesn't work yet
# I think there's just a step or two missing.
#
# Ugh...this whole thing is completely jacked...
#
# This pretty much needs to be completely implemented
# which means there's no verification of any kind 
# happening right now.

    ctx.set_verify(OpenSSL.SSL.VERIFY_PEER, tru)

#    if 0:
#        if verbose: print "SSL: Verifying peer (daemon)"
#        ctx.set_verify(OpenSSL.SSL.VERIFY_PEER | OpenSSL.SSL.VERIFY_FAIL_IF_NO_PEER_CERT, tru)
#            ctx.load_verify_locations("server.pem")
#    else:
#        ctx.set_verify(OpenSSL.SSL.VERIFY_NONE, tru)

def setSslKey(ctx, sslKey = None):
    """
    Checks to see if sslKey is a file. If so,
    it opens it and uses that file for the SSL
    key. Otherwise, it assumes sslKey is a PEM
    format key. If nothing is provided, we'll
    use cobraDevKey...
    """
    if sslKey:
        try:
            os.stat(sslKey)
            keyIsFile = True
        except:
            keyIsFile = False

        if keyIsFile:
            if verbose: print "SSL: Using key file: %s" % (sslKey)
            ctx.use_privatekey_file(sslKey)
        else:
            if verbose: print "SSL: Using specified key"
            key = OpenSSL.crypto.load_privatekey(OpenSSL.crypto.FILETYPE_PEM, sslKey)
            ctx.use_privatekey(cobraKey)

    else:
        if verbose: print "SSL: Key not provided...using dev key"
        key = OpenSSL.crypto.load_privatekey(OpenSSL.crypto.FILETYPE_PEM, cobraDevKey)
        ctx.use_privatekey(key)

def setSslCert(ctx, sslCert = None):
    """
    Checks to see if sslCert is a file. If so,
    it opens it and uses that file for the SSL
    cert. Otherwise, it assumes sslKey is a PEM
    format cert. If nothing is provided, we'll
    use cobraDevCert...
    """
    if sslCert:
        try:
            os.stat(sslCert)
            certIsFile = True
        except:
            certIsFile = False

        if certIsFile:
            if verbose: print "SSL: Using cert file: %s" % (sslCert)
            ctx.use_certificate_file(sslCert)
        else:
            if verbose: print "SSL: Using specified cert"
            cert = OpenSSL.crypto.load_certificate(OpenSSL.crypto.FILETYPE_PEM, sslCert)
            ctx.use_certificate(cert)

    else:
        if verbose: print "SSL: Cert not provided...using dev cert"
        cert = OpenSSL.crypto.load_certificate(OpenSSL.crypto.FILETYPE_PEM, cobraDevCert)
        ctx.use_certificate(cert)

class CobraDaemon(ThreadingTCPServer):
    def __init__(self, host="", port=COBRA_PORT):
        self.shared = {}
        self.host = host
        self.port = port
        self.reflock = RLock()
        self.refcnts = {}

        self.allow_reuse_address = True
        ThreadingTCPServer.__init__(self, (host, port), CobraConnectionHandler)

        if port == 0:
            self.port = self.socket.getsockname()[1]

        self.daemon_threads = True

    def fireThread(self):
        thr = Thread(target=self.serve_forever)
        thr.setDaemon(True)
        thr.start()

    def getSharedObject(self, name):
        return self.shared.get(name, None)

    def getSharedName(self, obj):
        '''
        If this object is shared already, get the name...
        '''
        for name, sobj in self.shared.items():
            if sobj == obj:
                return name
        return None

    def getRandomName(self):
        ret = ""
        for byte in os.urandom(16):
            ret += "%.2x" % ord(byte)
        return ret

    def shareObject(self, obj, name=None, doref=False):
        """
        Share an object in this cobra server.  By specifying
        doref=True you will let CobraProxy objects decide that
        the object is done and should be un-shared.  Also, if
        name == None a random name is chosen.

        Returns: name (or the newly generated random one)
        """
        refcnt = None
        if doref:
            refcnt = 0
        if name == None:
            name = self.getRandomName()

        self.shared[name] = obj
        self.refcnts[name] = refcnt
        return name

    def decrefObject(self, name):
        """
        Decref this object and if it reaches 0, unshare it.
        """
        if verbose: print "DECREF:",name
        self.reflock.acquire()
        try:

            refcnt = self.refcnts.get(name, None)
            if refcnt != None:
                refcnt -= 1
                self.refcnts[name] = refcnt
                if refcnt == 0:
                    self.unshareObject(name)

        finally:
            self.reflock.release()

    def increfObject(self, name):
        if verbose: print "INCREF:",name
        self.reflock.acquire()
        try:
            refcnt = self.refcnts.get(name, None)
            if refcnt != None:
                refcnt += 1
                self.refcnts[name] = refcnt
        finally:
            self.reflock.release()

    def unshareObject(self, name):
        self.refcnts.pop(name, None)
        return self.shared.pop(name, None)

class CobraSslDaemon(CobraDaemon):
    """
    Pretty much just extends the CobraDaemon class to provide an SSL enabled CobraDaemon
    """
    def __init__(self, host="", port=COBRASSL_PORT, sslVerify = False, sslKey = None, sslCert = None):
        CobraDaemon.__init__(self, host=host, port=COBRASSL_PORT)
        sslContext = OpenSSL.SSL.Context(OpenSSL.SSL.SSLv3_METHOD)

        if verbose: print "SSL: Setting up SSL (daemon)"

        try:
            if sslVerify:
                setSslVerify(sslContext)

            setSslKey(sslContext, sslKey)
            setSslCert(sslContext, sslCert)
            sslContext.check_privatekey()

            ssock = OpenSSL.SSL.Connection(sslContext, self.socket)
            ssock.set_connect_state()
            self.socket = ssock
        except:
            raise "SSL: SSL setup failed"

class CobraConnectionHandler(BaseRequestHandler):

    def setup(self):
        self.handlers = (
            self.handleHello,
            self.handleCall,
            self.handleGetAttr,
            self.handleSetAttr,
            self.handleError,
            self.handleGoodbye)

    def handle(self):
        peer = self.request.getpeername()
        me = self.request.getsockname()
        if verbose: print "GOT A CONNECTIONN",peer
        csock = CobraSocket(self.request)
        setCallerInfo(peer)
        setLocalInfo(me)

        while True:

            try:
                mtype,name,data = csock.recvMessage()
            except CobraClosedException:
                break
            except socket.error:
                if verbose: traceback.print_exc()
                break

            obj = self.server.getSharedObject(name)
            if verbose: print "MSG FOR:",name,type(obj)

            if obj == None:
                try:
                    csock.sendMessage(COBRA_ERROR, name, Exception("Unknown object requested: %s" % name))
                except CobraClosedException:
                    pass
                if verbose: print "WARNING: Got request for unknown object",name
                continue

            try:
                handler = self.handlers[mtype]
            except:
                try:
                    csock.sendMessage(COBRA_ERROR, name, Exception("Invalid Message Type"))
                except CobraClosedException:
                    pass
                if verbose: print "WARNING: Got Invalid Message Type: %d for %s" % (mtype, data)
                continue

            try:
                handler(csock, name, obj, data)
            except Exception, e:
                if verbose: traceback.print_exc()
                try:
                    csock.sendMessage(COBRA_ERROR, name, e)
                except CobraClosedException:
                    pass

    def handleError(self, csock, oname, obj, data):
        print "THIS SHOULD NEVER HAPPEN"

    def handleHello(self, csock, oname, obj, data):
        """
        Hello messages are used to get the initial cache of
        method names for the newly connected object.
        """
        if verbose: print "GOT A HELLO"
        self.server.increfObject(oname)
        ret = {}
        for name in dir(obj):
            if type(getattr(obj,name)) == types.MethodType:
                ret[name] = True
        try:
            csock.sendMessage(COBRA_HELLO, version, ret)
        except CobraClosedException:
            pass

    def handleCall(self, csock, oname, obj, data):
        if verbose: print "GOT A CALL",data
        methodname, args, kwargs = data
        meth = getattr(obj, methodname)
        try:
            csock.sendMessage(COBRA_CALL, "", meth(*args, **kwargs))
        except CobraClosedException:
            pass

    def handleGetAttr(self, csock, oname, obj, name):
        if verbose: print "GETTING ATTRIBUTE:",name
        try:
            csock.sendMessage(COBRA_GETATTR, "", getattr(obj, name))
        except CobraClosedException:
            pass

    def handleSetAttr(self, csock, oname, obj, data):
        if verbose: print "SETTING ATTRIBUTE:",data
        name,value = data
        setattr(obj, name, value)
        try:
            csock.sendMessage(COBRA_SETATTR, "", "")
        except CobraClosedException:
            pass

    def handleGoodbye(self, csock, oname, obj, data):
        self.server.decrefObject(oname)
        try:
            csock.sendMessage(COBRA_GOODBYE, "", "")
        except CobraClosedException:
            pass

def isCobraUri(uri):
    try:
        x = urllib2.Request(uri)
        if x.get_type() not in ["cobra","cobrassl"]:
            return False
    except Exception, e:
        return False
    return True

class CobraProxy:
    """
    A proxy object for remote objects shared with Cobra
    """
    def __init__(self, URI, retrymax=None, sslVerify=False, sslKey=None, sslCert=None, timeout=None):
        port = COBRA_PORT
        req = urllib2.Request(URI)
        scheme = req.get_type()
        host = req.get_host()
        name = req.get_selector().strip("/")

        if scheme not in ["cobra","cobrassl"]:
            raise Exception("Invalid scheme: %s" % scheme)

        # Store the ssl stuff in the proxy object to be
        # referenced later...
        if scheme == "cobrassl":
            port = COBRASSL_PORT
            self.__dict__["__cobra_key"] = sslKey
            self.__dict__["__cobra_cert"] = sslCert
            self.__dict__["__cobra_verify"] = sslVerify

        if ":" in host:
            host,portstr = host.split(":")
            port = int(portstr)

        if verbose: print "HOST",host,"PORT",port,"OBJ",name

        # FIXME this should all be newobject easyness...
        self.__dict__["__cobra_uri"] = URI
        self.__dict__["__cobra_scheme"] = scheme
        self.__dict__["__cobra_host"] = host
        self.__dict__["__cobra_port"] = port
        self.__dict__["__cobra_name"] = name
        self.__dict__["__cobra_retrymax"] = retrymax
        self.__dict__["__cobra_timeout"] = timeout

        csock = getCobraSocket(self)
        mtype,rver,data = csock.cobraTransaction(COBRA_HELLO, name, "")
        if mtype == COBRA_ERROR:
            raise data
        if rver != version:
            raise Exception("Server Version Not Supported: %s" % rver)
        if mtype != COBRA_HELLO:
            raise Exception("Invalid Cobra Hello Response")
        self.__dict__["__cobra_methods"] = data

    def __getstate__(self):
        return self.__dict__

    def __setstate__(self, sdict):
        self.__dict__.update(sdict)

    def __hash__(self):
        return hash(self.__dict__["__cobra_uri"])

    def __nonzero__(self):
        return True

    def __repr__(self):
        return str(self)

    def __str__(self):
        return "<CobraProxy %s>" % self.__dict__["__cobra_uri"]

    def __eq__(self, obj):
        if not hasattr(obj, "__dict__"):
            return False

        if not obj.__dict__.has_key("__cobra_uri"):
            return False

        return obj.__dict__["__cobra_uri"] == self.__dict__["__cobra_uri"]

    def __ne__(self, obj):
        if self == obj:
            return False
        return True

    def __setattr__(self, name, value):
        if verbose: print "SETATTR %s %s" % (name, repr(value)[:20])
        csock = getCobraSocket(self)
        oname = self.__dict__["__cobra_name"]
        mtype,name,data = csock.cobraTransaction(COBRA_SETATTR, oname, (name, value))
        if mtype == COBRA_ERROR:
            raise data
        elif mtype == COBRA_SETATTR:
            return
        else:
            raise Exception("Invalid Cobra Response")

    def __getattr__(self, name):
        # Handle methods
        if name == "__getinitargs__":
            raise AttributeError()

        if self.__dict__["__cobra_methods"].get(name, False):
            return CobraMethod(self, name)

        if verbose: print "GETATTR",name
        csock = getCobraSocket(self)
        mtype,name,data = csock.cobraTransaction(COBRA_GETATTR, self.__dict__["__cobra_name"], name)
        if mtype == COBRA_ERROR:
            raise data
        return data

    def __del__(self):
        """
        Tell the server we're done with our reference in case it's refcnt'd
        """
        try:
            csock = getCobraSocket(self)
            csock.cobraTransaction(COBRA_GOODBYE, self.__dict__["__cobra_name"], "")
        except socket.error, e:
            if verbose: print "Probably Harmless: %s" % e
        except CobraException, e:
            if verbose: print "Probably Harmless: %s" % e

def startCobraServer(host="", port=COBRA_PORT):
    global daemon
    if daemon == None:
        daemon = CobraDaemon(host,port)
        daemon.fireThread()
    return daemon

def startCobraSslServer(host="", port=COBRASSL_PORT, sslVerify = False, sslKey = None, sslCert = None):
    global daemon
    if daemon == None:
        daemon = CobraSslDaemon(host,port, sslVerify=sslVerify, sslKey=sslKey, sslCert=sslCert)
        daemon.fireThread()
    return daemon

def shareObject(obj, name=None, doref=False):
    """
    If shareObject is called before startCobraServer 
    or startCobraSslServer, it will call startCobraServer
    """
    global daemon
    if daemon == None:
        startCobraServer()
    return daemon.shareObject(obj, name, doref=doref)

def unshareObject(name):
    return daemon.unshareObject(name)

cobraDevCert = """
-----BEGIN CERTIFICATE-----
MIIFLjCCAxYCCQDEBFr+KgECMzANBgkqhkiG9w0BAQQFADBZMQswCQYDVQQGEwJV
UzEUMBIGA1UECBMLRW5saWdodGVuZWQxJDAiBgNVBAoTG0tlbnNob3RvIFBzeW9w
cyBEaXJlY3RvcmF0ZTEOMAwGA1UEAxMFQ29icmEwHhcNMDcwNDE2MjIxMDM1WhcN
MTcwNDEzMjIxMDM1WjBZMQswCQYDVQQGEwJVUzEUMBIGA1UECBMLRW5saWdodGVu
ZWQxJDAiBgNVBAoTG0tlbnNob3RvIFBzeW9wcyBEaXJlY3RvcmF0ZTEOMAwGA1UE
AxMFQ29icmEwggIiMA0GCSqGSIb3DQEBAQUAA4ICDwAwggIKAoICAQDNHzEgbtJH
9RT7ziUq+xQya2GnXzWPI35wSRvT+q252zqaFhaXQtL7HZxdKeRUI2Xaxm7LyfqA
rxISD8qkNz0zaPOOeVlMthKgxiUgY22qLBJylfa5mXrnRK6sb4GWEUAMzlFBFf5F
yQHUh4jvmtNz/QxAk2pghSySij/+HYxl1VUsGWjE9JA91yqhEAUH4QCCRlm1B+ia
YoY+aaqDDwLFV4mVypPEQLnGX4SBkp1lrUEK+dYLD11kgJT0/8PL+cSmvhI8+NVN
7fk2tlQGiAACB09r7RHUq4ZEOPzEaqkT206OCl5sun0cSd9lmW/atWtPRzJO6WVJ
v/ZfUV2wpcoVtmNu9DKY7yz3JHw7ls8H0cD7SB4l3i6FP/z0TtPyRgr+sJWDc5Ma
sWLuyjCNQfCIepZKthSd2RU+Pkje+Xb5EtS3YdbQ89VGfPU27YzhPfUDQqEj0pbN
WB8jo7NUKjdv2UMI858Kj5Cwof7Nbyq9LQysXW8w4goJmdRKWDMrSBy0FB5m124P
qB6WYfxKMwHo7qjsSASd5N0fFbZ7UZKmGfWGoviPojelL+G4noyCk0rZi8G5sjdC
qVc+WtptLu6rskg9cRIiI88WbJ/6cPp9+JcQ2dSBEaIAo9Z2vlubOWkoJ/tV50g0
6weQpQHHamZoR9lwI09rq2DjzGNAPPrkqwIDAQABMA0GCSqGSIb3DQEBBAUAA4IC
AQCJ/YFgGNC0vtL93ose5kWyY1CH4ieMTcxW+c8UPN+7VKIFJX/uFbyebX7osPYG
gd0VSkT2LC6mGt32Ts7XQ2hoP+D/J83dIdPDaB8r5Bne1vNUItRfQzVB3YUFU87C
ldzwzGBlwe/SJsTAXR+3U2NPmlkicDWKpf2Mo8G1b6pfAV5E2o6MiiOyF+aCiCS/
WOT/PWe08oZoOp3Le+h3NIJLIyWf3Q1iQOLBBIEJFFWlpifjlzpRbIluerD7bWZW
KvbR+MXxiy9nJtJEsHnSDQXFu0F/rf1GLvNCqI2NtLNVxhKM+FF2oHnCk7ITq7yh
DDmV2ImCsMXFcq0z9TxkUj9inby1449miJZxmicAbdQpQktyx5gUmMmMqmwSHnzz
9xHubr2nhowb6rrcd/bF8bCVXiH0AFjQiDV6Fop81JFFmZ616Ac3/agnFjdyvObq
Qn6u2CdbTiNJz8V/E5wkHQ643yXWJSF2qZL9OcvYlyKbWsczUhWtKZy63XPu3mot
xzOwJvzTq1K22lFM1PZOCn1SysBvPHMEBqs+f0tmp/5Z7ZxkCNI52EIwxGY8+z7l
hp7Qv/E5SUlbjDNsVX5UwLo13haVVp9O5CP/Cqt5wDufes7ASjfpAW3GGyltDLn2
6wL5BCH/pVeGN3fyjSEqmZA8FN98iR2xcs6pPtvFvYbeVQ==
-----END CERTIFICATE-----
"""

cobraDevKey = """
-----BEGIN RSA PRIVATE KEY-----
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
-----END RSA PRIVATE KEY-----
"""
