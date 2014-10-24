
"""
A package to contain all the extended functionality for platform specific
commands and modules.
"""

__all__ = ["loadGuiExtensions","windows"]

def loadGuiExtensions(vdb, mainwin):
    """
    Actually load all known extensions here.
    """
    trace = vdb.getTrace()
    plat = trace.getMeta("Platform").lower()
    arch = trace.getMeta("Architecture").lower()

    if plat in __all__:
        mod = __import__("vdb.gui.extensions.%s" % plat, 0, 0, 1)
        mod.vdbGuiExtension(vdb, mainwin)

    if arch in __all__:
        mod = __import__("vdb.gui.extensions.%s" % arch, 0, 0, 1)
        mod.vdbGuiExtension(vdb, mainwin)

