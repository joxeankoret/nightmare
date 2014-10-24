"""
The envi architecuture module for the AMD 64 platform.
"""
import envi
import envi.bits as e_bits
import envi.registers as e_reg
import envi.archs.i386 as e_i386

# We inherit all the regular intel prefixes...
PREFIX_REX   = 0x100000 # Shows that the rex prefix is present
PREFIX_REX_B = 0x010000 # Bit 0 in REX prefix (0x41) means ModR/M r/m field, SIB base, or opcode reg
PREFIX_REX_X = 0x020000 # Bit 1 in REX prefix (0x42) means SIB index extension
PREFIX_REX_R = 0x040000 # Bit 2 in REX prefix (0x44) means ModR/M reg extention
PREFIX_REX_W = 0x080000 # Bit 3 in REX prefix (0x48) means 64 bit operand

# NOTE: some notes from the intel manual...
# REX.W overrides 66, but alternate registers (via REX.B etc..) can have 66 to be 16 bit..
# REX.R only modifies reg for GPR/SSE(SIMD)/ctrl/debug addressing modes.
# REX.X only modifies the SIB index value
# REX.B modifies modrm r/m field, or SIB base (if SIB present), or opcode reg.

# Pre generate these for fast lookup. Because our REX prefixes have the same relative
# bit relationship to eachother, we can cheat a little...
amd64_prefixes = list(e_i386.i386_prefixes)
amd64_prefixes[0x40] = (0x10 << 16)
amd64_prefixes[0x41] = (0x11 << 16)
amd64_prefixes[0x42] = (0x12 << 16)
amd64_prefixes[0x43] = (0x13 << 16)
amd64_prefixes[0x44] = (0x14 << 16)
amd64_prefixes[0x45] = (0x15 << 16)
amd64_prefixes[0x46] = (0x16 << 16)
amd64_prefixes[0x47] = (0x17 << 16)
amd64_prefixes[0x48] = (0x18 << 16)
amd64_prefixes[0x49] = (0x19 << 16)
amd64_prefixes[0x4a] = (0x1a << 16)
amd64_prefixes[0x4b] = (0x1b << 16)
amd64_prefixes[0x4c] = (0x1c << 16)
amd64_prefixes[0x4d] = (0x1d << 16)
amd64_prefixes[0x4e] = (0x1e << 16)
amd64_prefixes[0x4f] = (0x1f << 16)


# NOTE: The REX prefixes don't end up with displayed names

# NOTE: all REX_R registers must *directly* follow their 3 bit variants
#       in the table below
REX_BUMP = 8

amd64regs = [
    ("rax",64),("rcx",64),("rdx",64),("rbx",64),("rsp",64),("rbp",64),("rsi",64),("rdi",64),
    # The amd64 extended GP regs
    ("r8",64),("r9",64),("r10",64),("r11",64),("r12",64),("r13",64),("r14",64),("r15",64),

    ("mm0",64),("mm1",64), ("mm2",64), ("mm3",64), ("mm4",64), ("mm5",64), ("mm6",64), ("mm7",64),

    # SIMD registers
    ("xmm0",128),("xmm1",128),("xmm2",128),("xmm3",128),("xmm4",128),("xmm5",128),("xmm6",128),("xmm7",128),
    # The amd64 extended SIMD regs...
    ("xmm8",128),("xmm9",128),("xmm10",128),("xmm11",128),("xmm12",128),("xmm13",128),("xmm14",128),("xmm15",128),

    # Debug registers
    ("debug0",64),("debug1",64),("debug2",64),("debug3",64),("debug4",64),("debug5",64),("debug6",64),("debug7",64),
    # Extended Debug registers (REX.R)
    ("debug8",64),("debug9",64),("debug10",64),("debug11",64),("debug12",64),("debug13",64),("debug14",64),("debug15",64),

    # Control registers
    ("ctrl0",64),("ctrl1",64),("ctrl2",64),("ctrl3",64),("ctrl4",64),("ctrl5",64),("ctrl6",64),("ctrl7",64),
    # Extended Control registers (REX.R)
    ("ctrl8",64),("ctrl9",64),("ctrl10",64),("ctrl11",64),("ctrl12",64),("ctrl13",64),("ctrl14",64),("ctrl15",64),

    # Test registers
    ("test0", 32),("test1", 32),("test2", 32),("test3", 32),("test4", 32),("test5", 32),("test6", 32),("test7", 32),
    # Segment registers
    ("es", 16),("cs",16),("ss",16),("ds",16),("fs",16),("gs",16),
    # FPU Registers
    ("st0", 128),("st1", 128),("st2", 128),("st3", 128),("st4", 128),("st5", 128),("st6", 128),("st7", 128),
    # Leftovers ;)
    ("eflags", 32), ("rip", 64),
]

