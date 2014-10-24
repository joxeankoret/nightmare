
import gtk
import gtk.glade

import envi.cli as e_cli

import vwidget.layout as vw_layout
import vwidget.menubuilder as vw_menu
import vwidget.memview as vw_memview

from envi.threads import firethread
from vwidget.main import idlethread

class MainWindow(vw_layout.LayoutWindow):
    """
    A nice main text window with a CLI input and history etc...
    """
    def __init__(self, cli, memobj, syms=None):
        vw_layout.LayoutWindow.__init__(self)
        self.cli = cli
        self.connect("key-press-event", self.keypressed)

        self.vbox = gtk.VBox()
        self.menubar = vw_menu.MenuBar()

        self.add(self.vbox)
        self.vbox.pack_start(self.menubar, expand=False)
        toolbar = self.getMainToolbar()
        if toolbar != None:
            self.vbox.pack_start(toolbar, expand=False)

        self.canvas = vw_memview.ScrolledMemoryView(memobj, syms=syms)
        self.canvas.textview.set_property("wrap_mode", gtk.WRAP_WORD)
        self.vbox.pack_start(self.canvas, expand=True)

        # If it's an EnviCli, let's over-ride the canvas right away.
        if isinstance(cli, e_cli.EnviCli):
            cli.setCanvas(self.canvas)

        entry = gtk.Entry()
        entry.connect("activate", self.cli_activate)
        entry.connect("key-press-event", self.entrykeypressed)
        self.vbox.pack_start(entry, expand=False)
        self.entry = entry

        self.history = []
        self.histidx = 0
        entry.grab_focus()

    @idlethread
    def _sensitive_entry(self, sensitive):
        # For the fired thread
        self.entry.set_sensitive(sensitive)
        if sensitive:
            self.entry.grab_focus()

    def getMainToolbar(self):
        return None

    def useHistory(self, entry, delta):
        if delta < 0 and self.histidx == 0:
            return

        if delta > 0 and len(self.history) <= self.histidx+delta:
            self.histidx = len(self.history)
            entry.set_text("")
            return

        self.histidx += delta
        htext = self.history[self.histidx]
        entry.set_text(htext)
        entry.set_position(-1)

    def entrykeypressed(self, entry, event):
        if event.keyval == 65362:
            self.useHistory(entry, -1)
            return True
        elif event.keyval == 65364:
            self.useHistory(entry, 1)
            return True
        return False

    @firethread
    def onecmd(self, cmd):
        '''
        Issue a single command with proper history tracking etc...
        (fires a thread to do it...)
        '''
        self._sensitive_entry(False)
        try:
            cmd = self.cli.precmd(cmd)
            self.canvas.write("%s %s\n" % (self.cli.prompt,cmd))
            self.cli.onecmd(cmd)
            self.addHistory(cmd)
        finally:
            self._sensitive_entry(True)

    def keypressed(self, window, event):
        fkbase = 65469
        fkey = event.keyval - fkbase
        if fkey >= 1 and fkey < 13:
            self.onecmd("<f%d>" % fkey)

        elif event.keyval == 65299:
            self.onecmd("break")

    def addHistory(self, histcmd):
        self.history.append(histcmd)
        self.histidx = len(self.history)

    def cli_activate(self, entry):
        cmd = entry.get_text()
        entry.set_text("")
        self.onecmd(cmd)

#FIXME is anything even using this one still?
class VWindow:
    """
    A class for all vdb/vivisect windows to inherit from.  Full of
    little utilities that make GUI writing slightly less painful.

    When inheriting from this class, you *must* make your classname
    the same as the top level window object in your glade project.
    """

    def __init__(self, fname, layout):
        self.glade = gtk.glade.XML(fname)
        self.glade.signal_autoconnect(self)
        self.getWidget(self.__class__.__name__).connect("delete_event", self.delete)
        self.notebook_groups = {}
        self.vwlayout = layout

    def delete(self, window, event):
        print "ENDING GEOM:",repr(self.getGeometry())
        return False

    def getGeometry(self):
        """
        Returns a tuple of (x, y, xsize, ysize) for later use in setGeometry()
        """
        win = self.getWidget(self.__class__.__name__)
        x, y = win.get_position()
        xsize, ysize = win.get_size()
        return (x, y, xsize, ysize)

    def setGeometry(self, geom):
        win = self.getWidget(self.__class__.__name__)
        win.move(geom[0], geom[1])
        win.resize(geom[2], geom[3])

    def setTitle(self, title):
        widget = self.getWidget(self.__class__.__name__)
        if widget:
            widget.set_title(title)

    def setSensitive(self, widgetname, sensitive):
        wid = self.getWidget(widgetname)
        wid.set_sensitive(sensitive)

    def textFromWidget(self, wName):
        wid = self.glade.get_widget(wName)
        if not wid:
            raise Exception("ERROR - Can't find widget %s" % wName)
        return wid.get_text()

    def getWidget(self, name):
        return self.glade.get_widget(name)

    def show(self):
        self.getWidget(self.__class__.__name__).show()

    def hide(self):
        self.getWidget(self.__class__.__name__).hide()

