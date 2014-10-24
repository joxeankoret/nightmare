import os
import tempfile
import threading
import subprocess

import envi.memory as e_mem

import vtrace
import vtrace.archs.arm as v_arm
import vtrace.platforms.base as v_base
import vtrace.platforms.posix as v_posix
import vtrace.platforms.gdbstub as v_gdbstub

from cStringIO import StringIO

platdir = os.path.dirname(__file__)
targdir = '/data/local/tmp/'

gdbserver_arm = 'gdbserver_arm_4.3.3'
gdbserver_arm_path = os.path.join(platdir, 'gdbbins', gdbserver_arm)

gdbserver_arm_targ = targdir + gdbserver_arm

def adbCommand(*argv):
    return subprocess.check_output(argv, stderr=subprocess.PIPE)

def checkGdbServer():
    t = adbCommand('adb','shell','ls',targdir)
    if t.find(gdbserver_arm) == -1:
        adbCommand('adb','push',gdbserver_arm_path,targdir)
        adbCommand('adb','shell','chmod','755', gdbserver_arm_targ)

def openAndroidFile(fname):
    fd = tempfile.NamedTemporaryFile()
    adbCommand('adb','pull', fname, fd.name)
    return file(fd.name, 'r+b')

arm_regfmt = '<16I96sI'
arm_regnames = ["r0","r1","r2","r3","r4","r5","r6","r7","r8","r9","sl","fp","ip","sp", "lr","pc", None, "cpsr"]

class AndroidArmTrace(
        vtrace.Trace,
        v_gdbstub.GdbStubMixin,
        v_arm.ArmMixin,
        v_posix.ElfMixin,
        v_base.TracerBase):

    def __init__(self, avd=None):
        vtrace.Trace.__init__(self, archname='arm')
        v_base.TracerBase.__init__(self)
        v_gdbstub.GdbStubMixin.__init__(self)
        v_arm.ArmMixin.__init__(self)
        v_posix.ElfMixin.__init__(self)

        self._gdbSetRegisterInfo(arm_regfmt, arm_regnames)

        self._gdb_filemagic = '\x7fELF'

        self.setMeta('Platform', 'android')

        self.avd = avd
        self.gdbserver = None

    def platformAttach(self, pid):

        port = 33221

        checkGdbServer()

        gserver = ['adb','shell',gdbserver_arm_targ,'0.0.0.0:%d' % port, '--attach', str(pid) ]

        try:
            self.gdbserver = subprocess.Popen(gserver,
                                              stdout=subprocess.PIPE,
                                              stdin=subprocess.PIPE)

            # Read the "Attached" and "Listening" output (which delays us long
            # enough to connect correctly....)
            # FIXME error check this stuff!
            l1 = self.gdbserver.stdout.readline()
            l2 = self.gdbserver.stdout.readline()

            adbCommand('adb','forward','tcp:%d' % port, 'tcp:%d' % port)

            self._gdb_host = 'localhost'
            self._gdb_port = port

            return v_gdbstub.GdbStubMixin.platformAttach(self, pid)

        except Exception, e:

            if self.gdbserver:
                self.gdbserver.kill()
                self.gdbserver = None

            raise

    def platformGetMaps(self):
        maps = []
        mapsbuf = adbCommand('adb','shell','cat','/proc/%d/maps' % self.pid)
        for line in mapsbuf.splitlines():

            if not line:
                continue

            perms = 0
            sline = line.split(" ")
            addrs = sline[0]
            permstr = sline[1]
            fname = sline[-1].strip()
            addrs = addrs.split("-")
            base = long(addrs[0],16)
            max = long(addrs[1],16)
            mlen = max-base

            if "r" in permstr:
                perms |= e_mem.MM_READ
            if "w" in permstr:
                perms |= e_mem.MM_WRITE
            if "x" in permstr:
                perms |= e_mem.MM_EXEC

            maps.append((base,mlen,perms,fname))

        return maps

    def platformDetach(self):
        if self.gdbserver:
            self.gdbserver.kill()
            self.gdbserver = None

    def platformPs(self):
        ret = []

        output = adbCommand('adb','shell','ps')

        for line in output.split('\n'):
            line = line.strip()

            if not line:
                continue
            if line.startswith('USER'):
                continue

            parts = line.split(None, 8)
            ret.append( (int(parts[1]), parts[8]) )
        return ret

    def platformOpenFile(self, filename):
        return openAndroidFile(filename)
        #output = adbCommand('adb','shell','cat',filename)
        #return StringIO(output)

def getTrace(avd=None):
    # Check for adb in path...
    try:
        output = adbCommand('adb', 'devices')
        lines = output.splitlines()
        if len(lines) <= 2:
            print('Warning: "adb devices" didnt see an Android device, start/attach one!')

    except Exception, e:
        raise Exception('Android "adb" command *must* be in your path!')

    return AndroidArmTrace(avd)

