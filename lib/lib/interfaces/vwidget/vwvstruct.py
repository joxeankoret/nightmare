
"""
GUI widgets for use in vstruct enabled applications
"""

import gtk
import inspect
import vstruct
import vstruct.builder as vs_builder
import vstruct.primitives as vs_prims

import vwidget.main as vw_main
import vwidget.util as vw_util
import vwidget.views as vw_views

target_entries = [('example', gtk.TARGET_SAME_APP, 0)]

def selectStructure(vsbuilder, parent=None):
    dia = SelectStructureDialog(vsbuilder, parent=parent)
    return dia.selectStructure()

def selectNamespace(parent=None):
    dia = SelectNamespaceDialog(parent=parent)
    return dia.selectNamespace()

class SelectStructureDialog(gtk.Dialog):
    def __init__(self, vsbuilder, parent=None):
        buttons=(gtk.STOCK_CANCEL,gtk.RESPONSE_CANCEL,gtk.STOCK_OPEN,gtk.RESPONSE_OK)
        gtk.Dialog.__init__(self, "Select a structure...", buttons=buttons, parent=parent)
        self.selector = VStructBuilderView(vsbuilder)
        self.vbox.pack_start(self.selector, expand=True)
        self.selector.treeview.connect("row_activated", self.nsActivated)
        self.selector.treeview.connect("cursor_changed", self.nsSelected)
        self.modinfo = None
        self.resize(400, 600)

    def nsActivated(self, *args):
        self.response(gtk.RESPONSE_OK)

    def nsSelected(self, *args):
        self.modinfo = self.selector.vwGetSelected(0)

    def selectStructure(self):
        self.show_all()
        resp = self.run()
        self.hide()
        if resp == gtk.RESPONSE_OK:
            return self.modinfo
        return None

class SelectNamespaceDialog(gtk.Dialog):
    def __init__(self, parent=None):
        buttons=(gtk.STOCK_CANCEL,gtk.RESPONSE_CANCEL,gtk.STOCK_OPEN,gtk.RESPONSE_OK)
        gtk.Dialog.__init__(self, "Select a structure namespace...", buttons=buttons, parent=parent)
        self.selector = VStructNamespaceSelector()
        self.vbox.pack_start(self.selector, expand=True)
        self.selector.treeview.connect("row_activated", self.nsActivated)
        self.selector.treeview.connect("cursor_changed", self.nsSelected)
        self.modinfo = None
        self.resize(400, 600)

    def nsActivated(self, *args):
        self.response(gtk.RESPONSE_OK)

    def nsSelected(self, *args):
        nspace = self.selector.vwGetSelected(2)
        modname = self.selector.vwGetSelected(0)
        if modname:
            self.modinfo = (nspace, modname)

    def selectNamespace(self):
        self.show_all()
        resp = self.run()
        self.hide()
        if resp == gtk.RESPONSE_OK:
            return self.modinfo
        return None

class VStructNamespaceSelector(vw_views.VTreeView):
    __model_class__ = gtk.TreeStore
    __cols__ = (
        (None, 0, object),
        ('Subsystem', 1, str),
        ('Module Name', 2, str),
    )

    def __init__(self):
        vw_views.VTreeView.__init__(self)

    def vwLoad(self):
        self.model.clear()

        win = self.model.append(None, (None, 'windows', ''))
        xp_i386_user = self.model.append(win, (None, 'Windows XP i386 Userland', ''))
        self.model.append(xp_i386_user, ('vstruct.defs.windows.win_5_1_i386.ntdll','', 'ntdll'))

        xp_i386_kern = self.model.append(win, (None, 'Windows XP i386 Kernel', ''))
        self.model.append(xp_i386_kern, ('vstruct.defs.windows.win_5_1_i386.ntoskrnl','', 'nt'))
        self.model.append(xp_i386_kern, ('vstruct.defs.windows.win_5_1_i386.win32k','', 'win32k'))

        win7_amd64_user = self.model.append(win, (None, 'Windows 7 amd64 Userland', ''))
        self.model.append(win7_amd64_user, ('vstruct.defs.windows.win_6_1_amd64.ntdll','', 'ntdll'))

        pos = self.model.append(None, (None, 'posix', ''))
        self.model.append(pos, ('vstruct.defs.elf', '', 'Elf'))

        arm = self.model.append(None, (None, 'arm', ''))
        self.model.append(arm, (None, '', 'arm7'))

    def __vwActivated(self, tree, path, column):
        x = self.vwGetSelected(0)
        if x == None:
            return

        print 'WOOT',x

        import sys
        import gtk
        __import__(x)
        mod = sys.modules[x]

        b = vs_builder.VStructBuilder()
        b.addVStructNamespace(self.vwGetSelected(2), mod)

        bv = VStructBuilderView(b)

        w = gtk.Window()
        w.add(bv)

        w.show_all()


