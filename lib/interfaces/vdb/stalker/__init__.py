'''
The stalker subsystem is a breakpoint based coverage tool
'''

import vtrace

import envi
import envi.codeflow as e_codeflow

brskip = (envi.BR_PROC | envi.BR_DEREF)

class StalkerBreak(vtrace.Breakpoint):

    '''
    Stalker breakpoints are added to function entry points
    to trigger code-flow analysis and subsequent block breakpoint
    addition.
    '''

    def __init__(self, address, expression=None):
        vtrace.Breakpoint.__init__(self, address, expression=expression)
        self.fastbreak = True
        self.mymap = None

    def resolvedaddr(self, trace, address):
        vtrace.Breakpoint.resolvedaddr(self, trace, address)
        self.mymap = trace.getMemoryMap(address)

    def notify(self, event, trace):
        self.trace = trace

        # Get out of the way
        self.enabled = False
        self.deactivate(trace)

        breaks = trace.getMeta('StalkerBreaks')
        h = trace.getMeta('StalkerHits')
        h.append(self.address)
        trace.runAgain()

        self.bplist = []   # Block Breaks
        self.sbreaks = []  # Stalker Breaks
        self.scbreaks = [] # Callbreaks

        cf = trace.getMeta('StalkerCodeFlow')
        if cf == None:
            cf = e_codeflow.CodeFlowContext(trace, opcallback=self.opcallback)
            trace.setMeta('StalkerCodeFlow', cf)

        # we need to make sure it points to *our* callback
        cf.opcallback = self.opcallback

        cf.addCodeFlow(self.address, persist=True)

        for va in self.bplist:
            if breaks.get(va):
                continue
            breaks[va] = True
            #print 'block: 0x%.8x' % va
            b = StalkerBlockBreak(va)
            bid = trace.addBreakpoint(b)

        for va in self.sbreaks:
            if breaks.get(va):
                continue
            breaks[va] = True
            #print 'func: 0x%.8x' % va
            b = StalkerBreak(va)
            bid = trace.addBreakpoint(b)

        for va in self.scbreaks:
            if breaks.get(va):
                continue
            breaks[va] = True
            #print 'call: 0x%.8x' % va
            b = StalkerDynBreak(va)
            bid = trace.addBreakpoint(b)

    def opcallback(self, va, op):
        branches = op.getBranches()
        for br,bflags in branches:

            if bflags & envi.BR_DEREF and br != None:
                br = self.trace.readMemoryFormat(br, '<P')[0]

            # For now, we skip all branches to another module
            if br != None and self.trace.getMemoryMap(br) != self.mymap:
                continue

            # Procedural branches to regs etc must be marked
            # Otherwise, add another breakpoint like us
            if bflags & envi.BR_PROC:
                if br == None:
                    self.scbreaks.append(op.va)
                else:
                    self.sbreaks.append(br)
                continue

            if br == None:
                #print 'Skipping a branch from 0x%.8x: %s' % (op.va, repr(op))
                self.scbreaks.append(op.va)
                continue

            # Conditional branches always create new blocks...
            if bflags & envi.BR_COND:
                self.bplist.append(br)
                continue

            # Even non-conditional jmp's will create new blocks for now...
            if br != op.va + len(op):
                self.bplist.append(br)
                continue

class StalkerBlockBreak(vtrace.Breakpoint):
    '''
    A breakpoint object which is put on codeblock boundaries
    to track hits.
    '''

    def __init__(self, address, expression=None):
        vtrace.Breakpoint.__init__(self, address, expression=expression)
        self.fastbreak = True

    def notify(self, event, trace):
        h = trace.getMeta('StalkerHits')
        h.append(self.address)
        self.enabled = False
        self.deactivate(trace)
        trace.runAgain()

class StalkerDynBreak(vtrace.Breakpoint):

    '''
    A breakpoint which is placed on dynamic branches to track
    code flow across them.
    '''

    def __init__(self, address, expression=None):
        vtrace.Breakpoint.__init__(self, address, expression=expression)
        self.fastbreak = True
        self.mymap = None
        self.lasthit = None
        self.lastcnt = 0

    def resolvedaddr(self, trace, address):
        vtrace.Breakpoint.resolvedaddr(self, trace, address)
        self.mymap = trace.getMemoryMap(address)

    def notify(self, event, trace):

        trace.runAgain()

        self.deactivate(trace)
        op = trace.parseOpcode(self.address)
        # Where is the call going?
        dva = op.getOperValue(0, emu=trace)

        if self.lasthit == dva:
            self.lastcnt += 1
        else:
            self.lasthit = dva
            self.lastcnt = 0

        #print 'Dynamic: 0x%.8x: %s -> 0x%.8x' % (self.address, repr(op), dva)
        if trace.getMemoryMap(dva) == self.mymap:
            addStalkerEntry(trace, dva)

        if self.lastcnt > 10: # FIXME what should this be??!?!
            self.lasthit = None
            self.lastcnt = 0
            self.enabled = False
        else:
            self.activate(trace)

def initStalker(trace):
    if trace.getMeta('StalkerBreaks') == None:
        trace.setMeta('StalkerBreaks', {})
        trace.setMeta('StalkerHits', [])

def clearStalkerHits(trace):
    '''
    Clear the stalker hit list for the given trace
    '''
    initStalker(trace)
    trace.setMeta('StalkerHits', [])

def getStalkerHits(trace):
    '''
    Retrieve the list of blocks hit in the current stalker
    '''
    initStalker(trace)
    return trace.getMeta('StalkerHits', [])

def clearStalkerBreaks(trace):
    '''
    Cleanup all stalker breaks and metadata
    '''
    initStalker(trace)
    breaks = trace.getMeta('StalkerBreaks', {})
    trace.setMeta('StalkerCodeFlow', None)
    bpaddrs = list(breaks.keys())
    for va in bpaddrs:
        bp = trace.getBreakpointByAddr(va)
        if bp != None:
            trace.removeBreakpoint(bp.id)
        breaks.pop(va, None)

def resetStalkerBreaks(trace):
    '''
    Re-enable all previously hit stalker breakpoints.
    '''
    initStalker(trace)
    breaks = trace.getMeta('StalkerBreaks', {})
    bpaddrs = list(breaks.keys())
    trace.fb_bp_done = False # FIXME HACK
    for va in bpaddrs:
        bp = trace.getBreakpointByAddr(va)
        if bp != None:
            trace.setBreakpointEnabled(bp.id, enabled=True)

def addStalkerEntry(trace, va):
    '''
    Add stalker coverage beginning with the specified entry point
    '''
    initStalker(trace)
    b = trace.getMeta('StalkerBreaks')
    if b.get(va):
        return
    bp = StalkerBreak(va)
    trace.addBreakpoint(bp)
    b[va] = True

