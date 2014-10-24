
from types import *
from vtrace import *

import sys
import vdb
import gtk
import gtk.gdk as gdk
import pygtk
import pydoc
import struct
import getopt
import inspect
import gtk.glade
import traceback
import threading

import time
import pango
import gobject
import vtrace
import vwidget.main as vw_main
import vdb.gui.extensions

import vstruct
import vstruct.primitives as vs_prims

import vwidget.layout as vw_layout
import vwidget.memview as vw_memview
import vwidget.vwvtrace as vw_vtrace
import vwidget.views as vw_views

from envi.threads import firethread
from vwidget.main import idlethread, idlethreadsync

symtype_names = {
    SYM_MISC:"Unknown",
    SYM_GLOBAL:"Global",
    SYM_LOCAL:"Local",
    SYM_FUNCTION:"Function",
    SYM_SECTION:"Section",
    SYM_META:"Meta"}

def hex(num):
    return "0x%.8x" % num

stylerc = """

style "kenshoto" {

    font = "Monospace 10"

    bg[NORMAL] = {0.1, 0.1, 0.1}
    fg[NORMAL] = {0.0, 1.0, 0.0}

    bg[SELECTED] = {0.0, 1.0, 0.0}
    fg[SELECTED] = {0.0, 0.0, 0.0}

    bg[PRELIGHT] = {0.0, 1.0, 0.0}
    fg[PRELIGHT] = {0.0, 0.0, 0.0}

    bg[ACTIVE] = {0.0, 1.0, 0.0}
    fg[ACTIVE] = {0.0, 0.0, 0.0}

    bg[INSENSITIVE] = {0.2, 0.2, 0.2}
    fg[INSENSITIVE] = {1.0, 1.0, 1.0}

}

#widget_class "*" style "kenshoto"

gtk-font-name = "Monospace 10"

"""

class VdbGui(vw_layout.LayoutManager, Notifier):

    def __init__(self, db, ismain=True):
        vw_layout.LayoutManager.__init__(self)

        self.db = db
        db.gui = self
        self.db.registerNotifier(NOTIFY_ALL, self)
        self.ismain = ismain

        self.winactive = False

        gtk.rc_parse_string(stylerc)

        defgeom = (20,20,600,450)
        self.defgeom = defgeom

        self.addWindowClass(VdbMainWindow, args=(db,self), defgeom=defgeom)
        self.addWindowClass(VdbMemoryWindow, args=(db,self), defgeom=defgeom)
        self.addWindowClass(VdbMemoryMapWindow, args=(db,self), defgeom=defgeom)
        self.addWindowClass(VdbFileDescWindow, args=(db,self), defgeom=defgeom)
        self.addWindowClass(VdbRegisterWindow, args=(db,self), defgeom=defgeom)

        mainwin = None
        if self.db.vdbhome:
            lfile = os.path.join(self.db.vdbhome, "vdb.lyt2")
            if os.path.exists(lfile):
                self.loadLayoutFile(file(lfile,"rb"))

        self.mainwin = self.getOrCreateWindow('VdbMainWindow')

        t = self.db.trace
        if t.isAttached() and not t.isRunning():
            self.setTraceWindowsActive(True)
        else:
            self.setTraceWindowsActive(False)

        vdb.gui.extensions.loadGuiExtensions(db, self)

    def addExtensionWindow(self, name, winclass):
        self.addWindowClass(winclass, args=(self.db, self), defgeom=self.defgeom, clsname=name)
        self.mainwin.menubar.addField("Extensions.%s" % name, self.createExtensionWindow, args=(name,))

    def createExtensionWindow(self, item, name):
        self.createWindow(name)

    def saveVdbLayout(self, *args):
        if self.db.vdbhome:
            lfile = os.path.join(self.db.vdbhome, "vdb.lyt2")
            self.saveLayoutFile(file(lfile, "wb"))

    def createWindow(self, clsname):
        win = vw_layout.LayoutManager.createWindow(self, clsname)
        win.setTraceWindowActive(self.winactive)
        return win

    def setTraceWindowsActive(self, active=True):
        self.winactive = active
        for win in self.getManagedWindows():
            try:
                win.setTraceWindowActive(active)
            except Exception, e:
                #FIXME ugly 
                print "ERROR: setTraceWindowsActive() for %s: %s" % (win.__class__.__name__, e)

    @idlethreadsync
    def notify(self, event, trace):

        if event in [vtrace.NOTIFY_CONTINUE, vtrace.NOTIFY_DETACH, vtrace.NOTIFY_EXIT]:
            self.setTraceWindowsActive(False)

        else:
            # If the trace is just going to run again, skip the update.
            if not trace.shouldRunAgain():
                self.setTraceWindowsActive(True)

