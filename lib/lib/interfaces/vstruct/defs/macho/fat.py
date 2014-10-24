
import vstruct
from vstruct.primitives import *
import vstruct.primitives as vs_prim

class fat_header(vstruct.VStruct):
    def __init__(self):
        vstruct.VStruct.__init__(self, bigend=True)
        self.magic = v_uint32()
        self.nfat_arch = v_uint32()

class fat_arch(vstruct.VStruct):
    def __init__(self):
        vstruct.VStruct.__init__(self, bigend=True)
        self.cputype    = v_uint32()  # cpu specifier (int) */
        self.cpusubtype = v_uint32()  # machine specifier (int) */
        self.offset     = v_uint32()  # file offset to this object file */
        self.size       = v_uint32()  # size of this object file */
        self.align      = v_uint32()  # alignment as a power of 2 */