class VStructBuilderView(vw_views.VTreeView):
    __model_class__ = gtk.TreeStore
    __cols__ = (
        (None,        0, object),
        ('Namespace', 1, str),
        ('Structure', 2, str),
    )

    def __init__(self, vsbuilder):
        self.vsbuilder = vsbuilder
        vw_views.VTreeView.__init__(self)

    def vwLoad(self):
        for nsname in self.vsbuilder.getVStructNamespaceNames():
            nm = self.model.append(None, (None, nsname, ''))
            for sname in self.vsbuilder.getVStructNames(namespace=nsname):
                self.model.append(nm, ('%s.%s' % (nsname, sname), '', sname))

    # FIXME make a structure selector for a builder namespace!

class VStructView(vw_views.VTreeView):
    __model_class__ = gtk.TreeStore
    __cols__ = (
        (None, 0, object),
        #FIXME offset and use vsGetPrintInfo
        ("Offset", 1, str),
        ("Name", 2, str),
        ("Type", 3, str),
    )

    def __init__(self, vs, editable=False):
        self.mystruct = vs
        vw_views.VTreeView.__init__(self)

        if editable:
            self.treeview.enable_model_drag_dest(target_entries, gtk.gdk.ACTION_MOVE)
            self.treeview.connect('drag-data-received', self.vwDragRecv)

    def vwDragRecv(self, treeview, dcontext, x, y, sdata, info, etime):
        print "DROP!",sdata.data
        drow = treeview.get_dest_row_at_pos(x, y)
        print repr(self.treeview),repr(treeview)
        if drow == None:
            titer = None
            dpos = gtk.TREE_VIEW_DROP_AFTER
        else:
            tpath, dpos = drow
            titer = self.model.get_iter(tpath)

        #if dpos == gtk.TREE_VIEW_DROP_INTO_OR_BEFORE:
            #new = self.model.prepend(parent=target, row=source_row)
        #elif dpos == gtk.TREE_VIEW_DROP_INTO_OR_AFTER:
            #new = self.model.append(parent=target, row=source_row)
        #elif dpos == gtk.TREE_VIEW_DROP_BEFORE:
            #new = self.model.insert_before(parent=None, sibling=target, row=source_row)
        #elif dpos == gtk.TREE_VIEW_DROP_AFTER:
            #new = self.model.insert_after(parent=None, sibling=target, row=source_row)

        dcontext.finish(success=False, del_=False, time=etime)

    def vwLoad(self):
        self.model.clear()
        i = self.model.append(None, (self.mystruct, "00000000", self.mystruct._vs_name, self.mystruct.vsGetClassPath()))
        todo = [(self.mystruct, i, 0),]
        while len(todo):
            d,iter,baseoff = todo.pop()
            for name,field in d: # FIXME unify iter for vstruct w/o name?
                if isinstance(field, vstruct.VStruct):
                    off = d.vsGetOffset(name)
                    i = self.model.append(iter, (d, "%.8x" % (baseoff+off), name, ""))
                    todo.append((field, i, baseoff+off))

                elif isinstance(field, vstruct.VArray):
                    pass

                else:
                    off = d.vsGetOffset(name)
                    self.model.append(iter, (field, "%.8x" % (baseoff+off), name, field.vsGetTypeName()))

    def vwActivated(self, tree, path, column):
        print "WOOT"
        pass

class VStructBrowser(vw_views.VTreeView):
    __model_class__ = gtk.TreeStore
    __cols__ = (
        (None, 0, object),
        ("Name", 1, str),
    )

    def __init__(self):
        vw_views.VTreeView.__init__(self)
        self.treeview.enable_model_drag_source(
            gtk.gdk.BUTTON1_MASK,
            target_entries,
            gtk.gdk.ACTION_MOVE)
        self.treeview.connect("drag-data-get", self.vwDragGet)

    def vwDragGet(self, treeview, dcontext, sdata, info, etime):
        treesel = treeview.get_selection()
        model, iter = treesel.get_selected()
        text = model.get_value(iter, 1)
        sdata.set('example', 8, text)
        return

    def vwLoad(self):
        self.model.clear()
        # Start with just the primitives.
        piter = self.model.append(None, (vs_prims, "primitives"))
        for name in dir(vs_prims):
            c = getattr(vs_prims, name)

            if inspect.isclass(c):

                if issubclass(c, vs_prims.v_prim):
                    self.model.append(piter, (c, c.__name__))

class VStructAttrs(vw_views.VTreeView):
    pass