class VdbWindow(vw_layout.LayoutWindow):
    """
    A VDB window is the basis for all vdb GUI windows.
    """
    def __init__(self, db, gui):
        vw_layout.LayoutWindow.__init__(self)
        self.db = db
        self.gui = gui

    def setTraceWindowActive(self, active):
        pass

class VdbRegisterWindow(VdbWindow):

    def __init__(self, db, gui):
        VdbWindow.__init__(self, db, gui)
        self.set_title("Registers")
        trace = vdb.VdbTrace(db)
        self.regview = vw_views.VTextView()
        self.regview.textview.set_editable(False)
        arch = trace.getMeta("Architecture")
        self.reglist = db.config.get("RegisterView",arch).split(",")
        self.add(self.regview)

        self.regs = {}
        self.lastthread = -1

    def getRegTag(self, regname):
        tag = self.regview.vwGetTag(regname)
        if tag == None:
            tag = gtk.TextTag(regname)
            self.regview.vwInitTag(tag, "register")
        return tag

    def getVaTag(self, va):
        vaname = "%.8x" % va
        tag = self.regview.vwGetTag(vaname)
        if tag == None:
            tag = gtk.TextTag(vaname)
            self.regview.vwInitTag(tag, "va", self.vaTagEvent)
            tag.va = va
        return tag

    def vaTagEvent(self, tag, textview, event, iter):
        if event.type == gdk._2BUTTON_PRESS:
            memwin = self.gui.createWindow("VdbMemoryWindow")
            memwin.setExpression("0x%.8x" % tag.va)

    def update(self):
        trace = self.db.getTrace()
        thrid = trace.getMeta("ThreadId")
        if thrid != self.lastthread:
            self.regs = {}

        regs = trace.getRegisters()
        self.regview.vwClearText()

        iter = self.regview.vwGetAppendIter()

        for rname in self.reglist:
            newval = regs.get(rname, 0)
            oldval = self.regs.get(rname, newval)

            deftag = self.regview.vwGetTag("default")
            regtag = self.getRegTag(rname)
            vatag = deftag
            if trace.isValidPointer(newval):
                vatag = self.getVaTag(newval)

            self.regview.vwInsertText(rname, iter=iter, tag=regtag)
            self.regview.vwInsertText(": ", iter=iter, tag=deftag)
            self.regview.vwInsertText("0x%.8x" % newval, iter=iter, tag=vatag)
            self.regview.vwInsertText("\n", iter=iter, tag=deftag)

        self.lastthread = thrid
        self.regs = regs

    def setTraceWindowActive(self, active):
        if active:
            self.regview.set_sensitive(True)
            self.update()
        else:
            self.regview.set_sensitive(False)

class VdbViewWindow(VdbWindow):

    def __init__(self, db, gui, vtclass):
        VdbWindow.__init__(self, db, gui)
        trace = vdb.VdbTrace(db)
        self.vtview = vtclass(trace)
        self.add(self.vtview)

    def setTraceWindowActive(self, active):
        if active:
            self.vtview.set_sensitive(True)
            self.vtview.vwLoad()
        else:
            self.vtview.set_sensitive(False)

class VdbFileDescWindow(VdbViewWindow):
    def __init__(self, db, gui):
        VdbViewWindow.__init__(self, db, gui, vw_vtrace.FileDescView)
        self.set_title("File Descriptors")

class VdbMemoryMapWindow(VdbViewWindow):
    def __init__(self, db, gui):
        VdbViewWindow.__init__(self, db, gui, vw_vtrace.MemoryMapView)
        self.vtview.treeview.connect("row_activated", self.mapActivated)
        self.set_title("Memory Maps")

    def getWindowName(self):
        return self.__class__.__name__

    def mapActivated(self, tree, path, column):
        model = self.vtview.model
        iter = model.get_iter(path)
        base = model.get_value(iter, 0)
        memwin = self.gui.createWindow("VdbMemoryWindow")
        memwin.setExpression("0x%.8x" % base)

import vwidget.windows as vw_windows

