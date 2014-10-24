#include "machmodule.h"

// Convenience function for adding object types to modules
void add_obj(PyObject *mod, char *name, void *obj) {
    PyTypeObject *pobj = (PyTypeObject *)obj;
    pobj->tp_new = PyType_GenericNew;
    if (PyType_Ready(pobj) < 0)
        return;
    Py_INCREF(pobj);
    PyModule_AddObject(mod, name, (PyObject *)pobj);
}

// Instantiate a wrapper from a PyTypeObject and a mach_port_t
PyObject *MachPort_New(PyTypeObject *classtype, mach_port_t port) {
    MachPort *obj;

    obj = PyObject_New(MachPort, classtype);
    if (obj) {
        memcpy(&obj->port, &port, sizeof(mach_port_t));
    }
    return (PyObject *)obj;
}

// Generic deallocator for MachPort objects
void MachPort_dealloc(MachPort *self) {
    mach_port_deallocate(mach_task_self(), self->port);
    self->ob_type->tp_free((PyObject*)self);
}