# Build up a set of accessable constants
l = locals()
e_reg.addLocalEnums(l, amd64regs)

amd64meta = e_i386.i386meta + [
    ("eax", REG_RAX, 0, 32),
    ("ecx", REG_RCX, 0, 32),
    ("edx", REG_RDX, 0, 32),
    ("ebx", REG_RBX, 0, 32),
    ("esp", REG_RSP, 0, 32),
    ("ebp", REG_RBP, 0, 32),
    ("esi", REG_RSI, 0, 32),
    ("edi", REG_RDI, 0, 32),

    ("ax", REG_RAX, 0, 16),
    ("cx", REG_RCX, 0, 16),
    ("dx", REG_RDX, 0, 16),
    ("bx", REG_RBX, 0, 16),
    ("sp", REG_RSP, 0, 16),
    ("bp", REG_RBP, 0, 16),
    ("si", REG_RSI, 0, 16),
    ("di", REG_RDI, 0, 16),

    ("al", REG_RAX, 0, 8),
    ("cl", REG_RCX, 0, 8),
    ("dl", REG_RDX, 0, 8),
    ("bl", REG_RBX, 0, 8),

    ("ah", REG_RAX, 8, 8),
    ("ch", REG_RCX, 8, 8),
    ("dh", REG_RDX, 8, 8),
    ("bh", REG_RBX, 8, 8),

    # NOTE: with a REX prefix, all ah/ch regs get
    # mapped back to being sil/dil etc...
    ("spl", REG_RSP, 8, 8),
    ("bpl", REG_RBP, 8, 8),
    ("sil", REG_RSI, 8, 8),
    ("dil", REG_RDI, 8, 8),

    # The new GP regs are accessible in all modes.
    ("r8d",  REG_R8,  0, 32),
    ("r9d",  REG_R9,  0, 32),
    ("r10d", REG_R10, 0, 32),
    ("r11d", REG_R11, 0, 32),
    ("r12d", REG_R12, 0, 32),
    ("r13d", REG_R13, 0, 32),
    ("r14d", REG_R14, 0, 32),
    ("r15d", REG_R15, 0, 32),

    ("r8w",  REG_R8,  0, 16),
    ("r9w",  REG_R9,  0, 16),
    ("r10w", REG_R10, 0, 16),
    ("r11w", REG_R11, 0, 16),
    ("r12w", REG_R12, 0, 16),
    ("r13w", REG_R13, 0, 16),
    ("r14w", REG_R14, 0, 16),
    ("r15w", REG_R15, 0, 16),

    ("r8l",  REG_R8,  0, 8),
    ("r9l",  REG_R9,  0, 8),
    ("r10l", REG_R10, 0, 8),
    ("r11l", REG_R11, 0, 8),
    ("r12l", REG_R12, 0, 8),
    ("r13l", REG_R13, 0, 8),
    ("r14l", REG_R14, 0, 8),
    ("r15l", REG_R15, 0, 8),

    # Flags
    ("TF", REG_EFLAGS, 8, 1),
]

# Add the meta's indexes
e_reg.addLocalMetas(l, amd64meta)

# DIS NOTES:
# the REX prefix must be the *last* non escape (0f) prefix

# EMU NOTES:
# In 64 bit mode, all 32 bit dest regs get 0 extended into the rest of the bits
# In 64 bit mode, all 8/16 bit accesses do NOT modify the upper bits
# In 64 bit mode, all near branches, and implicit RSP (push pop) use RIP even w/o REX
# In 64 bit mode, if mod/rm is mod=0 and r/m is 5, it's RIP relative IMM32
import envi.archs.i386.opcode86 as opcode86

