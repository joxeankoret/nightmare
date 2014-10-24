'''
Underlying platform implementation for kernel debugging
with vmware gdbserver.

Msv1_0SubAuthenticationRoutine

VMWare config options...
debugStub.listen.guest64 = "TRUE" # ends up on port 8864 (or next avail)


# 32 bit target.... ( defaults to port 8832 )
debugStub.listen.guest32 = "TRUE"
debugStub.listen.guest32.remote = "TRUE" # bind to 0.0.0.0 rather than 127.0.0.1
debugStub.hideBreakpoints = "TRUE" # Enable breakpoints

# 64 bit target.... ( defaults to port 8864 )
debugStub.listen.guest64 = "TRUE"
debugStub.listen.guest64.remote = "TRUE" # bind to 0.0.0.0 rather than 127.0.0.1
debugStub.hideBreakpoints = "TRUE" # Enable breakpoints

'''
import PE
import vtrace

import envi.bits as e_bits
import envi.resolver as e_resolv

import vtrace.archs.i386 as vt_i386
import vtrace.platforms.base as vt_base
import vtrace.platforms.win32 as vt_win32
import vtrace.platforms.winkern as vt_winkern
import vtrace.platforms.gdbstub as vt_gdbstub

class VMWareMixin(vt_gdbstub.GdbStubMixin):

    def __init__(self, host=None, port=None):
        vt_gdbstub.GdbStubMixin.__init__(self, host=host, port=port)
        self.bigmask = e_bits.u_maxes[ self.getPointerSize() ]

class VMWare32WindowsTrace(
            vtrace.Trace,
            VMWareMixin,
            vt_i386.i386Mixin,
            vt_base.TracerBase,
            ):

    def __init__(self, host=None, port=None):
        vtrace.Trace.__init__(self, archname='i386')
        vt_base.TracerBase.__init__(self)
        vt_i386.i386Mixin.__init__(self)
        VMWareMixin.__init__(self, host=host, port=port)

        self.setMeta('Format','pe')
        self.setMeta('Platform','Windows')

        self._break_after_bp = False  # we stop directly on the bp addr

    def _getVmwareReg(self, rname):
        '''
        Use VMWare's monitor extension to get a register we wouldn't
        normally have...
        '''
        #fs 0x30 base 0xffdff000 limit 0x00001fff type 0x3 s 1 dpl 0 p 1 db 1
        fsstr = self._monitorCommand('r %s' % rname)
        fsparts = fsstr.split()
        return int(fsparts[3], 16)

    def _gdbJustAttached(self):
        # Implement the callback from the GdbStubMixin parent...

        fsbase = self._getVmwareReg('fs')

        fs_fields = self.readMemoryFormat(fsbase, '<8I')
        # Windows has a self reference in the KPCR...
        if fs_fields[7] != fsbase:
            print [ hex(x) for x in fs_fields ]
            raise Exception('poi(fsbase+(ptr*7)) != fsbase! ( not actually windows? )')


        import vstruct.defs.windows.win_5_1_i386.ntoskrnl as vs_w_ntoskrnl
        self.vsbuilder.addVStructNamespace('nt', vs_w_ntoskrnl)

        self.casesens = False

        kpcr = self.getStruct('nt.KPCR', fsbase)
        kver = self.getStruct('nt.DBGKD_GET_VERSION64', kpcr.KdVersionBlock)

        #print kpcr.tree()
        print kver.tree()

        winver = vt_winkern.win_builds.get( kver.MinorVersion )
        if winver == None:
            winver = 'Untested Windows Build! (%d)' % kver.MinorVersion

        print('vtrace (vmware32): Windows Version: %s' % winver)

        kernbase = kver.KernBase & self.bigmask
        modlist = kver.PsLoadedModuleList & self.bigmask

        self.setVariable('kpcr', fsbase)
        self.setVariable('KernelBase', kernbase)
        self.setVariable('PsLoadedModuleList', modlist)

        #self.platformParseBinary = self.platformParseBinaryPe
        self.fireNotifiers(vtrace.NOTIFY_ATTACH)

        self.addLibraryBase('nt', kernbase, always=True)

        ldr_entry = self.readMemoryFormat(modlist, '<I')[0]
        while ldr_entry != modlist:
            ldte = self.getStruct('nt.LDR_DATA_TABLE_ENTRY', ldr_entry)
            try:
                dllname = self.readMemory(ldte.FullDllName.Buffer, ldte.FullDllName.Length).decode('utf-16le')
                dllbase = ldte.DllBase & self.bigmask
                self.addLibraryBase(dllname, dllbase, always=True)
            except Exception, e:
                print('Trouble while parsing one...')
            ldr_entry = ldte.InLoadOrderLinks.Flink & self.bigmask

        vt_winkern.addBugCheckBreaks(self)

    def normFileName(self, libname):
        basename = libname.split('\\')[-1]
        return basename.split(".")[0].split("-")[0].lower()

    def platformParseBinary(self, filename, baseaddr, normname):
        try:
            pe = PE.peFromMemoryObject(self, baseaddr)
            for rva, ord, name in pe.getExports():
                self.addSymbol(e_resolv.Symbol(name, baseaddr+rva, 0, normname))
        except Exception, e:
            print('Error Parsing Binary (%s): %s' % (normname, e))

    def buildNewTrace(self):
        return VMWare32WindowsTrace( host=self._gdb_host, port=self._gdb_port )

    # FIXME move these to gdbstub

    def isValidPointer(self, addr):
        # Fake this out by attempting to read... ( slow/lame )
        cmd = 'm%x,%x' % (addr, 1)
        pkt = self._cmdTransact(cmd)
        return not pkt.startswith('E')

    def archActivBreakpoint(self, addr):
        self._gdbAddMemBreak(addr, 1)

    def archClearBreakpoint(self, addr):
        self._gdbDelMemBreak(addr, 1)

