
import envi.cli as e_cli
import envi.archs.arm.thumb as e_thumb

def thumb(db, line):
    '''
    Disassemble thumb instructions from the given address.

    Usage: thumb <addr_exp>
    '''
    t = db.getTrace()

    d = e_thumb.ArmThumbDisasm()

    argv = e_cli.splitargs(line)
    size = 20
    argc = len(argv)
    if argc == 0:
        addr = t.getProgramCounter()
    else:
        addr = t.parseExpression(argv[0])

    if argc > 1:
        size = t.parseExpression(argv[1])

    bytes = t.readMemory(addr, size)
    offset = 0

    db.vprint("Dissassembly:")
    while offset < size:
        va = addr + offset
        op = d.disasm(bytes, offset, va)
        obytes = bytes[offset:offset+len(op)]


        db.canvas.addVaText('0x%.8x' % va, va=va)
        db.canvas.addText(": %s " % obytes.encode('hex').ljust(17))
        op.render(db.canvas)
        db.canvas.addText("\n")

        offset += len(op)

def vdbExtension(db, trace):
    vdb.config.set('Aliases','db','mem -F bytes')
    vdb.config.set('Aliases','dw','mem -F u_int_16')
    vdb.config.set('Aliases','dd','mem -F u_int_32')
    vdb.config.set('Aliases','dq','mem -F u_int_64')
    vdb.config.set('Aliases','dr','mem -F "Deref View"')
    vdb.config.set('Aliases','ds','mem -F "Symbols View"')
    db.registerCmdExtension(thumb)

