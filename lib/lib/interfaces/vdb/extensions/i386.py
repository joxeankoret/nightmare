
import envi.archs.i386 as e_i386

def eflags(vdb, line):
    """
    Show the status of the eflags register bits.

    Usage: eflags
    """
    t = vdb.getTrace()
    ef = t.getRegisterByName("eflags")
    vdb.vprint("%16s: %s" % ("Carry", bool(ef & e_i386.EFLAGS_CF)))
    vdb.vprint("%16s: %s" % ("Parity", bool(ef & e_i386.EFLAGS_PF)))
    vdb.vprint("%16s: %s" % ("Adjust", bool(ef & e_i386.EFLAGS_AF)))
    vdb.vprint("%16s: %s" % ("Zero", bool(ef & e_i386.EFLAGS_ZF)))
    vdb.vprint("%16s: %s" % ("Sign", bool(ef & e_i386.EFLAGS_SF)))
    vdb.vprint("%16s: %s" % ("Trap", bool(ef & e_i386.EFLAGS_TF)))
    vdb.vprint("%16s: %s" % ("Interrupt", bool(ef & e_i386.EFLAGS_IF)))
    vdb.vprint("%16s: %s" % ("Direction", bool(ef & e_i386.EFLAGS_DF)))
    vdb.vprint("%16s: %s" % ("Overflow", bool(ef & e_i386.EFLAGS_OF)))

def vdbExtension(vdb, trace):
    vdb.config.set('Aliases','db','mem -F bytes')
    vdb.config.set('Aliases','dw','mem -F u_int_16')
    vdb.config.set('Aliases','dd','mem -F u_int_32')
    vdb.config.set('Aliases','dq','mem -F u_int_64')
    vdb.config.set('Aliases','dr','mem -F "Deref View"')
    vdb.config.set('Aliases','ds','mem -F "Symbols View"')
    vdb.registerCmdExtension(eflags)

