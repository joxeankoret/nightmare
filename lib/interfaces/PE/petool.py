
import os
import sys

import PE

'''
For now, all this does is rename files to their exportname and version info.
(more to come is likely)
'''

if __name__ == "__main__":

    vsver = None
    expname = None

    pe = PE.peFromFileName(sys.argv[1])

    expname = pe.getExportName()

    dirname = os.path.dirname(sys.argv[1])

    vs = pe.getVS_VERSIONINFO()
    if vs != None:
        vsver = vs.getVersionValue('FileVersion')
        #newpath = os.path.join(dirname, '

    if vsver != None and expname != None:
        expname = expname.split('.')[0].lower()
        vsver = vsver.split()[0]
        destpath = os.path.join(dirname, '%s_%s.dll' % (expname, vsver))
        print 'Renaming to %s' % destpath
        os.rename(sys.argv[1], destpath)

