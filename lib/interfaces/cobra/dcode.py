"""

Cobra's distributed code module capable of allowing
serialization of code from one system to another.

Particularly useful for clustering and workunit stuff.

"""
import os
import sys
import imp
import cobra

class DcodeFinder(object):
    """
    This is the module finder which is exposed by a dcode
    server to allow clients to attempt to find modules.
    """
    def find_module(self, fullname, uri, path=None):
        # If there are nested module names, they are
        # accounted for in path, so grab just the end
        fullname = fullname.split(".")[-1]
        fobj, filename, typeinfo = imp.find_module(fullname, path)
        if os.path.isdir(filename):
            filename = os.path.join(filename, "__init__.py")

        if not os.path.exists(filename):
            return None

        path = "%s|%s" % (uri,os.path.dirname(filename))
        fbytes = file(filename, "rU").read()
        return DcodeLoader(fbytes, filename, path)

class DcodeLoader(object):

    """
    This object gets pickled by the DcodeFinder and returned
    to the client who calls load_module.
    """

    def __init__(self, fbytes, filename, path):
        object.__init__(self)
        self.fbytes = fbytes
        self.filename = filename
        self.path = path

    def get_source(self, name):
        return self.fbytes

    def load_module(self, fullname):
        mod = sys.modules.get(fullname)
        if mod == None:
            mod = imp.new_module(fullname)
            sys.modules[fullname] = mod
            mod.__file__ = self.filename
            mod.__loader__ = self
            if self.path != None:
                mod.__path__ = [self.path]

            exec self.fbytes in mod.__dict__

        return mod

class DcodeImporter(object):
    """
    This object goes into the client side import path_hooks
    to allow cobra:// uri's to be added to the import path.
    """
    def __init__(self, uri, retrymax=3, timeout=10):
        object.__init__(self)

        if not cobra.isCobraUri(uri):
            raise ImportError

        path = None
        if uri.find("|") != -1:
            uri,path = uri.split("|")
            path = [path,]

        self.uri = uri
        self.path = path

        try:
            self.cobra = cobra.CobraProxy(uri, retrymax=retrymax, timeout=timeout)
        except Exception, e:
            raise ImportError

    def find_module(self, fullname, path=None):
        if path == None:
            path = self.path
        return self.cobra.find_module(fullname, self.uri, path)

def enableDcodeClient():
    """
    Once having called this, a client will be able to add cobra URIs
    to sys.path (one will be added automatically for the optional
    server parameter) and code will be imported via the distributed method.
    """
    if DcodeImporter not in sys.path_hooks:
        sys.path_hooks.append(DcodeImporter)

def addDcodeServer(server, port=None, override=False, ssl=False):
    scheme = "cobra"
    if ssl:
        scheme = "cobrassl"

    if port == None:
        port = cobra.COBRA_PORT

    uri = "%s://%s:%d/DcodeServer" % (scheme, server, port)
    if uri not in sys.path:
        if override:
            sys.path.insert(0, uri)
        else:
            sys.path.append(uri)

def enableDcodeServer():
    cobra.shareObject(DcodeFinder(), "DcodeServer")

