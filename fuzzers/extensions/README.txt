libdisable_signal.so version 0.0.1
Copyright (c) Joxean Koret

Simple library to enable memcheck in applications using glibc and
disable signal handlers for SIGSEGV, SIGBUS, SIGFPE and SIGABRT.

This library can be used by setting the LD_PRELOAD environment variable
like in the following example:

$ LD_PRELOAD=/full/path/to/the/lib/libdisable_signal.so app arguments

Please be advised that memcheck is more aggressive than MALLOC_CHECK_
and you're likely discovering that almost all Linux applications you run
daily contains many stupid bugs at initialization.
