"""
Just a place to house some universalish utilities
"""

import gtk

def makeColumn(name, index, onedit=None, cell=None, links=None):
    """
    Return a default "TreeViewColumn" of name "name"
    whose TreeModel index for the renderer is "index"
    """
    if cell == None:
        cell = gtk.CellRendererText()
    if links == None:
        links = {"text":index}
    if onedit:
        cell.set_property("editable", True)
        cell.connect("edited", onedit)
    col = gtk.TreeViewColumn(name,cell,**links)
    col.set_property("clickable", True)
    col.set_property("reorderable", True)
    col.set_property("resizable",True)
    col.set_property("sizing",1)
    col.set_property("sort-indicator", True)
    col.set_sort_column_id(index)
    return col

def getTreeSelected(treeview, colnum):
    """
    Return the object in column *colnum* from the currently
    selected row in the given treeview...
    """
    ret = None
    path,view = treeview.get_cursor()
    model = treeview.get_model()
    if path:
        iter = model.get_iter(path)
        ret = model.get_value(iter, colnum)
    return ret


