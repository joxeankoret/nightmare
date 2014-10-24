"""
A unified memory analysis view
"""

import os
import gtk
import gtk.gdk as gdk

import vwidget.views as vw_views
from vwidget.main import idlethread, idlethreadsync

import envi
import envi.memcanvas as e_canvas


moddir = os.path.dirname(__file__)

# All normal key codes are the same as
# ord('K').  Some are here for special esc/FN etc treatment
KEYCODE_esc = 0xff1b

class VaTag(vw_views.VRevTextTag):

    def __init__(self, va):
        tname = '%.8x' % va
        vw_views.VRevTextTag.__init__(self, '%.8x' % va)
        self.va = va

class MemoryView(vw_views.VTextView, e_canvas.MemoryCanvas):
    """
    A MemoryCanvas compliant GTK TextView.
    """

    def __init__(self, memobj, syms=None):
        vw_views.VTextView.__init__(self)
        self.textview.set_editable(False)
        e_canvas.MemoryCanvas.__init__(self, memobj, syms=syms)
        self.iter = self.vwGetAppendIter()
        self.lastsize = 32

        # Set this to get gui widget updates in a MemoryWindow
        self.memwin = None

        self.vatag = None
        self.selectva = None

        # Keep "marked" va locations
        self.markmap = {}
        self.beginva = None
        self.endva = None

        self.valist = [] # our "history"
        self.histindex = None

        self.colormap = None

        # Anybody who extends this may by default put a file
        # named memview.conf to describe the default tags
        fullpath = os.path.join(moddir,"memview.conf") 
        self.vwLoadTags(fullpath)

        self.hotkeys = {}
        self.textview.connect("key_press_event", self.keyPressed)
        self.textview.connect("move_cursor", self.cursorMoved)

        self.registerHotKey(KEYCODE_esc, self.goback)

    def setColorMap(self, map):
        oldmap = None
        if self.colormap != None:
            oldmap = self.colormap

        self.colormap = map

        if oldmap:
            for va in oldmap.keys():
                tag = self.getVaTag(va)
                self.vwSetTagColor(tag, "va")

        if self.colormap:
            for va,color in self.colormap.items():
                tag = self.getVaTag(va)
                tag.set_property("background", color)

    def registerHotKey(self, keycode, callback, args=(), kwargs={}):
        self.hotkeys[keycode] = (callback,args,kwargs)

    def keyPressed(self, textview, event):
        hkinfo = self.hotkeys.get(event.keyval)
        if hkinfo == None:
            return
        callback,args,kwargs = hkinfo
        callback(*args, **kwargs)

    def cursorMoved(self, textview, stepsize, stepcount, eselect):
        if stepsize == gtk.MOVEMENT_DISPLAY_LINES:
            mark = self.textbuf.get_insert()
            iter = self.textbuf.get_iter_at_mark(mark)
            lineno = iter.get_line()
            self.setVaFromLine(lineno+stepcount)

#############################################################
# The MemoryCanvas API

    def write(self, msg):
        self.addText(msg)

    @idlethreadsync
    def getTag(self, typename):
        # Return a type colored tag that doesn't
        # do highlight on click etc...
        tag = self.vwGetTag(typename)
        if tag == None:
            tag = vw_views.VTextTag(typename)
            self.vwInitTag(tag, typename)
        return tag

    @idlethreadsync
    def getNameTag(self, tname, typename="name"):
        """
        Get a tag for a unique name
        (so they all highlight on highlight one)
        """
        tag = self.vwGetTag(tname)
        if tag == None:
            tag = vw_views.VRevTextTag(tname)
            self.vwInitTag(tag, typename, self.vwNamedTagEvent)
        return tag

    @idlethreadsync
    def getVaTag(self, va):
        tname = "%.8x" % va
        tag = self.vwGetTag(tname)
        if tag == None:
            #tag = gtk.TextTag(tname)
            tag = VaTag(va)
            self.vwInitTag(tag, "va", self.vaTagEvent)
            #tag.va = va
        return tag

    @idlethread
    def addText(self, text, tag=None):
        if tag == None:
            tag = self.vwGetTag("default")
        self.vwInsertText(text, tag=tag, iter=self.iter)

    @idlethread
    def addVaText(self, text, va):
        tag = self.getVaTag(va)
        self.addText(text, tag=tag)

