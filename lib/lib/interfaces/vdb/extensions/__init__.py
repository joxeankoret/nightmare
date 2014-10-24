
'''
A package to contain all the extended functionality for platform specific
commands and modules.
'''

__all__ = ['loadExtensions','windows','i386','darwin','amd64','gdbstub','arm']

def loadExtensions(vdb, trace):
    '''
    Actually load all known extensions here.
    '''
    plat = trace.getMeta('Platform').lower()
    arch = trace.getMeta('Architecture').lower()

    if plat in __all__:
        mod = __import__('vdb.extensions.%s' % plat, 0, 0, 1)
        mod.vdbExtension(vdb, trace)

    if arch in __all__:
        mod = __import__('vdb.extensions.%s' % arch, 0, 0, 1)
        mod.vdbExtension(vdb, trace)