class Amd64RipRelOper(envi.Operand):
    def __init__(self, imm, tsize):
        self.imm = imm
        self.tsize = tsize

    def getOperValue(self, op, emu=None):
        if emu == None: return None
        return emu.readMemValue(self.getOperAddr(op, emu), self.tsize)

    def setOperValue(self, op, emu, val):
        emu.writeMemValue(self.getOperAddr(op, emu), val, self.tsize)

    def getOperAddr(self, op, emu=None):
        return op.va + op.size + self.imm

    def isDeref(self):
        return True

    def render(self, mcanv, op, idx):
        destva = op.va + op.size + self.imm
        sym = mcanv.syms.getSymByAddr(destva)

        mcanv.addNameText(e_i386.sizenames[self.tsize])
        mcanv.addText(" [")
        mcanv.addNameText("rip", typename="registers")

        if self.imm > 0:
            mcanv.addText(" + ")
            if sym != None:
                mcanv.addVaText("$%s" % repr(sym), destva)
            else:
                mcanv.addNameText(str(self.imm))
        elif self.imm < 0:
            mcanv.addText(" - ")
            if sym != None:
                mcanv.addVaText("$%s" % repr(sym), destva)
            else:
                mcanv.addNameText(str(abs(self.imm)))
        mcanv.addText("]")

    def repr(self, op):
        return "[rip + %d]" % self.imm

class Amd64Module(e_i386.i386Module):

    def __init__(self):
        envi.ArchitectureModule.__init__(self, "amd64")
        self._arch_dis = Amd64Disasm()

    def getEmulator(self):
        return Amd64Emulator()

    def getPointerSize(self):
        return 8

    def pointerString(self, va):
        return "0x%.8x" % va

    def archGetRegCtx(self):
        return Amd64RegisterContext()

class Amd64RegisterContext(e_reg.RegisterContext):
    def __init__(self):
        self.loadRegDef(amd64regs)
        self.loadRegMetas(amd64meta)
        self.setRegisterIndexes(REG_RIP, REG_RSP)

    def setRegister(self, index, value):
        # NOTE: A special override is needed here because setting "eax" automagicall
        # zero extends into RAX...
        if (index & 0xffff0000) == RMETA_LOW32:
            index = index & 0xffff
        e_reg.RegisterContext.setRegister(self, index, value)

class Amd64Call(envi.CallingConvention):

    def getCallArgs(self, emu, count):
        ret = []
        if count == 0: return ret
        ret.append(emu.getRegister(REG_RCX))
        if count == 1: return ret
        ret.append(emu.getRegister(REG_RDX))
        if count == 2: return ret
        ret.append(emu.getRegister(REG_R8))
        if count == 3: return ret
        ret.append(emu.getRegister(REG_R9))
        if count == 4: return ret
        rsp = emu.getStackCounter()
        stargs = emu.readMemoryFormat(rsp, "<12Q")
        ret.extend(stargs[4:])
        return ret[:count]

    def setReturnValue(self, emu, value, argc):
        rsp = emu.getStackCounter()
        rsp += 8
        emu.setStackCounter(rsp)
        emu.setRegister(REG_RAX, value)

amd64call = Amd64Call()

class Amd64Emulator(Amd64Module, Amd64RegisterContext, e_i386.IntelEmulator):
    def __init__(self):
        e_i386.IntelEmulator.__init__(self)
        # The above sets up the intel reg context, so we smash over it
        Amd64RegisterContext.__init__(self)
        Amd64Module.__init__(self)
        # For the format calls in reading memory
        self.imem_psize = 8
        self.addCallingConvention("amd64call", amd64call)

MODE_16 = 0
MODE_32 = 1
MODE_64 = 2

RMETA_LOW32 = 0x00200000