#############################################################

    def appendHistory(self, va, size=None, rend=None):

        if size == None:
            size = self.lastsize

        if rend == None:
            rend = self.currend

        if self.histindex == None:
            self.histindex = -1
        self.histindex += 1
        self.valist = self.valist[:self.histindex]
        self.valist.append((va,size,rend))

    def checkRender(self, va, size=None, rend=None):
        # Check if the given VA is inside the currently rendered
        # space, and if not, make it there.

        if rend == None:
            rend = self.currend

        if size == None:
            size = self.lastsize

        if (  va < self.beginva or 
              va >= self.endva or
              rend != self.currend ):


            self.render(va, size, rend=rend)

    def goto(self, va, size=None, rend=None):
        if size == None:
            size = self.lastsize
        self.appendHistory(va, size=size, rend=rend)
        self.checkRender(va, size, rend=rend)
        self.__goto(va)

    def goforward(self):
        if self.histindex == None:
            return

        newindex = self.histindex + 1
        if newindex < len(self.valist):
            self.histindex = newindex
            va,size,rend = self.valist[self.histindex]
            self.checkRender(va,size,rend)
            self.__goto(va)

    def goback(self):
        if self.histindex == None:
            return
        if self.histindex > 0:
            self.histindex -= 1
            va,size,rend = self.valist[self.histindex]
            self.checkRender(va,size,rend)
            self.__goto(va)

    def godown(self):
        va,size,rend = self.valist[self.histindex]
        va = self.endva
        self.checkRender(va, size, rend)
        self.__goto(va)

    def goup(self):
        va,size,rend = self.valist[self.histindex]
        va = self.beginva - size
        self.checkRender(va, size, rend)
        self.__goto(va)

    def __goto(self, va):
        # Scroll and highlight.
        mark = self.markmap.get(va)
        while mark == None:
            va -= 1
            mark = self.markmap.get(va)
        self.textview.scroll_to_mark(mark, 0, True, 0, 0.3)

        # Select the specified tag
        vatag = self.getVaTag(va)
        self.vaTagSelector(vatag)

        if self.memwin:
            self.memwin.updateHistoryButtons()
            #self.memwin.eentry.set_text(hex(va))

    @idlethreadsync
    def render(self, va, size, rend=None):
        self.vwClearText()
        self.iter = self.vwGetAppendIter()

        self.beginva = va
        self.endva = va + size

        self.render_noclear(va, size, rend=rend)

    @idlethreadsync
    def render_noclear(self, va, size, rend=None):
        # Use this if you've set up your own iter for a partial
        # re-render and don't want your render call to clear the
        # current canvas or set the iter.

        if rend == None:
            rend = self.currend

        self.lastsize = size
        self.currend = rend # we need this for tag events... store it.

        try:
            endva = va + size
            while va < endva:
                mark = self.textbuf.create_mark(None, self.iter, left_gravity=True)
                self.markmap[va] = mark
                va += rend.render(self, va)
        except Exception, e:
            self.addText("\nException At %s: %s\n" % (hex(va),e))

    def refresh(self, va, size):
        if va < self.beginva or va >= self.endva:
            return

        endva = va+size

        # Find the beginning mark for the change.
        mark = self.markmap.get(va)
        if mark == None:
            print "WARNING: va 0x%.8x has no mark for refresh!" % va
            return

        # Get the start iter
        startiter = self.textbuf.get_iter_at_mark(mark)
        startline = startiter.get_line()

        # Search for the end iter
        endmark = None
        endsearch = endva
        enditer = None
        while endsearch < self.endva:
            endmark = self.markmap.get(endsearch, None)
            if endmark != None:
                enditer = self.textbuf.get_iter_at_mark(endmark)
                break
            endsearch += 1

        if enditer == None:
            enditer = self.textbuf.get_end_iter()

        # Delete the old text
        self.textbuf.delete(startiter, enditer)

        for delva in range(va, endsearch):
            mark = self.markmap.pop(delva, None)
            if mark != None:
                # FIXME make sure parents are using vwClear and deleting marks!
                self.textbuf.delete_mark(mark)

        # we're all cleaned up, lets re-render the area
        self.iter = self.textbuf.get_iter_at_line(startline)

        self.render_noclear(va, size)

        # Because the endmark was left gravity, he stayed at the beginning, move him.
        if endmark != None:
            self.textbuf.move_mark(endmark, self.iter)

        return

    def vwClearText(self):
        vw_views.VTextView.vwClearText(self)
        # FIXME delete marks from textview!
        self.markmap = {}

    def vaTagSelector(self, tag):
        # Check if it's already selected
        if self.vatag == tag:
            return
        if self.vatag != None:
            self.vatag.reverse()
        self.vatag = tag
        self.vatag.reverse()

    def vwNamedTagEvent(self, tag, textview, event, iter):
        self.vwTagEvent(tag, textview, event, iter)
        self.vwTagSelector(tag, textview, event, iter)

    def vwTagEvent(self, tag, textview, event, iter):
        # The first tag on a line is *always* the VA tag
        # for the line.  Update our "position" on clicks
        if event.type == gdk.BUTTON_PRESS:
            self.setVaFromIter(iter)

    # A special tag event handler for VA tags.
    def vaTagEvent(self, tag, textview, event, iter):

        if event.type == gdk._2BUTTON_PRESS:
            self.goto(tag.va)

        elif event.type == gdk.BUTTON_PRESS:
            self.selectva = tag.va
            self.vaTagSelector(tag)

    def setVaFromIter(self, iter):
        lineno = iter.get_line()
        self.setVaFromLine(lineno)

    def setVaFromLine(self, lineno):
        lineiter = self.textbuf.get_iter_at_line(lineno)
        linetags = lineiter.get_tags()
        if len(linetags):
            vatag = linetags[0]
            va = getattr(vatag, "va", None)
            if va != None:
                self.selectva = va
                self.vaTagSelector(vatag)

