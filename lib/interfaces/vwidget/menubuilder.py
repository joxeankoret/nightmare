
import gtk

class FieldAdder:
    def __init__(self, menu, splitchar='.'):
        self.splitchar = splitchar
        self.menu = menu
        self.menu.idx = 0
        self.menu.kids = {}

    def addField(self, pathstr, callback=None, args=(), stockid=None):
        parent = self.menu
        kid = None
        plist = pathstr.split(self.splitchar)

        for p in plist[:-1]:
            kid = parent.kids.get(p)
            if kid == None:
                item = gtk.MenuItem(p, True)
                item.set_name("vwidget_menu")
                item.show()
                parent.insert(item, parent.idx)
                parent.idx += 1
                kid = Menu()
                kid.idx = 0
                item.set_submenu(kid)
                parent.kids[p] = kid
            parent = kid

        if stockid != None:
            item = gtk.ImageMenuItem(stock_id=stockid)
        else:
            item = gtk.MenuItem(plist[-1], True)
        if callback != None:
            item.connect("activate", callback, *args)

        item.show()
        item.set_name("vwidget_menu")
        parent.insert(item, parent.idx)
        parent.idx += 1
        #parent.append(item)
        return item

class MenuBar(FieldAdder, gtk.MenuBar):
    def __init__(self):
        gtk.MenuBar.__init__(self)
        FieldAdder.__init__(self, self)
        self.set_name("vwidget_menu")

class Menu(FieldAdder, gtk.Menu):
    def __init__(self):
        gtk.Menu.__init__(self)
        FieldAdder.__init__(self, self)
        self.set_name("vwidget_menu")

