
import gtk
import time
import gobject
from threading import currentThread

from Queue import Queue

gtk.gdk.threads_init()

def idlethread(func):
    '''
    A decorator which causes the function to be called by the gtk
    main iteration loop rather than synchronously...

    NOTE: This makes the call async handled by the gtk main
    loop code.  you can NOT return anything.
    '''
    def dowork(arginfo):
        args,kwargs = arginfo
        return func(*args, **kwargs)

    def idleadd(*args, **kwargs):
        if currentThread().getName() == 'GtkThread':
            return func(*args, **kwargs)
        gtk.gdk.threads_enter()
        gobject.idle_add(dowork, (args,kwargs))
        gtk.gdk.threads_leave()

    return idleadd

def idlethreadsync(func):
    '''
    Similar to idlethread except that it is synchronous and able
    to return values.
    '''
    q = Queue()
    def dowork(arginfo):
        args,kwargs = arginfo
        try:
            q.put(func(*args, **kwargs))
        except Exception, e:
            q.put(e)

    def idleadd(*args, **kwargs):
        if currentThread().getName() == 'GtkThread':
            return func(*args, **kwargs)
        gtk.gdk.threads_enter()
        gobject.idle_add(dowork, (args,kwargs))
        gtk.gdk.threads_leave()
        return q.get()

    return idleadd

@idlethread
def shutdown():
    gtk.main_quit()

def mainthread():
    currentThread().setName('GtkThread')

def main():
    currentThread().setName('GtkThread')
    gtk.gdk.threads_enter()
    gtk.main()
    gtk.gdk.threads_leave()