class VdbMainWindow(vw_windows.MainWindow):

    def __init__(self, db, gui):

        trace = vdb.VdbTrace(db)
        self.db = db

        # The vdb instance *is* the cli object.
        vw_windows.MainWindow.__init__(self, db, trace, syms=trace)

        self.gui = gui
        self.set_title("Vdb")
        self.menubar.addField("File.Save.Layout", self.file_save_layout)
        self.menubar.addField("File.Save.Snapshot", self.file_save_snapshot)
        self.menubar.addField("File.Quit", self.file_quit)
        self.menubar.addField("Edit.Copy", self.file_edit_copy)
        self.menubar.addField("View.Memory Window", self.file_view_memwin)
        self.menubar.addField("View.Memory Maps", self.file_view_memmaps)
        self.menubar.addField("View.Registers", self.file_view_registers)
        self.menubar.addField("View.File Descriptors", self.file_view_filedesc)
        self.menubar.addField("Tools.Python", self.tools_python)

        # On delete, lets save off the layout...
        self.connect('delete_event', self._mainDelete)

        #descr = pango.FontDescription("Monospace 12")
        #entry.modify_font(descr)

    def getMainToolbar(self):
        trace = vdb.VdbTrace(self.db)
        return vw_vtrace.TraceToolBar(trace)

    def setTraceWindowActive(self, active):
        pass

    def tools_python(self, *args):
        import vwidget.pydialog as vw_pydialog
        l = vtrace.VtraceExpressionLocals(vdb.VdbTrace(self.db))
        p = vw_pydialog.PyDialog(l)
        p.show()

    def file_view_registers(self, *args):
        self.gui.createWindow("VdbRegisterWindow")

    def file_view_memmaps(self, *args):
        self.gui.createWindow("VdbMemoryMapWindow")

    def file_view_memwin(self, *args):
        self.gui.createWindow("VdbMemoryWindow")

    def file_view_filedesc(self, *args):
        self.gui.createWindow("VdbFileDescWindow")

    def file_edit_copy(self, *args):
        print "copy"

    def _mainDelete(self, *args):
        self.db.do_quit("")
        self.db.shutdown.set()
        self.gui.saveVdbLayout()
        self.gui.deleteAllWindows(omit=self)
        if self.gui.ismain:
            vw_main.shutdown()

    def file_quit(self, *args):
        self.gui.deleteAllWindows()

    def file_save_snapshot(self, *args):
        print "Save Snapshot!"

    def file_save_layout(self, *args):
        print "SAVE LAYOUT"

class VdbMemoryView(vw_memview.MemoryView):
    """
    Extend so we can override right click popups
    """
    def __init__(self, trace, vdbwin):
        vw_memview.MemoryView.__init__(self, trace, syms=trace)
        self.vdbwin = vdbwin

    def checkRender(self, va, size=None, rend=None):
        self.render(va, size, rend)

    def vwGetPopup(self, textview, menu):
        va = self.selectva

        if va != None:

            pos = 0

            # Breakpoints
            bm = gtk.MenuItem("Breakpoint")
            bm.connect("activate", self.popBreakpoint, va)
            menu.insert(bm, pos)
            pos += 1

            rm = gtk.MenuItem("Run To Here")
            rm.connect("activate", self.popRunToHere, va)
            menu.insert(rm, pos)
            pos += 1

            # Watchpoints
            wmenu = gtk.Menu()
            wm = gtk.MenuItem("Watch")
            wm.set_submenu(wmenu)

            wmread = gtk.MenuItem("Reads")
            wmread.connect("activate", self.popWatchRead, va)
            wmwrite = gtk.MenuItem("Writes")
            wmwrite.connect("activate", self.popWatchWrite, va)

            wmenu.append(wmread)
            wmenu.append(wmwrite)

            menu.insert(wm, pos)
            pos += 1

            # Renderers
            rmenu = gtk.Menu()
            mn = gtk.MenuItem("Render")
            mn.set_submenu(rmenu)
            for name in self.vdbwin.db.canvas.getRendererNames():
                i = gtk.MenuItem(name)
                i.connect("activate", self.reRender, name)
                rmenu.append(i) 

            menu.insert(mn,pos)
            pos += 1

        menu.show_all()

    @firethread
    def popRunToHere(self, item, va):
        self.vdbwin.db.trace.run(until=va)

    def popBreakpoint(self, item, va):
        bp = vtrace.Breakpoint(va)
        self.vdbwin.db.trace.addBreakpoint(bp)

    def popWatchRead(self, item, va):
        bp = vtrace.Watchpoint(va, perms="r")
        self.vdbwin.db.trace.addBreakpoint(bp)

    def popWatchWrite(self, item, va):
        bp = vtrace.Watchpoint(va)
        self.vdbwin.db.trace.addBreakpoint(bp)

    def reRender(self, item, name):
        self.vdbwin.setWindowState(("0x%.8x" % self.selectva, "256", name))

class VdbMemoryWindow(vw_memview.MemoryWindow):
    def __init__(self, db, gui):
        self.db = db
        self.gui = gui
        trace = vdb.VdbTrace(db)
        canvas = VdbMemoryView(trace, self)
        for rname in db.canvas.getRendererNames():
            canvas.addRenderer(rname, db.canvas.getRenderer(rname))

        vw_memview.MemoryWindow.__init__(self, canvas)

    def setTraceWindowActive(self, active=True):
        if active:
            self.vbox.set_sensitive(True)
            self.updateMemoryView()
        else:
            self.vbox.set_sensitive(False)

    def updateMemoryView(self, *args):

        trace = self.db.getTrace()
        if (not trace.isAttached()) or trace.isRunning():
            return

        return vw_memview.MemoryWindow.updateMemoryView(self, *args)

def main(db):
    vw_main.mainthread()
    vg = VdbGui(db)
    vw_main.main()