class Amd64Disasm(e_i386.i386Disasm):

    def __init__(self):
        e_i386.i386Disasm.__init__(self)
        self._dis_prefixes = amd64_prefixes
        self._dis_regctx = Amd64RegisterContext()

        # Over-ride these which are in use by the i386 version of the ASM
        self.ROFFSET_MMX   = e_i386.getRegOffset(amd64regs, "mm0")
        self.ROFFSET_SIMD  = e_i386.getRegOffset(amd64regs, "xmm0")
        self.ROFFSET_DEBUG = e_i386.getRegOffset(amd64regs, "debug0")
        self.ROFFSET_CTRL  = e_i386.getRegOffset(amd64regs, "ctrl0")
        self.ROFFSET_TEST  = e_i386.getRegOffset(amd64regs, "test0")
        self.ROFFSET_SEG   = e_i386.getRegOffset(amd64regs, "es")
        self.ROFFSET_FPU   = e_i386.getRegOffset(amd64regs, "st0")

    # NOTE: Technically, the REX must be the *last* prefix specified

    def _dis_calc_tsize(self, opertype, addrtype, prefixes):
        """
        Use the oper type and prefixes to decide on the tsize for
        the operand.
        """

        mode = MODE_32

        sizelist = opcode86.OPERSIZE.get(opertype, None)
        if sizelist == None:
            raise "OPERSIZE FAIL"

        # NOTE: REX takes precedence over 66
        # (see section 2.2.1.2 in Intel 2a)
        if prefixes & PREFIX_REX_W:

            mode = MODE_64

        elif prefixes & e_i386.PREFIX_OP_SIZE:

            mode = MODE_16

        return sizelist[mode]

    def byteRegOffset(self, val):
        # NOTE: Override this because there is no AH etc in 64 bit mode
        return val + e_i386.RMETA_LOW8

    def extended_parse_modrm(self, bytes, offset, opersize, regbase=0):
        """
        Return a tuple of (size, Operand)
        """
        size = 1
        # FIXME this would be best to not parse_modrm twice.  tweak it.
        mod,reg,rm = self.parse_modrm(ord(bytes[offset]))
        if mod == 0 and rm == 5:
            imm = e_bits.parsebytes(bytes, offset + size, 4, sign=True)
            size += 4
            return(size, Amd64RipRelOper(imm, 4))

        return e_i386.i386Disasm.extended_parse_modrm(self, bytes, offset, opersize, regbase)

    # NOTE: Override a bunch of the address modes to account for REX
    def ameth_0(self, operflags, operval, tsize, prefixes):
        o = e_i386.i386Disasm.ameth_0(self, operflags, operval, tsize, prefixes)
        # If it has a builtin register, we need to check for bump prefix
        if prefixes & PREFIX_REX_B and isinstance(o, e_i386.i386RegOper):
            o.reg += REX_BUMP
        return o

    def ameth_g(self, bytes, offset, tsize, prefixes):
        osize, oper = e_i386.i386Disasm.ameth_g(self, bytes, offset, tsize, prefixes)
        if oper.tsize == 4 and oper.reg != REG_RIP:
            oper.reg += RMETA_LOW32
        if prefixes & PREFIX_REX_R:
            oper.reg += REX_BUMP
        return osize, oper

    def ameth_c(self, bytes, offset, tsize, prefixes):
        osize, oper = e_i386.i386Disasm.ameth_c(self, bytes, offset, tsize, prefixes)
        if prefixes & PREFIX_REX_R:
            oper.reg += REX_BUMP
        return osize,oper

    def ameth_d(self, bytes, offset, tsize, prefixes):
        osize, oper = e_i386.i386Disasm.ameth_d(self, bytes, offset, tsize, prefixes)
        if prefixes & PREFIX_REX_R:
            oper.reg += REX_BUMP
        return osize,oper

    def ameth_v(self, bytes, offset, tsize, prefixes):
        osize, oper = e_i386.i386Disasm.ameth_v(self, bytes, offset, tsize, prefixes)
        if prefixes & PREFIX_REX_R:
            oper.reg += REX_BUMP
        return osize,oper

    # NOTE: The ones below are the only ones to which REX.X or REX.B can apply (besides ameth_0)
    def _dis_rex_exmodrm(self, oper, prefixes):
        # REMEMBER: all extended mod RM reg fields come from the r/m part.  If it
        #           were actually just the reg part, it'd be in one of the above
        #           addressing modes...
        if getattr(oper, "index", None) != None:
            if oper.tsize == 4:
                oper.index += RMETA_LOW32
            if prefixes & PREFIX_REX_X:
                oper.index += REX_BUMP
            # Adjust the size if needed

        # oper.reg will be r/m or SIB base
        if getattr(oper, "reg", None) != None:
            # Adjust the size if needed
            if oper.tsize == 4:
                oper.reg += RMETA_LOW32

            if prefixes & PREFIX_REX_B:
                oper.reg += REX_BUMP

    def ameth_e(self, bytes, offset, tsize, prefixes):
        osize, oper = e_i386.i386Disasm.ameth_e(self, bytes, offset, tsize, prefixes)
        self._dis_rex_exmodrm(oper, prefixes)
        return osize, oper

    def ameth_w(self, bytes, offset, tsize, prefixes):
        osize, oper = e_i386.i386Disasm.ameth_w(self, bytes, offset, tsize, prefixes)
        self._dis_rex_exmodrm(oper, prefixes)
        return osize,oper


