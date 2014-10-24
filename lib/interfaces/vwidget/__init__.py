
import gtk
import gobject
from gtk import gdk

blue = (0, 0, 0x99)
green =  (0, 0xff, 0)
yellow = (0xff, 0xff, 0)
orange = (0xff, 0x66, 0)
red = (0xff, 0, 0)

class VWidget(gtk.Widget):
    def __init__(self, dheight=300, dwidth=20):
        self._dheight = dheight
        self._dwidth = dwidth
        gtk.Widget.__init__(self)
        self._layout = self.create_pango_layout("")

    def do_realize(self):
        self.set_flags(self.flags() | gtk.REALIZED)

        self.window = gdk.Window(self.get_parent_window(),
                                 width=20,
                                 height=self.allocation.height,
                                 window_type=gdk.WINDOW_CHILD,
                                 wclass=gdk.INPUT_OUTPUT,
                                 event_mask=self.get_events() | gdk.EXPOSURE_MASK | gdk.BUTTON_PRESS_MASK
                                 )
        self.window.set_user_data(self)
        self.style.attach(self.window)
        self.style.set_background(self.window, gtk.STATE_NORMAL)

    def do_unrealize(self):
        self.window.set_user_data(None)

    def do_size_request(self, req):
        req.width = self._dwidth
        req.height = self._dheight

    def do_size_allocate(self, alloc):
        self.allocation = alloc
        if self.flags() & gtk.REALIZED:
            self.window.move_resize(*alloc)

class RefView(VWidget):
    """
    Render a box which draws arrows for references between
    "locations" in it's known address space.
    """
    def __init__(self, base, size, refs):
        VWidget.__init__(self)
        self.updateRefs(base, size, refs)

    def inRange(self, addr):
        if addr < self.base:
            return False
        if addr >= self.base + self.size:
            return False
        return True

    def updateRefs(self, base, size, refs):
        self.base = base
        self.size = size
        self.refs = []
        self.deps = []
        for r in refs:
            fromus = self.inRange(r[0])
            tous = self.inRange(r[1])
            if fromus and tous:
                self.refs.insert(0, r)

            elif not fromus and not tous:
                continue

            else:
                self.refs.append(refs)

        for i in range(len(self.refs)):
            depth = 2
            r = self.refs[i]
            for j in range(i, 0, -1):
                if self.isOverlap(r, self.refs[j]):
                    depth += 2

        if self.flags() & gtk.REALIZED:
            self.move_resize(*self.allocation)

    def do_expose_event(self, event):
        x, y, w, h = self.allocation
        cr = self.window.cairo_create()
        # Fill the whole thing in black

        cr.set_source_rgb(0, 0, 0)
        cr.rectangle(0, 0, h, w)
        cr.fill()

        for base,size,color,text in self.spaces:
            start = ((base-self.min) * h) / self.range
            size = ((size * h) / self.range) + 1
            cr.rectangle(0, start, w, size)
            cr.set_source_rgb(*color)
            cr.fill()

        cr.update_layout(self._layout)
        cr.show_layout(self._layout)

class SpaceView(VWidget):
    """
    Render a potentially sparse space which may be backed by varied
    types of maps/pages/etc.
    """
    def __init__(self, spaces, dheight=300, dwidth=20):
        """
        Render a list of "spaces".  These are a list of tuples
        with the following contents (<base>,<len>,<color_tuple>,<text>).
        """
        VWidget.__init__(self, dheight=dheight, dwidth=dwidth)
        self.updateSpaces(spaces)

    def updateSpaces(self, spaces):
        self.spaces = spaces

        # Find out the range we're dealing with
        min = 0xffffffff
        max = 0
        for base,size,color,text in self.spaces:
            if base < min:
                min = base
            end = base+size
            if end > max:
                max = end

        # Setup our size parameters
        self.min = min
        self.max = max
        self.range = max - min

        if self.flags() & gtk.REALIZED:
            self.queue_draw()

    def goto(self, value):
        # Extend and over-ride this for location callbacks
        pass

    def do_button_press_event(self, event):
        x, y, w, h = self.allocation
        clickx, clicky = event.get_coords()
        off = float(clicky * self.range) / float(h)
        self.goto(self.min + int(off))
        return True

    def do_expose_event(self, event):
        x, y, w, h = self.allocation
        cr = self.window.cairo_create()
        # Fill the whole thing in black

        cr.set_source_rgb(0, 0, 0)
        cr.rectangle(0, 0, h, w)
        cr.fill()

        for base,size,color,text in self.spaces:
            start = ((base-self.min) * h) / self.range
            size = ((size * h) / self.range) + 1
            cr.rectangle(0, start, w, size)
            cr.set_source_rgb(*color)
            cr.fill()

        cr.update_layout(self._layout)
        cr.show_layout(self._layout)

    def shutdown(self, *args):
        gtk.main_quit()

gobject.type_register(SpaceView)
gobject.type_register(RefView)

cmap = { 4: red,
         6: blue,
         5: orange }

def spacesForMaps(mapobj):
    """
    Return a set of "spaces" for each of the maps
    returned by the getMemoryMaps() api (for emu or trace).
    """
    spaces = []
    for base,size,perms,fname in mapobj.getMemoryMaps():
        spaces.append((base,size,cmap.get(perms, yellow),fname))
    return spaces

def spacesForWin32HeapSegment(segment):
    spaces = []
    for chunk in segment.getChunks():
        if chunk.isBusy():
            color = (0xff, 0, 0)
        else:
            color = (0, 0xff, 0)
        spaces.append((chunk.address, len(chunk), color, "stuff"))

    return spaces

