
import os

from threading import Thread

import gtk
import vwidget
import vwidget.main as vw_main
import vwidget.windows as vw_windows

class ScriptThread(Thread):
    def __init__(self, cobj, locals):
        Thread.__init__(self)
        self.setDaemon(True)
        self.cobj = cobj
        self.locals = locals

    def run(self):
        try:
            exec(self.cobj, self.locals)
        except Exception, e:
            print "Script Error: ",e

class PyDialog(vw_windows.VWindow):
    def __init__(self, locals=None):
        dname = os.path.dirname(vwidget.__file__)
        fname = os.path.join(dname, "pydialog.glade")
        vw_windows.VWindow.__init__(self, fname, None)
        if locals == None:
            locals = {}
        self.locals = locals

    def PyDialogRun(self, button):
        buffer = self.getWidget("PyDialogText").get_buffer()
        start, end = buffer.get_bounds()
        script = buffer.get_text(start,end)
        self.runPython(script)

    def runPython(self, pystring):
        """
        Extend and over-ride this for any special handling...
        """
        cobj = compile(pystring, "pydialog_exec.py", "exec")
        sthr = ScriptThread(cobj, self.locals)
        sthr.start()
        # FIXME set button insensitive and have ScriptThread take
        # a reference to the dialog and change it back when run is complete

