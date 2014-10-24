"""
A module for GUI management of cobra.cluster clients
calling into a server.
"""

import gtk

import cobra
import cobra.cluster as c_cluster

import vwidget.util as vw_util
import vwidget.views as vw_views

from vwidget.main import idlethread

class ClusterServerView(vw_views.VTreeView,
                        c_cluster.ClusterCallback):
    """
    A cluster server status GUI.
    """
    __cols__ = (
        ("Id", 0, int),
        ("Client",1,str),
        ("Status",2,str),
        ("Percent",3,int)
    )

    def __init__(self):
        vw_views.VTreeView.__init__(self)
        # Hook all the GUI callbacks in the server.
        #FIXME make this a callback object in the server
        self.id_iter = {}
        # Setup a progress bar renderer
        self.treeview.remove_column(self.treeview.get_column(3))
        col = vw_util.makeColumn("Percent", 3, cell=gtk.CellRendererProgress(), links={"value":3})
        self.treeview.append_column(col)

    # Mirror the server interfaces so it's easy to keep things straight
    def workGotten(self, server, work):
        ip,port = cobra.getCallerInfo()
        self._dispWorkGotten(work, ip, port)

    @idlethread
    def _dispWorkGotten(self, work, ip, port):
            iter = self.model.append((work.id, ip, "Starting", 0))
            self.id_iter[work.id] = iter

    @idlethread
    def workDone(self, server, work):
        iter = self.id_iter.pop(work.id, None)
        if iter != None:
            self.vwRemove(iter)

    def workTimeout(self, server, work):
        self.workDone(server, work)

    def workCanceled(self, server, work):
        self.workDone(server, work)

    def workFailed(self, server, work):
        self.workDone(server, work)

    @idlethread
    def workStatus(self, server, workid, status):
        iter = self.id_iter.get(workid)
        self.model.set_value(iter, 2, status)

    @idlethread
    def workCompletion(self, server, workid, percent):
        iter = self.id_iter.get(workid)
        self.model.set_value(iter, 3, percent)

