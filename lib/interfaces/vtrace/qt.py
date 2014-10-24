from PyQt4 import QtCore, QtGui

import vtrace

import envi.qt as envi_qt

import vqt.tree as vq_tree
import vqt.colors as vq_colors

from envi.threads import firethread
from vqt.main import idlethread, idlethreadsync

'''
QtGui objects which assist in GUIs which use vtrace parts.
'''

class VQTraceNotifier(vtrace.Notifier):
    '''
    A bit of shared mixin code for the handling of vtrace
    notifier callbacks in various VQTreeViews...
    '''
    def __init__(self, trace=None):
        self.trace = trace
        vtrace.Notifier.__init__(self)
        self.trace.registerNotifier(vtrace.NOTIFY_ALL, self)

    @idlethreadsync
    # FIXME this should be part of a shared API!
    def notify(self, event, trace):
        if event in [vtrace.NOTIFY_CONTINUE, vtrace.NOTIFY_DETACH, vtrace.NOTIFY_EXIT]:
            self.setEnabled(False)

        else:
            # If the trace is just going to run again, skip the update.
            if not trace.shouldRunAgain():
                self.setEnabled(True)
                self.vqLoad()

class VQRegisterListModel(vq_tree.VQTreeModel):
    columns = ('Name', 'Hex', 'Dec')

class VQRegistersListView(vq_tree.VQTreeView, VQTraceNotifier):

    '''
    A pure "list view" object for registers
    '''

    def __init__(self, trace=None, parent=None):
        VQTraceNotifier.__init__(self, trace)
        vq_tree.VQTreeView.__init__(self, parent=parent)
        self.setModel(VQRegisterListModel(parent=self))
        self.setAlternatingRowColors(True)
        self.regnames = None
        self.lastregs = {}
        self.regvals = {}

        self.vqLoad()

    def vqLoad(self):

        self.lastregs = self.regvals

        if not self.trace.isAttached():
            self.setEnabled(False)
            return

        if self.trace.isRunning():
            self.setEnabled(False)
            return

        model = VQRegisterListModel(parent=self)
        self.setModel(model)

        regs = self.trace.getRegisters()

        names = self.regnames
        if names == None:
            names = regs.keys()
            names.sort()

        for rname in names:
            rval = regs.get(rname)
            model.append( (rname, '0x%.8x' % rval, rval) )

        self.regvals = regs

class RegColorDelegate(QtGui.QStyledItemDelegate):

    def __init__(self, parent):
        QtGui.QStyledItemDelegate.__init__(self, parent)
        self.reglist = parent

    def paint(self, painter, option, index):
        node = index.internalPointer()
        weight = QtGui.QFont.Normal
        if self.reglist.lastregs.get(node.rowdata[0]) != node.rowdata[2]:
            weight = QtGui.QFont.Bold
        option.font.setWeight(weight)
        return QtGui.QStyledItemDelegate.paint(self, painter, option, index)


class VQRegistersView(QtGui.QWidget):

    '''
    A register view which includes the idea of "sub views" for particular
    sets of registers per-architecture.
    '''

    def __init__(self, trace=None, parent=None):
        QtGui.QWidget.__init__(self, parent=parent)
        self.setWindowTitle('Registers')

        vbox = QtGui.QVBoxLayout(self)
        vbox.setMargin(2)
        vbox.setSpacing(4)

        self.viewnames = QtGui.QComboBox(self)
        self.viewnames.addItem('all')
        self.regviews = {}

        arch = trace.getMeta('Architecture')

        # FIXME make this in envi or something once and for all...

        if arch == 'i386':
            self.regviews['general'] = ['eax','ebx','ecx','edx','esi','edi','ebp','esp','eip']

        elif arch == 'amd64':
            self.regviews['general'] = ['rax','rbx','rcx','rdx','rsi','rdi','rbp','rsp','rip',
                                        'r8','r9','r10','r11','r12','r13','r14','r15']

        for name in self.regviews.keys():
            self.viewnames.addItem(name)

        sig = QtCore.SIGNAL('currentIndexChanged(QString)')
        self.viewnames.connect(self.viewnames, sig, self.regViewNameSelected)

        self.reglist = VQRegistersListView(trace=trace, parent=self)
        self.regdelegate = RegColorDelegate(self.reglist)
        self.reglist.setItemDelegate(self.regdelegate)

        vbox.addWidget(self.viewnames)
        vbox.addWidget(self.reglist)

        self.setLayout(vbox)

    def regViewNameSelected(self, name):
        self.reglist.regnames = self.regviews.get(str(name), None)
        self.reglist.vqLoad()

