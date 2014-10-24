"""
A layout manager for gtk windows.
"""

import gtk
import cPickle as pickle

class LayoutWindow(gtk.Window):

    lyt_restore = True

    def getWindowName(self):
        return self.__class__.__name__

    def getWindowState(self):
        return None

    def setWindowState(self, state):
        return None

    def getGeometry(self):
        """
        Returns a tuple of (x, y, xsize, ysize) for later use in setGeometry()
        """
        x, y = self.get_position()
        xsize, ysize = self.get_size()
        return (x, y, xsize, ysize)

    def setGeometry(self, geom):
        self.move(geom[0], geom[1])
        self.resize(geom[2], geom[3])

class LayoutManager:

    def __init__(self):
        self.windows = []
        self.winclasses = {}
        self.defaultgeom = {}

    def addWindowClass(self, cls, args=(), defgeom=None, clsname=None):
        if clsname == None:
            clsname = cls.__name__
        self.winclasses[clsname] = (cls,args)
        self.defaultgeom[clsname] = defgeom

    def getWindowClass(self, name):
        return self.winclasses.get(name)[0]

    def createWindow(self, clsname):
        clstup = self.winclasses.get(clsname)
        if clstup == None:
            raise Exception("Layout manager doesn't know how to make %s" % clsname)
        cls, args = clstup
        win = cls(*args)
        self.manageWindow(win)
        return win

    def getOrCreateWindow(self, name):
        '''
        Get an existing instance of the given window type.  If one does not
        exist, make one instead.
        '''
        for win in self.getManagedWindows():
            if win.getWindowName() == name:
                return win
        return self.createWindow(name)

    def loadLayoutFile(self, fd):
        try:
            for line in fd.readlines():

                clsname, geom, state = line.split(':', 2)

                clstup = self.winclasses.get(clsname)
                if clstup == None:
                    print "ERROR: unregistered class in layout: %s" % clsname
                    continue

                cls, args = clstup

                win = cls(*args)
                win.setGeometry(eval(geom))
                try:
                    win.setWindowState(eval(state))
                except Exception, e:
                    print "ERROR: Failed to set window state: %s %s" % (clsname, e)

                self.__trackWindow(win)

            return True

        except Exception, e:
            print 'Layout Error: %s' % e
            return False

    def saveLayoutFile(self, fd):
        """
        You *must* call the save layout routine *before* the gtk teardown.
        """
        wlist = []
        for win in self.windows:
            if win.lyt_restore:
                geom = win.getGeometry()
                state = win.getWindowState()
                wlist.append((win.getWindowName(), geom, state))
                fd.write('%s:%s:%s\n' % (win.getWindowName(), repr(geom), repr(state)))

    def __trackWindow(self, win):
        self.windows.append(win)
        win.connect("delete-event", self._windowDeleted)
        win.show_all()

    def getManagedWindows(self):
        return list(self.windows)

    def manageWindow(self, window):
        self.__trackWindow(window)
        geom = self.defaultgeom.get(window.__class__.__name__)
        if geom != None:
            window.setGeometry(geom)

    def _windowDeleted(self, window, event):
        try:
            self.windows.remove(window)
        except ValueError, e:
            pass

    def deleteAllWindows(self, omit=None):
        for win in self.windows:
            if win == omit:
                continue
            win.emit('delete_event', None)
            win.destroy()

