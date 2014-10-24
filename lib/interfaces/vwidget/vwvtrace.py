import envi.memory as e_mem
import vtrace
import gtk
import vwidget.views as vw_views

from envi.threads import firethread
from vwidget.main import idlethread, idlethreadsync

class VtraceView:
    def __init__(self, trace):
        self.trace = trace

    def setTrace(self, trace):
        self.trace = trace

    def traceIsReady(self):
        if self.trace.isAttached() and not self.trace.isRunning():
            return True
        return False

class ProcessListView(VtraceView, vw_views.VTreeView):
    __cols__ = (
        (None, 0, object),
        ("Pid", 1, int),
        ("Name", 2, str),
    )

    def __init__(self, trace):
        VtraceView.__init__(self, trace)
        vw_views.VTreeView.__init__(self)

    def vwLoad(self):
        self.vwClear()
        for pid,name in self.trace.ps():
            self.model.append((None,pid,name))

class SelectProcessDialog(gtk.Dialog):
    def __init__(self, trace):
        buttons=(gtk.STOCK_CANCEL,gtk.RESPONSE_CANCEL,gtk.STOCK_OPEN,gtk.RESPONSE_OK)
        gtk.Dialog.__init__(self, "Select a process...", buttons=buttons)
        self.proclist = ProcessListView(trace)
        self.vbox.pack_start(self.proclist, expand=True)
        self.proclist.treeview.connect("row_activated", self.procListActivated)
        self.proclist.treeview.connect("cursor_changed", self.procListSelected)
        self.pid = None
        self.resize(300, 600)

    def procListActivated(self, *args):
        self.response(gtk.RESPONSE_OK)

    def procListSelected(self, *args):
        self.pid = self.proclist.vwGetSelected(1)

    def selectProcess(self):
        self.show_all()
        resp = self.run()
        self.hide()
        if resp == gtk.RESPONSE_OK:
            return self.pid
        return None

class TraceToolBar(gtk.Toolbar, vtrace.Notifier):
    def __init__(self, trace):
        gtk.Toolbar.__init__(self)
        vtrace.Notifier.__init__(self)
        self.trace = trace
        self.battach = gtk.ToolButton(gtk.STOCK_ADD)
        self.bdetach = gtk.ToolButton(gtk.STOCK_REMOVE)
        self.bcontin = gtk.ToolButton(gtk.STOCK_MEDIA_PLAY)
        self.bbreak  = gtk.ToolButton(gtk.STOCK_MEDIA_PAUSE)
        self.bstep   = gtk.ToolButton(gtk.STOCK_GO_FORWARD)
        #self.bstepo  = gtk.ToolButton(gtk.STOCK_GOTO_LAST)

        self.battach.connect("clicked", self.attach)
        self.battach.set_property("label", "Attach")
        self.bdetach.connect("clicked", self.detach)
        self.bdetach.set_property("label", "Detach")
        self.bcontin.connect("clicked", self.tcontinue)
        self.bcontin.set_property("label", "Continue")
        self.bbreak.connect("clicked", self.tbreak)
        self.bbreak.set_property("label", "Break")
        self.bstep.connect("clicked", self.tstep)
        self.bstep.set_property("label", "Step")
        #self.bstepo.connect("clicked", self.tstep)
        #self.bstepo.set_property("label", "Step Over")

        self.insert(self.battach, -1)
        self.insert(self.bdetach, -1)
        self.insert(self.bcontin, -1)
        self.insert(self.bbreak,  -1)
        self.insert(self.bstep,  -1)

        self.wantsnotattached = [self.battach,]
        self.wantsrunning = [self.bbreak,]
        self.wantsnotrunning = [self.bdetach,self.bcontin, self.bstep]

        trace.registerNotifier(vtrace.NOTIFY_ALL, self)

        self.updateButtons(trace.isAttached(), trace.isRunning())

        self.activateList(self.wantsrunning, True)
        self.activateList(self.wantsnotrunning, True)
        self.activateList(self.wantsnotattached, True)

    @idlethread
    def updateButtons(self, attached, running):
        self.activateList(self.wantsnotattached, not attached)
        if attached:
            self.activateList(self.wantsrunning, running)
            self.activateList(self.wantsnotrunning, not running)
        else:
            self.activateList(self.wantsrunning, False)
            self.activateList(self.wantsnotrunning, False)
            
    def activateList(self, objs, sens):
        for o in objs:
            o.set_sensitive(sens)

    @firethread
    def tstep(self, button):
        self.trace.stepi()

    @firethread
    def tbreak(self, button):
        if self.trace.getMeta('PendingBreak'):
            return
        self.trace.setMeta('PendingBreak', True)
        self.trace.sendBreak()

    @firethread
    def tcontinue(self, button):
        self.trace.run()

    def attach(self, button):
        dia = SelectProcessDialog(self.trace)
        pid = dia.selectProcess()
        if pid != None:
            self._doattach(pid)

    @firethread
    def _doattach(self, pid):
        self.trace.attach(pid)

    @firethread
    def detach(self, button):
        if self.trace.isAttached():
            self.trace.detach()

    def notify(self, event, trace):
        if event == vtrace.NOTIFY_DETACH:
            self.updateButtons(False, False)

        elif event == vtrace.NOTIFY_CONTINUE:
            self.updateButtons(True, True)

        else:
            self.updateButtons(trace.isAttached(), trace.shouldRunAgain())

class MemoryMapView(VtraceView, vw_views.VTreeView):
    __cols__ = (
        (None, 0, int),
        ("Base", 1, str),
        ("Size", 2, int),
        ("Perms", 3, str),
        ("File", 4, str),
    )

    def __init__(self, trace):
        VtraceView.__init__(self, trace)
        vw_views.VTreeView.__init__(self)

    def vwLoad(self):
        if self.traceIsReady():
            self.vwClear()
            maps = self.trace.getMemoryMaps()
            for base,size,perms,fname in maps:
                pname = e_mem.reprPerms(perms)
                self.model.append((base, "0x%.8x" % base, size, pname, fname))

class FileDescView(VtraceView, vw_views.VTreeView):
    __cols__ = (
        (None, 0, object),
        ("Fd", 1, str),
        ("Type", 2, int),
        ("Name", 3, str),
    )

    def __init__(self, trace):
        VtraceView.__init__(self, trace)
        vw_views.VTreeView.__init__(self)

    def vwLoad(self):
        if self.traceIsReady():
            self.vwClear()
            for fd,fdtype,bestname in self.trace.getFds():
                self.model.append((None, fd, fdtype, bestname))