class VQProcessListModel(vq_tree.VQTreeModel):
    columns = ('Pid','Name')

class VQProcessListView(vq_tree.VQTreeView):
    def __init__(self, trace=None, parent=None):
        vq_tree.VQTreeView.__init__(self, parent=parent)
        if trace == None:
            trace = vtrace.getTrace()
        self.trace = trace

        model = VQProcessListModel(parent=self)
        self.setModel(model)
        self.setAlternatingRowColors(True)

        for pid,name in self.trace.ps():
            model.append((pid,name))

class VQProcessSelectDialog(QtGui.QDialog):

    def __init__(self, trace=None, parent=None):
        QtGui.QDialog.__init__(self, parent=parent)

        self.pid = None

        self.setWindowTitle('Select a process...')

        vlyt = QtGui.QVBoxLayout()
        hlyt = QtGui.QHBoxLayout()

        self.plisttree = VQProcessListView(trace=trace, parent=self)

        hbox = QtGui.QWidget(parent=self)

        ok = QtGui.QPushButton("Ok", parent=hbox)
        cancel = QtGui.QPushButton("Cancel", parent=hbox)

        self.plisttree.doubleClicked.connect( self.dialog_activated )

        ok.clicked.connect(self.dialog_ok)
        cancel.clicked.connect(self.dialog_cancel)

        hlyt.addStretch(1)
        hlyt.addWidget(cancel)
        hlyt.addWidget(ok)
        hbox.setLayout(hlyt)

        vlyt.addWidget(self.plisttree)
        vlyt.addWidget(hbox)
        self.setLayout(vlyt)

        self.resize(300, 500)

    def dialog_activated(self, idx):
        node = idx.internalPointer()
        if node:
            self.pid = node.rowdata[0]
            self.accept()

    def dialog_ok(self):
        for idx in self.plisttree.selectedIndexes():
            node = idx.internalPointer()
            if node:
                self.pid = node.rowdata[0]
                break
        self.accept()

    def dialog_cancel(self):
        self.reject()

@idlethreadsync
def getProcessPid(trace=None, parent=None):
    d = VQProcessSelectDialog(trace=trace, parent=parent)
    r = d.exec_()
    return d.pid

class FileDescModel(vq_tree.VQTreeModel):
    columns = ('Fd','Type','Name')

class VQFileDescView(vq_tree.VQTreeView, VQTraceNotifier):

    def __init__(self, trace, parent=None):
        VQTraceNotifier.__init__(self, trace)
        vq_tree.VQTreeView.__init__(self, parent=parent)
        self.setWindowTitle('File Descriptors')
        self.setModel(FileDescModel(parent=self))
        self.vqLoad()

    def vqLoad(self):

        if not self.trace.isAttached():
            self.setEnabled(False)
            return

        if self.trace.isRunning():
            self.setEnabled(False)
            return

        model = FileDescModel(parent=self)
        for fd,fdtype,bestname in self.trace.getFds():
            model.append((fd, fdtype, bestname))
        self.setModel(model)

