import cgi

import vqt.main as vq_main
import vqt.colors as vq_colors
import envi.qt.html as e_q_html
import envi.memcanvas as e_memcanvas

qt_horizontal   = 1
qt_vertical     = 2

from PyQt4    import QtCore, QtGui, QtWebKit
from vqt.main import idlethread, idlethreadsync

#class memhotkey:
    #def __init__(self, 

KEY_BACKSPACE = 0x1000003
#KEY_SHIFT     = 0x1000020
#KEY_CTRL      = 0x1000022

#KMASK_CTRL  = 0x100
#KMASK_SHIFT = 0x200

QMOD_CTRL   = 0x10000000
QMOD_SHIFT  = 0x02000000


class VQMemoryCanvas(QtWebKit.QWebView, e_memcanvas.MemoryCanvas):

    def __init__(self, mem, syms=None, parent=None):
        QtWebKit.QWebView.__init__(self, parent=parent)
        e_memcanvas.MemoryCanvas.__init__(self, mem, syms=syms)

        self.setContent(e_q_html.template, 'application/xhtml+xml')
        #self.setHtml(e_q_html.template)
        frame = self.page().mainFrame()
        self._canv_cache = None
        self._canv_rend_middle = False

        self._canv_curva = None
        self._canv_rendtagid = '#memcanvas'
        self._canv_hotkeys = {}

        self.page().mainFrame().addToJavaScriptWindowObject('vnav', self)

    def keyPressEvent(self, event):

        key = event.key()
        txt = str(event.text())
        #print 'KEY',hex(key),repr(txt)

        mods = int(event.modifiers())

        keytxt = ''
        if key < 255:

            keytxt = chr(key).lower()

            if mods & QMOD_SHIFT:
                keytxt = keytxt.upper()

            if mods & QMOD_CTRL:
                keytxt = 'ctrl+' + keytxt

        #print 'KEYTXT: %s' % keytxt

        handler = self._canv_hotkeys.get(keytxt)
        if handler == None:
            handler = self._canv_hotkeys.get(key)

        if handler != None:
            handler(self, key)
            event.accept()

        return QtWebKit.QWebView.keyPressEvent(self, event)

    def vqAddHotKey(self, key, callback):
        self._canv_hotkeys[key] = callback

    def renderMemory(self, va, size, rend=None):

        if self._canv_rend_middle:
            vmap = self.mem.getMemoryMap(va)
            origva = va
            va = max(va - size, vmap[0])
            size += size

        ret = e_memcanvas.MemoryCanvas.renderMemory(self, va, size, rend=rend)

        if self._canv_rend_middle:
            self._scrollToVa(origva)

        return ret

    @idlethread
    def _scrollToVa(self, va):
        vq_main.eatevents() # Let all render events go first
        self.page().mainFrame().scrollToAnchor('viv:0x%.8x' % va)

    def _beginRenderMemory(self, va, size, rend):
        self._canv_cache = ''

    def _endRenderMemory(self, va, size, rend):
        self._appendInside(self._canv_cache)
        self._canv_cache = None
        if self._canv_scrolled:
            self._scrollToEnd()

    def _beginRenderVa(self, va):
        self._add_raw('<a name="viv:0x%.8x" id="a_%.8x">' % (va,va))

    def _endRenderVa(self, va):
        self._add_raw('</a>')

    def _beginUpdateVas(self, valist):

        self._canv_cache = ''
        frame = self.page().mainFrame()
        elem = frame.findFirstElement('a#a_%.8x' % valist[0][0])
        elem.prependOutside('<update id="updatetmp"></update>')

        for va,size in valist:
            elem = frame.findFirstElement('a#a_%.8x' % va)
            elem.removeFromDocument()

    def _endUpdateVas(self):
        elem = self.page().mainFrame().findFirstElement('update#updatetmp')
        elem.appendOutside(self._canv_cache)
        elem.removeFromDocument()
        self._canv_cache = None

    def _beginRenderPrepend(self):
        self._canv_cache = ''
        self._canv_ppjump = self._canv_rendvas[0][0]

    def _endRenderPrepend(self):
        frame = self.page().mainFrame()
        elem = frame.findFirstElement(self._canv_rendtagid)
        elem.prependInside(self._canv_cache)
        self._canv_cache = None
        self._scrollToVa(self._canv_ppjump)

    def _beginRenderAppend(self):
        self._canv_cache = ''

    def _endRenderAppend(self):
        frame = self.page().mainFrame()
        elem = frame.findFirstElement(self._canv_rendtagid)
        elem.appendInside(self._canv_cache)
        self._canv_cache = None

    def getNameTag(self, name, typename=None):
        '''
        Return a "tag" for this memory canvas.  In the case of the
        qt tags, they are a tuple of html text (<opentag>, <closetag>)
        '''
        if typename == None:
            typename = 'name'
        return ('<%s class="name_%s" onclick="nameclick(this)">' % (typename,name), '</%s>' % typename)

    def getVaTag(self, va):
        # The "class" will be the same that we get back from goto event
        return ('<va class="va_0x%.8x" ondblclick="vagoto(this)" oncontextmenu="vaclick(this)" onclick="vaclick(this)">' % va, '</va>')

    @QtCore.pyqtSlot(str)  
    def _jsGotoExpr(self, expr):
        # The routine used by the javascript code to trigger nav events
        if self._canv_navcallback:
            self._canv_navcallback(expr)

    @QtCore.pyqtSlot(str)
    def _jsSetCurVa(self, vastr):
        self._canv_curva = int(str(vastr), 0)

    # NOTE: doing append / scroll seperately allows render to catch up
    @idlethread
    def _appendInside(self, text):
        frame = self.page().mainFrame()
        elem = frame.findFirstElement(self._canv_rendtagid)
        elem.appendInside(text)

    @idlethread
    def _scrollToEnd(self):
        vq_main.eatevents() # Let all render events go first
        frame = self.page().mainFrame()
        frame.setScrollBarValue(qt_vertical, 0x0fffffff)

    def _add_raw(self, text):
        # If we are in a call to renderMemory, cache til the end.
        if self._canv_cache != None:
            self._canv_cache += text
            return

        self._appendInside(text)
        if self._canv_scrolled:
            self._scrollToEnd()

    def addText(self, text, tag=None):
        text = cgi.escape(text)
        text = text.replace('\n','<br/>')
        text = text.replace(' ', '&nbsp;')

        if tag != None:
            otag, ctag = tag
            text = otag + text + ctag

        self._add_raw(text)

    @idlethreadsync
    def clearCanvas(self):
        frame = self.page().mainFrame()
        elem = frame.findFirstElement(self._canv_rendtagid)
        elem.setInnerXml('')

