import re
from collections import deque

from PyQt4 import QtCore, QtGui

import envi.memcanvas as e_memcanvas
import envi.qt.memcanvas as e_memcanvas_qt
import envi.memcanvas.renderers as e_render

import vqt.colors as vq_colors
import vqt.menubuilder as vqt_menu

from vqt.main import idlethread, idlethreadsync

class VQMemoryWindow(QtGui.QWidget):

    __canvas_class__ = e_memcanvas_qt.VQMemoryCanvas

    def __init__(self, memobj, syms=None, parent=None):

        QtGui.QWidget.__init__(self, parent=parent)
        self._mem_obj = memobj

        self.top_box = QtGui.QWidget(parent=self)
        hbox = QtGui.QHBoxLayout(self.top_box)
        hbox.setMargin(2)
        hbox.setSpacing(4)

        self.hist_button = QtGui.QPushButton('History', parent=self.top_box)
        self.hist_button.clicked.connect(self._histButtonClicked)
        self.addr_entry  = QtGui.QLineEdit(parent=self.top_box)
        self.size_entry  = QtGui.QLineEdit(parent=self.top_box)
        self.size_entry.setText('256')
        self.rend_select = QtGui.QComboBox(parent=self.top_box)

        self.mem_history = deque()
        self.mem_canvas = self.__canvas_class__(memobj, syms=syms, parent=self)

        self.mem_canvas.vqAddHotKey(e_memcanvas_qt.KEY_BACKSPACE, self._hotkey_BS)

        self.loadDefaultRenderers()
        self.loadRendSelect()

        self.addr_entry.returnPressed.connect(self._renderMemory)
        self.size_entry.returnPressed.connect(self._renderMemory)

        self.connect(self.rend_select, QtCore.SIGNAL('currentIndexChanged(QString)'), self._renderMemory)

        hbox.addWidget(self.hist_button)
        hbox.addWidget(self.addr_entry)
        hbox.addWidget(self.size_entry)
        hbox.addWidget(self.rend_select)

        vbox = QtGui.QVBoxLayout(self)
        vbox.setMargin(4)
        vbox.setSpacing(4)
        vbox.addWidget(self.top_box)
        vbox.addWidget(self.mem_canvas, stretch=100)

        self.top_box.setLayout(hbox)

        self.setLayout(vbox)
        self.setWindowTitle('Mem: None')

    def _hotkey_BS(self, canv, key):
        if len(self.mem_history) >= 2:
            hinfo = self.mem_history.popleft()
            hinfo = self.mem_history.popleft()
            self._histSelected( hinfo )

    def _histSelected(self, hinfo):
        addrexpr, sizeexpr, rendname = hinfo
        self.addr_entry.setText(addrexpr)
        self.size_entry.setText(sizeexpr)
        self.mem_canvas.setRenderer(rendname)
        self._renderMemory()

    def _histButtonClicked(self):

        menu = vqt_menu.VQMenu('context', parent=self.hist_button)
        menu.splitchar = '&&&&&' # Disable splitting
        for hinfo in self.mem_history:
            addrexpr, sizeexpr, rendname = hinfo
            addr = self._mem_obj.parseExpression(addrexpr)
            menustr = '0x%.8x' % addr
            sym = self._mem_obj.getSymByAddr(addr)
            if sym != None:
                menustr += ' - %s' % repr(sym)
            menu.addField(menustr, self._histSelected, (hinfo,))
        menu.exec_(self.mapToGlobal(self.hist_button.pos()))
        return

    def vqMemNavSlot(self, expr, sizeexpr=None):
        # Used by nav event generators to make us render
        self.addr_entry.setText(expr)
        if sizeexpr != None:
            self.size_entry.setText(sizeexpr)
        self._renderMemory()

    def loadRendSelect(self):
        self.rend_select.clear()
        for name in self.mem_canvas.getRendererNames():
            self.rend_select.addItem(name)

    def loadDefaultRenderers(self):
        self.mem_canvas.addRenderer("bytes",    e_render.ByteRend())
        self.mem_canvas.addRenderer("u_int_16", e_render.ShortRend())
        self.mem_canvas.addRenderer("u_int_32", e_render.LongRend())
        self.mem_canvas.addRenderer("u_int_64", e_render.QuadRend())

    def _getRenderVaSize(self):

        expr = str(self.addr_entry.text())
        sizeexpr = str(self.size_entry.text())

        if not expr:
            return None, None

        if not sizeexpr:
            return None, None

        try:
            addr = self._mem_obj.parseExpression(expr)
        except Exception, e:
            self.mem_canvas.addText('Invalid Address: %s (%s)' % (expr, e))
            return None, None

        try:
            size = self._mem_obj.parseExpression(sizeexpr)
        except Exception, e:
            self.mem_canvas.addText('Invalid Size: %s (%s)' % (expr, e))
            return None, None

        self.setWindowTitle('Mem: %s' % expr)
        return addr, size

    @idlethread
    def _renderMemory(self, *args, **kwargs):

        self.clearText()

        addr, size = self._getRenderVaSize()
        if addr == None:
            return

        expr = str(self.addr_entry.text())
        rname = str(self.rend_select.currentText())
        sizeexpr = str(self.size_entry.text())

        mhist = (expr, sizeexpr, rname)
        if mhist not in self.mem_history:
            self.mem_history.appendleft( mhist )
            while len(self.mem_history) > 100:
                self.mem_history.pop()

        self.mem_canvas.setRenderer(rname)
        self.mem_canvas.renderMemory(addr, size)

    def clearText(self):
        self.mem_canvas.clearCanvas()

