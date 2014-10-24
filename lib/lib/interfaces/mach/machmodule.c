#include "machmodule.h"


PyObject *MachError;
PyObject *TaskSelf;

static PyObject *Mach_task_for_pid(PyObject *self, PyObject *args) {
    kern_return_t err;
    mach_port_t task;
    int pid;

    if (!PyArg_ParseTuple(args, "i", &pid))
        return NULL;

    err = task_for_pid(mach_task_self(), pid, &task);
    if (err != KERN_SUCCESS) {
        PyErr_SetString(MachError, mach_error_string(err));
        return NULL;
    }

    return MachPort_New(&MachTaskType, task);
}

static PyObject *Mach_process_list(PyObject *self, PyObject *args) {
    PyObject *mylist = NULL;
    PyObject *tup = NULL;
    int ctl[4] = {0};
    unsigned int size = 0;
    struct kinfo_proc *kinfo = NULL;
    int i, count;

    ctl[0] = CTL_KERN;
    ctl[1] = KERN_PROC;
    ctl[2] = KERN_PROC_ALL;
    sysctl(ctl, 3, NULL, &size, NULL, 0); //Figure out the size we'll need
    kinfo = calloc(1, size);
    sysctl(ctl, 3, kinfo, &size, NULL, 0); //Acutally go get it.

    count = size / sizeof(struct kinfo_proc);

    mylist = PyList_New(0);

    for (i = 0; i < count; i++) {
        tup = PyTuple_New(2);
        PyTuple_SetItem(tup, 0, PyLong_FromUnsignedLong(kinfo[i].kp_proc.p_pid));
        PyTuple_SetItem(tup, 1, PyString_FromString(kinfo[i].kp_proc.p_comm));
        PyList_Append(mylist, tup);
    }

    free(kinfo);

    return mylist;
}

static PyMethodDef methods[] = {
    {"task_for_pid", Mach_task_for_pid, METH_VARARGS, "Retrieve task via PID."},
    {"process_list", Mach_process_list, METH_VARARGS, "Retrieve a list of (pid,cmd) tuples"},
    {NULL, NULL, 0, NULL}
};

PyMODINIT_FUNC initmach(void) {
    PyObject *m;
    
    m = Py_InitModule("mach", methods);
    
    // Create our exception type
    MachError = PyErr_NewException("mach.MachError", NULL, NULL);
    Py_INCREF(MachError);
    PyModule_AddObject(m, "MachError", MachError);

    // Create the self task reference
    TaskSelf = MachPort_New(&MachTaskType, mach_task_self());
    PyModule_AddObject(m, "task_self", TaskSelf);

    // Add classes
    add_obj(m, "MachTask", &MachTaskType);
    add_obj(m, "MachThread", &MachThreadType);
}
