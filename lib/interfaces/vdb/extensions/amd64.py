
def vdbExtension(vdb, trace):
    vdb.config.set('Aliases','db','mem -F bytes')
    vdb.config.set('Aliases','dw','mem -F u_int_16')
    vdb.config.set('Aliases','dd','mem -F u_int_32')
    vdb.config.set('Aliases','dq','mem -F u_int_64')
    vdb.config.set('Aliases','dr','mem -F "Deref View"')
    vdb.config.set('Aliases','ds','mem -F "Symbols View"')
