'''
Gui objects for things in the envi package.
'''

from PyQt4 import QtCore, QtGui

import envi.memory as e_mem

import vqt.tree as vq_tree

class VQMemoryMapView(vq_tree.VQTreeView):

    def __init__(self, mem, parent=None):
        cols = ('Address','Size','Perms','Filename')
        vq_tree.VQTreeView.__init__(self, parent=parent, cols=cols)
        self.mem = mem
        self.vqLoad()
        self.vqSizeColumns()
        self.setWindowTitle('Memory Maps')

    def vqLoad(self):
        model = self.model()
        for mva, msize, mperm, mfile in self.mem.getMemoryMaps():
            pstr = e_mem.reprPerms(mperm)
            model.append(('0x%.8x' % mva, msize, pstr, mfile))
        self.setModel(model)

