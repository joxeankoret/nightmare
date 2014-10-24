'''
Code for helping out windows kernel debugging...
'''
import vtrace

class KeBugCheckBreak(vtrace.Breakpoint):

    def __init__(self, symname):
        vtrace.Breakpoint.__init__(self, None, expression=symname)
        self.fastbreak = True

    def notify(self, event, trace):
        sp = trace.getStackCounter()
        savedpc, exccode = trace.readMemoryFormat(sp, '<PP')
        trace._fireSignal(exccode)

win_builds = {
    2600: 'Windows XP',
}

def addBugCheckBreaks(trace):
    trace.addBreakpoint(KeBugCheckBreak('nt.KeBugCheck'))
    trace.addBreakpoint(KeBugCheckBreak('nt.KeBugCheckEx'))