class ScrolledMemoryView(MemoryView):
    """
    Over-ride some of the MemoryView methods to make this a more
    continuous scrolling kind of canvas (like a CLI)
    """

    @idlethreadsync
    def render(self, va, size, rend=None):
        MemoryView.render(self, va, size, rend=rend)
        self.addText("\n")
        self.vwScrollToBottom()

    @idlethread
    def addText(self, text, tag=None):
        MemoryView.addText(self, text, tag=tag)
        if text.find("\n") != -1:
            self.vwScrollToBottom()

    def goto(self, va, size=None, rend=None):
        if size == None:
            size = self.lastsize
        self.render(va, size, rend=rend)

    def vwClearText(self):
        pass

import vwidget.layout as vw_layout

class MemoryWindow(vw_layout.LayoutWindow):
    def __init__(self, canvas):
        self.canvas = canvas
        vw_layout.LayoutWindow.__init__(self)
        self.vbox = gtk.VBox()
        elabel = gtk.Label(" Memory Expression ")
        slabel = gtk.Label(" Memory Size ")

        self.eentry = gtk.Entry()
        self.sentry = gtk.Entry()
        self.sentry.set_text("256")

        self.nextbutton = gtk.Button()
        i = gtk.image_new_from_stock(gtk.STOCK_GO_FORWARD, gtk.ICON_SIZE_BUTTON)
        self.nextbutton.set_image(i)
        self.nextbutton.connect("clicked", self.goforward)

        self.backbutton = gtk.Button()
        i = gtk.image_new_from_stock(gtk.STOCK_GO_BACK, gtk.ICON_SIZE_BUTTON)
        self.backbutton.set_image(i)
        self.backbutton.connect("clicked", self.goback)

        self.downbutton = gtk.Button()
        i = gtk.image_new_from_stock(gtk.STOCK_GO_DOWN, gtk.ICON_SIZE_BUTTON)
        self.downbutton.set_image(i)
        self.downbutton.connect("clicked", self.godown)

        self.upbutton = gtk.Button()
        i = gtk.image_new_from_stock(gtk.STOCK_GO_UP, gtk.ICON_SIZE_BUTTON)
        self.upbutton.set_image(i)
        self.upbutton.connect("clicked", self.goup)

        hbox = gtk.HBox()

        hbox.pack_start(self.backbutton, expand=False)
        hbox.pack_start(self.nextbutton, expand=False)
        hbox.pack_start(self.upbutton, expand=False)
        hbox.pack_start(self.downbutton, expand=False)
        hbox.pack_start(elabel, expand=False)
        hbox.pack_start(self.eentry, expand=True)
        hbox.pack_start(slabel, expand=False)
        hbox.pack_start(self.sentry, expand=True)

        self.cbox = gtk.combo_box_new_text()
        for name in self.canvas.getRendererNames():
            self.canvas.addRenderer(name, self.canvas.getRenderer(name))
            self.cbox.append_text(name)
        self.cbox.set_active(0)
        hbox.pack_start(self.cbox, expand=False)

        self.vbox.pack_start(hbox, expand=False)
        self.vbox.pack_start(self.canvas, expand=True)
        self.add(self.vbox)

        self.eentry.connect("activate", self.entryActivated)
        self.sentry.connect("activate", self.entryActivated)
        self.cbox.connect("changed", self.updateMemoryView)

        self.canvas.memwin = self
        self.updateHistoryButtons()

    def updateHistoryButtons(self):
        hi = self.canvas.histindex
        vl = self.canvas.valist
        self.nextbutton.set_sensitive(False)
        self.backbutton.set_sensitive(False)
        if hi == None:
            return
        if hi > 0:
            self.backbutton.set_sensitive(True)
        if hi < (len(vl)-1):
            self.nextbutton.set_sensitive(True)

    def goto(self, va, size=None, rend=None):
        self.canvas.goto(va, size=size, rend=rend)
        self.updateHistoryButtons()

    def godown(self, *args):
        self.canvas.godown()
        self.updateHistoryButtons()

    def goup(self, *args):
        self.canvas.goup()
        self.updateHistoryButtons()

    def goforward(self, *args):
        self.canvas.goforward()
        self.updateHistoryButtons()

    def goback(self, *args):
        self.canvas.goback()
        self.updateHistoryButtons()

    def setExpression(self, expr, size="1024"):
        self.eentry.set_text(expr)
        self.sentry.set_text(size)
        self.updateMemoryView()

    def entryActivated(self, *args):
        self.updateMemoryView()
        self.set_title("Memory: %s" % self.eentry.get_text())

    def updateMemoryView(self, *args):

        expr, sizestr, rendname = self.getWindowState()

        # If either string is "", return
        if not expr or not sizestr:
            return

        try:
            # FIXME this is a non-api assured assumption
            va = self.canvas.mem.parseExpression(expr)
        except Exception, e:
            self.canvas.addText("Invalid Expression: %s (%s)" % (expr,str(e)))
            return

        try:
            size = self.canvas.mem.parseExpression(sizestr)
        except Exception, e:
            self.canvas.addText("Invalid Expression: %s (%s)" % (expr,str(e)))
            return

        rend = self.canvas.getRenderer(rendname)
        self.goto(va, size=size, rend=rend)

    def setWindowState(self, state):
        e,s,r = state
        self.eentry.set_text(e)
        self.sentry.set_text(s)
        try:
            ridx = self.canvas.getRendererNames().index(r)
            self.cbox.set_active(ridx)
        except ValueError, e:
            pass
        self.entryActivated()

    def getWindowState(self):
        e = self.eentry.get_text()
        s = self.sentry.get_text()
        renditer = self.cbox.get_active_iter()
        r = self.cbox.get_model().get_value(renditer, 0)
        return (e,s,r)

