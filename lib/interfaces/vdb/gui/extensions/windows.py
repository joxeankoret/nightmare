
import os
import vwidget
import vwidget.windows as vw_windows
import vwidget.util as vw_util
import vtrace.tools.win32heap as win32heap

import vdb
import vdb.gui

import envi.memcanvas as e_canvas
import vwidget.memview as vw_memview

import gtk
import pango

busy_color = (0xff, 0, 0)
def_color  = (0, 0xff, 0)

class VdbHeapRenderer(e_canvas.MemoryRenderer):
    """
    A renderer which knows how to show heap chunks
    (only to be used on aligned addresses, our parent window
    takes care of that)
    """
    def __init__(self, trace):
        self.trace = trace

    def getPad(self, buf, size):
        return " " * (size-len(buf))

    def isAscii(self, buf):
        for b in buf:
            v = ord(b)
            if v == 0:
                continue
            if v < 0x20 or v >= 0x7f:
                return False
        return True

    def render(self, canvas, va):
        chunk = win32heap.Win32Chunk(self.trace, va)
        size = len(chunk)
        canvas.addVaText("0x%.8x" % va, va=va)
        canvas.addText(": ")
        sizestr = str(len(chunk))
        sizepad = self.getPad(sizestr, 7)
        canvas.addText("CHUNK:%s" % sizepad)
        canvas.addNameText(sizestr, name="chunk:%d" % size)
        canvas.addText(" %s" % chunk.reprFlags())
        canvas.addText("\n")

        dva = chunk.getDataAddress()
        dsize = chunk.getDataSize()
        #r = min(32, dsize)
        canvas.addVaText("0x%.8x" % dva, va=dva)
        dsizestr = str(dsize)
        dsizepad = self.getPad(dsizestr, 7)
        canvas.addText(": %s" % dsizepad)
        canvas.addNameText(dsizestr, name="data:%d" % dsize)
        canvas.addText(": ")

        bytes = self.trace.readMemory(dva, dsize)

        if not chunk.isBusy():
            flink, blink = self.trace.readMemoryFormat(dva, "PP")
            canvas.addText("FLINK: ")
            canvas.addVaText("0x%.8x" % flink, va=flink)
            canvas.addText(" BLINK: ")
            canvas.addVaText("0x%.8x" % blink, va=blink)
            canvas.addText(" leftovers: %s" % bytes[8:8+32].encode('hex'))

        else:
            if self.isAscii(bytes):
                canvas.addText(bytes[:128].replace("\x00",""))
            else:
                canvas.addText("%s" % bytes[:32].encode('hex'))

        canvas.addText("\n")

        return size

class VdbHeapView(vw_memview.MemoryView):

    def render(self, va, size, rend=None):
        trace = self.mem
        heap, seg, chunk = win32heap.getHeapSegChunk(trace, va)
        va = seg.address

        # FIXME if is valid
        last = seg.getLastChunk()
        size = (last.address+len(last))-va

        vw_memview.MemoryView.render(self, va, size, rend=rend)


class VdbHeapWindow(vw_memview.MemoryWindow):
    def __init__(self, db, gui):
        self.db = db
        self.gui = gui
        self.trace = vdb.VdbTrace(db)

        canvas = VdbHeapView(self.trace, syms=self.trace)
        canvas.addRenderer("Windows Heap", VdbHeapRenderer(self.trace))
        vw_memview.MemoryWindow.__init__(self, canvas)

    # These are straight stolen from vdb gui
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

class Win32HeapWindow(vw_windows.VWindow):
    def __init__(self, db):
        vw_windows.VWindow.__init__(self, os.path.join(vdb.basepath,"glade","Win32Heap.glade"), None)
        self.vdb = db
        self.font = pango.FontDescription("Monospace 10")
        self.setupHeapTree()
        self.setupChunkList()
        self.spaceview = vwidget.SpaceView([], dwidth=40)
        hb = self.getWidget("hbox1")
        hb.pack_start(self.spaceview, expand=False)
        self.spaceview.show()
        hb.resize_children()

    def chunkListActivated(self, tree, path, column):
        model = tree.get_model()
        iter = model.get_iter(path)
        chunk = model.get_value(iter, 0)
        vdb.gui.MemoryWindow(self.vdb, "0x%.8x" % chunk.address, len_expr=str(len(chunk)))

    def heapTreeActivated(self, tree, path, column):
        model = tree.get_model()
        iter = model.get_iter(path)
        o = model.get_value(iter, 0)
        if isinstance(o, win32heap.Win32Heap):
            if tree.row_expanded(path):
                tree.collapse_row(path)
            else:
                tree.expand_row(path, False)
        elif isinstance(o, win32heap.Win32Segment):
            self.updateChunkList(o)

    def updateWindow(self, trace):
        self.updateHeapTree()

    def setupChunkList(self):
        tree = self.getWidget("Win32ChunkList")
        tree.modify_font(self.font)
        col1 = vw_util.makeColumn("Chunkaddr", 1)
        col2 = vw_util.makeColumn("Size", 2)
        col3 = vw_util.makeColumn("Busy", 3) # FIXME make a picture?
        col4 = vw_util.makeColumn("Bytes", 4)
        tree.append_column(col1)
        tree.append_column(col2)
        tree.append_column(col3)
        tree.append_column(col4)
        store =  gtk.ListStore(object,str,str,str,str)
        tree.set_model(store)

    def updateChunkList(self, seg):
        """
        Because this is already parsing chunks, we'll have this update
        the segment view as well.
        """
        tree = self.getWidget("Win32ChunkList")
        model = tree.get_model()
        model.clear()

        spaces = []
        for c in seg.getChunks():

            if c.isBusy():
                color = busy_color
                bstr = "X"
            else:
                color = def_color
                bstr = ""

            bytes = c.getDataBytes(maxsize=10)
            r = ""
            for b in bytes:
                ob = ord(b)
                if ob >= 0x20 and ob < 0x7f:
                    r += b
                else:
                    r += "."

            spaces.append((c.address, len(c), color, r))
            model.append((c, "0x%.8x" % c.address, len(c), bstr, r))

        self.spaceview.updateSpaces(spaces)

    def setupHeapTree(self):
        tree = self.getWidget("Win32HeapTree")
        tree.modify_font(self.font)
        col1 = vw_util.makeColumn("Heap", 1)
        col2 = vw_util.makeColumn("Segment", 2)
        tree.append_column(col1)
        tree.append_column(col2)
        store =  gtk.TreeStore(object,str,str)
        tree.set_model(store)
        self.updateHeapTree(tree)

    def updateHeapTree(self, tree=None):
        if tree == None:
            tree = self.getWidget("Win32HeapTree")
        t = self.vdb.getTrace()
        model = tree.get_model()
        model.clear()
        if not t.isAttached():
            return

        # Populate the heap list
        for h in win32heap.getHeaps(t):
            #i = model.append(None, (h,"0x%.8x" % h.address,"0x%.8x" % int(h.heap.Flags),""))
            for s in h.getSegments():
                i = model.append(None, (s, "0x%.8x" % h.address,"0x%.8x" % s.address))
                model.append(i, (None, repr(h.heap), repr(s.seg)))

def heapview(db, line):
    """
    Open a Win32 Heap View window.

    Usage: heapview
    """
    Win32HeapWindow(db)

def vdbGuiExtension(db, gui):
    db.registerCmdExtension(heapview)
    gui.addExtensionWindow("Windows Heap", VdbHeapWindow)

