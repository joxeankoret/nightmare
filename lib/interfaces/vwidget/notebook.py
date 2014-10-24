
"""
A suite of tools for dealing with notebooks...
"""

import gtk

def prepNotebook(notebook=None, group=1):
    """
    Setup a notebook for use in vwindows/vviews.
    """
    if notebook == None:
        notebook = gtk.Notebook()
    if gtk.gtk_version[0] >= 2 and gtk.gtk_version[1] >= 12:
        notebook.connect("create-window", createNotebookWindow)
    notebook.set_group_id(group)
    return notebook

def appendToNotebook(notebook, view, totop=True):
    """
    Add the specified view to the given notebook which has
    been prep'd with prepNotebook.  It gives you a bunch of
    junk for free.
    """
    label = createTabLabel(view, notebook)
    index = notebook.append_page(view, label)
    notebook.set_tab_reorderable(view, True)
    notebook.set_tab_detachable(view, True)
    if totop:
        notebook.set_current_page(index)

def removeFromNotebook(notebook, page):
    notebook.remove_page(notebook.page_num(page))

def createTabLabel(page, notebook):
    label = gtk.Label(page.vwGetDisplayName())

    if not page.vwIsClosable():
        return label

    box = gtk.HBox()
    image = gtk.Image()
    image.set_from_stock(gtk.STOCK_CLOSE, gtk.ICON_SIZE_SMALL_TOOLBAR)

    cbutton = gtk.Button()
    cbutton.connect("clicked", closeTabButton, page, notebook)
    cbutton.set_image(image)
    cbutton.set_relief(gtk.RELIEF_NONE)

    box.pack_start(label, True, True)
    box.pack_end(cbutton, False, False)
    box.show_all()
    return box

def closeTabButton(button, page, notebook):
    removeFromNotebook(notebook, page)

def createNotebookWindow(notebook, page, x=400, y=300):
    """
    Snap the given page out of the notebook and create a new
    window for it...
    """
    notebook.remove_page(notebook.page_num(page))
    createWindowForPage(page, x, y)

def createWindowForPage(page, x=300, y=400):
    """
    x and y are the position for the new window
    """

    win = gtk.Window()
    nb = prepNotebook()
    nb.connect("page-removed", notebookWindowPageRemoved, win)
    appendToNotebook(nb, page)
    win.notebook = nb # NOTE: assume all "page windows" have this...
    win.add(nb)
    win.show_all()
    win.move(x,y)
    return win

def notebookWindowPageRemoved(notebook, child, pagenum, window):
    """
    When a tab is removed from a popped up window, check if it is the last.
    """
    if notebook.get_n_pages() == 0:
        window.destroy()

