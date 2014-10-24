
import os

import gtk
import vwidget
import vwidget.util as vw_util
import vwidget.windows as vw_windows

class ConfigDialog(vw_windows.VWindow):

    def __init__(self, cfg, cfgname=None):
        """
        A dialog for editing config options.  If you specify "cfgname",
        all changes will be saved out to the specified file
        as they happen.
        """
        dname = os.path.dirname(vwidget.__file__)
        fname = os.path.join(dname, "config.glade")
        vw_windows.VWindow.__init__(self, fname, (0,0,500,300))

        self.setGeometry((0,0,500,300))

        self.cfg = cfg
        self.cfgname = cfgname

        tree = self.getWidget("ConfigTree")
        tree.append_column(vw_util.makeColumn("Section",1))
        tree.append_column(vw_util.makeColumn("Option",2))
        tree.append_column(vw_util.makeColumn("Value", 3, self.OptionEdited))

        model = gtk.TreeStore(str,str,str,str)
        tree.set_model(model)

        secs = cfg.sections()
        secs.sort()
        for sec in secs:
            i = model.append(None, (None, sec, None, None))
            opts = cfg.options(sec)
            opts.sort()
            for opt in opts:
                model.append(i, ("%s|%s" % (sec,opt), None, opt, cfg.get(sec, opt)))

    def OptionEdited(self, renderer, path, value):
        model = self.getWidget("ConfigTree").get_model()
        iter = model.get_iter(path)
        model.set_value(iter, 3, value)
        sec, opt = model.get_value(iter, 0).split("|", 1)
        self.cfg.set(sec, opt, value)
        if self.cfgname != None:
            self.cfg.write(file(self.cfgname, "wb"))
        return True

