#include <Python.h>
#include <mach/mach.h>
#include <sys/types.h>
#include <sys/sysctl.h>

#define BASIC_PORT_CALL(s, f) \
    kern_return_t err;                                      \
    err = f(((MachPort *)s)->port);                         \
    if (err != KERN_SUCCESS) {                              \
        PyErr_SetString(MachError, mach_error_string(err)); \
        return NULL;                                        \
    }                                                       \
    Py_RETURN_NONE;


// machmodule.c
extern PyObject *MachError;

// thread.c, task.c
typedef struct {
    PyObject_HEAD
    mach_port_t port;
} MachPort;
extern PyTypeObject MachTaskType;
extern PyTypeObject MachThreadType;

// vm.c
typedef struct {
    PyObject_HEAD
    vm_offset_t *data;
    mach_msg_type_number_t data_count;
} MachVM;
extern PyTypeObject MachVMType;

// utility.c
extern void add_obj(PyObject *mod, char *name, void *obj);
extern PyObject *MachPort_New(PyTypeObject *classtype, mach_port_t port);
extern void MachPort_dealloc(MachPort *self);
extern PyObject *MachVM_New(vm_offset_t *data, mach_msg_type_number_t data_count);
