#include "machmodule.h"
#include "structmember.h"

#ifdef __i386__
#define STATE_TYPE i386_thread_state_t
#else
#ifdef __ppc__
#define STATE_TYPE ppc_thread_state_t
#endif
#endif

static PyObject *MachThread_get_state(PyObject *self, PyObject *args) {

    kern_return_t ret = 0;

    STATE_TYPE state = {0};
    unsigned int rsize = sizeof(state)/sizeof(int);
    int flavor = 0;

    if (!PyArg_ParseTuple(args, "i", &flavor)) {
        PyErr_SetString(PyExc_Exception, "thread_get_state() needs an int");
        return NULL;
    }

    ret = thread_get_state(((MachPort*)self)->port, flavor, (unsigned int *)&state, &rsize);
    if (ret != KERN_SUCCESS) {
        PyErr_SetString(MachError, mach_error_string(ret));
        return NULL;
    }
    return PyString_FromStringAndSize((char*)&state, sizeof(state));
}

static PyObject *MachThread_set_state(PyObject *self, PyObject *args) {

    kern_return_t ret = 0;
    PyObject *statebuf;
    int flavor = 0;

    if (!PyArg_ParseTuple(args, "IO", &flavor, &statebuf)) {
        PyErr_SetString(PyExc_Exception, "thread_set_state() needs a register state buffer");
        return NULL;
    }

    if (!PyString_Check(statebuf)) {
        PyErr_SetString(PyExc_Exception, "ERROR - mach.set_state requires a register state string");
        return NULL;
    }

    ret = thread_set_state(((MachPort*)self)->port, flavor,
            (unsigned int *)PyString_AS_STRING(statebuf), PyString_GET_SIZE(statebuf)/sizeof(int));
    if (ret != KERN_SUCCESS) {
        PyErr_SetString(MachError, mach_error_string(ret));
        return NULL;
    }

    Py_RETURN_NONE;
}

static PyObject *MachThread_abort(PyObject *self) {
    BASIC_PORT_CALL(self, thread_abort);
}

static PyObject *MachThread_resume(PyObject *self) {
    BASIC_PORT_CALL(self, thread_resume);
}

static PyObject *MachThread_suspend(PyObject *self) {
    BASIC_PORT_CALL(self, thread_suspend);
}

static PyObject *MachThread_terminate(PyObject *self) {
    BASIC_PORT_CALL(self, thread_terminate);
}


static PyMethodDef methods[] = {
    {"get_state", (PyCFunction)MachThread_get_state, METH_VARARGS, "Get the current thread state get_state(flavor)"},
    {"set_state", (PyCFunction)MachThread_set_state, METH_VARARGS, "Set the current thread state buffer set_state(flavor, buffer)"},
    {"abort", (PyCFunction)MachThread_abort, METH_NOARGS, "Abort the thread."},
    {"resume", (PyCFunction)MachThread_resume, METH_NOARGS, "Resume the thread."},
    {"suspend", (PyCFunction)MachThread_suspend, METH_NOARGS, "Suspend the thread."},
    {"terminate", (PyCFunction)MachThread_terminate, METH_NOARGS, "Terminate the thread."},
    {NULL},
};

PyTypeObject MachThreadType = {
    PyObject_HEAD_INIT(NULL)
    0,                         /* ob_size */
    "mach.MachThread",         /* tp_name */
    sizeof(MachPort),          /* tp_basicsize */
    0,                         /* tp_itemsize */
    (destructor)MachPort_dealloc, /* tp_dealloc */
    0,                         /* tp_print */
    0,                         /* tp_getattr */
    0,                         /* tp_setattr */
    0,                         /* tp_compare */
    0,                         /* tp_repr */
    0,                         /* tp_as_number */
    0,                         /* tp_as_sequence */
    0,                         /* tp_as_mapping */
    0,                         /* tp_hash */
    0,                         /* tp_call */
    0,                         /* tp_str */
    0,                         /* tp_getattro */
    0,                         /* tp_setattro */
    0,                         /* tp_as_buffer */
    Py_TPFLAGS_DEFAULT,        /* tp_flags */
    "Mach thread_t wrapper",     /* tp_doc */
    0,                         /* tp_traverse */
    0,                         /* tp_clear */
    0,                         /* tp_richcompare */
    0,                         /* tp_weaklistoffset */
    0,                         /* tp_iter */
    0,                         /* tp_iternext */
    methods,                   /* tp_methods */
    0,                         /* tp_members */
    0,                         /* tp_getset */
    0,                         /* tp_base */
    0,                         /* tp_dict */
    0,                         /* tp_descr_get */
    0,                         /* tp_descr_set */
    0,                         /* tp_dictoffset */
    0,                         /* tp_init */
    0,                         /* tp_alloc */
    0,                         /* tp_new */
};
