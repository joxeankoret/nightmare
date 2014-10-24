"""
A home for the vdb specific memory renderers.
"""

import envi
import envi.bits as e_bits
import envi.memory as e_mem
import envi.memcanvas as e_canvas

class OpcodeRenderer(e_canvas.MemoryRenderer):

    def __init__(self, trace):
        a = trace.getMeta("Architecture")
        self.arch = envi.getArchModule(a)
        self.pwidth = self.arch.getPointerSize()

    def render(self, mcanv, va):
        vastr = self.arch.pointerString(va)
        # NOTE: we assume the memobj is a trace
        trace = mcanv.mem
        sym = trace.getSymByAddr(va)
        if sym != None:
            mcanv.addVaText(str(sym), va=va)
            mcanv.addText(":\n")
        p = trace.readMemory(va, 16)
        op = self.arch.makeOpcode(p, va=va)
        obytes = p[:min(op.size, 8)]

        mcanv.addVaText(vastr, va=va)
        mcanv.addText(": %s " % obytes.encode('hex').ljust(17))
        op.render(mcanv)
        mcanv.addText("\n")
        return len(op)

class SymbolRenderer(e_canvas.MemoryRenderer):
    def __init__(self, trace):
        a = trace.getMeta("Architecture")
        self.arch = envi.getArchModule(a)
        self.pwidth = self.arch.getPointerSize()

    def render(self, mcanv, va):
        # This is only used with tracer based stuff...
        trace = mcanv.mem
        vastr = self.arch.pointerString(va)
        # NOTE: we assume the memobj is a trace
        trace = mcanv.mem
        p = trace.readMemoryFormat(va, 'P')[0]

        isptr = trace.isValidPointer(p)

        pstr = self.arch.pointerString(p)

        mcanv.addVaText(vastr, va=va)
        mcanv.addText(": ")
        if isptr:
            mcanv.addVaText(pstr, p)
        else:
            mcanv.addText(pstr)

        if isptr:
            sym = trace.getSymByAddr(p, exact=False)
            if sym != None:
                mcanv.addText(' %s + %d' % (repr(sym), p-long(sym)))
        mcanv.addText('\n')

        return self.pwidth

class DerefRenderer(e_canvas.MemoryRenderer):
    def __init__(self, trace):
        a = trace.getMeta("Architecture")
        self.arch = envi.getArchModule(a)
        self.pwidth = self.arch.getPointerSize()

    def render(self, mcanv, va):
        vastr = self.arch.pointerString(va)
        # NOTE: we assume the memobj is a trace
        trace = mcanv.mem
        p = trace.readMemoryFormat(va, 'P')[0]

        isptr = trace.isValidPointer(p)

        pstr = self.arch.pointerString(p)

        vareg = ""
        preg = ""

        regs = trace.getRegisters()
        for name,val in regs.items():
            if val == 0:
                continue
            if val == va:
                vareg = "(%s)" % name
            if val == p:
                preg = "(%s)" % name

        bt = trace.getStackTrace()
        if len(bt) > 1:
            for i in range(1, len(bt)):
                spc, sfc = bt[i]
                if sfc == 0:
                    break
                if spc == 0:
                    break
                if va == spc:
                    vareg = "(savepc)"
                if va == sfc:
                    vareg = "(frame%d)" % i
                if p == spc:
                    preg = "(savepc)"
                if p == sfc:
                    preg = "(frame%d)" % i

        vareg = vareg.ljust(8)
        preg = preg.ljust(8)

        #sym = trace.getSymByAddr(va)
        #if sym != None:
            #pstr = repr(sym)

        mcanv.addVaText(vastr, va=va)
        mcanv.addText(" %s: " % vareg)
        if isptr:
            mcanv.addVaText(pstr, p)
        else:
            mcanv.addText(pstr)
        mcanv.addText(preg)
        if isptr:
            try:
                addr,size,perm,fname = trace.getMemoryMap(p)
                pname = e_mem.reprPerms(perm)
                mcanv.addText(" ")
                mcanv.addNameText(pname)
                mcanv.addText(" ")

                bytes = trace.readMemory(p, 32)
                if self.isAscii(bytes):
                    mcanv.addText("'%s'" % bytes.split("\x00")[0])

                elif self.isBasicUnicode(bytes):
                    s = bytes.split("\x00\x00")[0].replace("\x00","")
                    mcanv.addText("u'%s'" % s)

                else:
                    mcanv.addText(bytes.encode('hex'))

            except Exception, e:
                mcanv.addText("ERROR: %s" % e)
        else:
            try:
                for fd,ftype,fname in trace.getFds():
                    if fd == p:
                        mcanv.addText('HANDLE/FD?: %s' % fname)
            except Exception, e:
                pass
        mcanv.addText("\n")

        return self.arch.getPointerSize()

    def isAscii(self, bytes):
        bytes = bytes.split("\x00")[0]
        if len(bytes) < 4:
            return False
        for i in range(len(bytes)):
            o = ord(bytes[i])
            if o < 0x20 or o > 0x7e:
                return False
        return True

    def isBasicUnicode(self, bytes):
        bytes = bytes.split("\x00\x00")[0]
        if len(bytes) < 8:
            return False
        nonull = bytes.replace("\x00", "")
        if (len(bytes) / 2) != len(nonull):
            return False
        return self.isAscii(nonull)
