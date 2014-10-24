#include "machmodule.h"
#include "structmember.h"

static PyObject *MachTask_threads(PyObject *self) {
    PyObject *threads;
    kern_return_t err;
    thread_t *thread_list;
    unsigned int thread_count, i;

    err = task_threads(((MachPort *)self)->port, &thread_list, &thread_count);
    if (err != KERN_SUCCESS) {
        PyErr_SetString(MachError, mach_error_string(err));
        return NULL;
    }

    threads = PyList_New(thread_count);
    if (!threads) {
        vm_deallocate(mach_task_self(), (unsigned int)thread_list, thread_count*sizeof(mach_port_t));
        return NULL;
    }
    
    for (i=0; i < thread_count; i++) {
        PyList_SET_ITEM(threads, i, MachPort_New(&MachThreadType, thread_list[i]));
    }

    vm_deallocate(mach_task_self(), (unsigned int)thread_list, thread_count*sizeof(mach_port_t));

    return threads;
}

static PyObject *MachTask_vm_read(PyObject *self, PyObject *args) {
    PyObject *buffer;
    kern_return_t err;
    unsigned int address, size;
    vm_offset_t data;
    vm_size_t data_count;

    if (!PyArg_ParseTuple(args, "II", &address, &size))
        return NULL;

    err = vm_read(((MachPort *)self)->port, address, size, &data, &data_count);
    if (err != KERN_SUCCESS) {
        PyErr_SetString(MachError, mach_error_string(err));
        return NULL;
    }

    buffer = PyString_FromStringAndSize((char *)data, data_count);
    vm_deallocate(mach_task_self(), data, data_count);
    return buffer;
}

static PyObject *MachTask_get_mmaps(PyObject *self, PyObject *args) {
    kern_return_t err;
    vm_address_t address = 0;
    unsigned int mapsize = 0;
    unsigned int nextaddr = 0;
    unsigned int prot = 0;

    PyObject *memlist = NULL;
    PyObject *tup = NULL;
    vm_region_basic_info_data_64_t info;
    mach_port_t name; //FIXME leak?
    unsigned int count = VM_REGION_BASIC_INFO_COUNT_64;

    memlist = PyList_New(0);

    do {
        address = nextaddr;
        err = vm_region(((MachPort*)self)->port,
                &address, &mapsize, VM_REGION_BASIC_INFO_64, 
                (vm_region_info_t)&info, &count, &name);
        if (err != KERN_SUCCESS) {
            address += 4096;
            continue;
        }

        prot = 0;
        if (info.protection & VM_PROT_READ)
            prot |= 4;
        if (info.protection & VM_PROT_WRITE)
            prot |= 2;
        if (info.protection & VM_PROT_EXECUTE)
            prot |= 1;
        if (info.shared != 0)
            prot |= 8;

        if (prot != 0) {
            tup = PyTuple_New(4);
            PyTuple_SetItem(tup, 0, PyLong_FromUnsignedLong(address));
            PyTuple_SetItem(tup, 1, PyLong_FromUnsignedLong(mapsize));
            PyTuple_SetItem(tup, 2, PyLong_FromUnsignedLong(prot));
            PyTuple_SetItem(tup, 3, PyString_FromString("")); //FIXME mmap names

            PyList_Append(memlist, tup);
        }

        nextaddr = address + mapsize;
    } while (nextaddr > address);

    return memlist;
}

static PyObject *MachTask_vm_write(PyObject *self, PyObject *args) {
    kern_return_t err;
    unsigned int address;
    PyObject *buffer;

    if (!PyArg_ParseTuple(args, "IO", &address, &buffer))
        return NULL;

    if (!PyString_Check(buffer)) {
        PyErr_SetString(PyExc_Exception, "ERROR parsing args to vm_write for mach task (2nd arg MUST be string)");
        return(NULL);
    }

    err = vm_write(((MachPort *)self)->port, address,
            (vm_offset_t)PyString_AS_STRING(buffer), PyString_GET_SIZE(buffer));
    if (err != KERN_SUCCESS) {
        char buf[10];
        sprintf(buf, "%d", err);
        PyErr_SetString(MachError, mach_error_string(err));
        return NULL;
    }

    Py_RETURN_NONE;
}

static PyMethodDef methods[] = {
    {"threads", (PyCFunction)MachTask_threads, METH_NOARGS, "Returns a list of the threads within a task."},
    {"get_mmaps", MachTask_get_mmaps, METH_VARARGS, "List a task's virtual memory maps"},
    {"vm_read", MachTask_vm_read, METH_VARARGS, "Read a task's virtual memory."},
    {"vm_write", MachTask_vm_write, METH_VARARGS, "Write a task's virtual memory."},
    {NULL},
};

PyTypeObject MachTaskType = {
    PyObject_HEAD_INIT(NULL)
    0,                         /* ob_size */
    "mach.MachTask",           /* tp_name */
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
    "Mach task_t wrapper",     /* tp_doc */
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