class VQTraceToolBar(QtGui.QToolBar, vtrace.Notifier):

    def __init__(self, trace, parent=None):
        QtGui.QToolBar.__init__(self, parent=parent)
        vtrace.Notifier.__init__(self)
        self.trace = trace

        self.setObjectName('VtraceToolbar')

        self.attach_action = self.addAction('Attach')
        self.attach_action.setStatusTip('Attach to a process')
        self.attach_action.triggered.connect(self.actAttach)

        self.detach_action = self.addAction('Detach')
        self.detach_action.setStatusTip('Detach from current process')
        self.detach_action.triggered.connect(self.actDetach)

        self.continue_action = self.addAction('Continue')
        self.continue_action.setStatusTip('Continue current process')
        self.continue_action.triggered.connect(self.actContinue)

        self.break_action = self.addAction('Break')
        self.break_action.setStatusTip('Break current process')
        self.break_action.triggered.connect(self.actBreak)

        self.stepi_action = self.addAction('Stepi')
        self.stepi_action.setStatusTip('Single step the current process')
        self.stepi_action.triggered.connect(self.actStepi)

        trace.registerNotifier(vtrace.NOTIFY_ALL, self)
        self._updateActions(trace.isAttached(), trace.isRunning())

    def actAttach(self, *args, **kwargs):
        pid = getProcessPid(trace=self.trace)
        if pid != None:
            firethread(self.trace.attach)(pid)

    def actDetach(self, thing):
        if self.trace.isAttached():
            firethread(self.trace.detach)()

    def actContinue(self, thing):
        firethread(self.trace.run)()

    def actBreak(self, thing):
        if self.trace.getMeta('PendingBreak'):
            return
        self.trace.setMeta('PendingBreak', True)
        firethread(self.trace.sendBreak)()

    def actStepi(self, thing):
        firethread(self.trace.stepi)()

    @idlethread
    def _updateActions(self, attached, running):
        if not attached:
            self.attach_action.setEnabled(True)
            self.detach_action.setEnabled(False)
            self.continue_action.setEnabled(False)
            self.break_action.setEnabled(False)
            self.stepi_action.setEnabled(False)
        else:
            if running:
                self.attach_action.setEnabled(False)
                self.detach_action.setEnabled(False)
                self.continue_action.setEnabled(False)
                self.break_action.setEnabled(True)
                self.stepi_action.setEnabled(False)
            else:
                self.attach_action.setEnabled(False)
                self.detach_action.setEnabled(True)
                self.continue_action.setEnabled(True)
                self.break_action.setEnabled(True)
                self.stepi_action.setEnabled(True)

    def notify(self, event, trace):
        if event == vtrace.NOTIFY_DETACH:
            self._updateActions(False, False)

        elif event == vtrace.NOTIFY_CONTINUE:
            self._updateActions(True, True)

        else:
            self._updateActions(trace.isAttached(), trace.shouldRunAgain())

class VQMemoryMapView(envi_qt.VQMemoryMapView, VQTraceNotifier):
    '''
    A memory map view which is sensitive to the status of a
    trace object.
    '''
    def __init__(self, trace, parent=None):
        VQTraceNotifier.__init__(self, trace)
        envi_qt.VQMemoryMapView.__init__(self, trace, parent=parent)

    def vqLoad(self):

        if not self.trace.isAttached():
            self.setEnabled(False)
            return

        if self.trace.isRunning():
            self.setEnabled(False)
            return

        envi_qt.VQMemoryMapView.vqLoad(self)

class VQThreadListModel(vq_tree.VQTreeModel):
    columns = ('Thread Id','Thread Info', 'State')

class VQThreadsView(vq_tree.VQTreeView, VQTraceNotifier):

    def __init__(self, trace=None, parent=None, selectthread=None):
        # selectthread is an optional endpoint to connect to
        VQTraceNotifier.__init__(self, trace)
        vq_tree.VQTreeView.__init__(self, parent=parent)
        self.setWindowTitle('Threads')
        self.setModel(VQThreadListModel(parent=self))
        self.setAlternatingRowColors(True)
        self.vqLoad()
        self.selectthread = selectthread

    def selectionChanged(self, selected, deselected):
        idx = self.selectedIndexes()[0]
        node = idx.internalPointer()
        if node:
            self.trace.selectThread(node.rowdata[0])

        return vq_tree.VQTreeView.selectionChanged(self, selected, deselected)

    def vqLoad(self):

        if not self.trace.isAttached():
            self.setEnabled(False)
            return

        if self.trace.isRunning():
            self.setEnabled(False)
            return

        model = VQThreadListModel(parent=self)

        stid = self.trace.getMeta('ThreadId')
        for i, (tid, tinfo) in enumerate(self.trace.getThreads().items()):
            state = ''
            if self.trace.isThreadSuspended(tid):
                state = 'suspended'
            model.append((tid, tinfo, state))

        self.setModel(model)
