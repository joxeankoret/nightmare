/*
 * libdisable_signal.so version 0.0.1
 * Copyright (c) Joxean Koret
 * 
 * Simple library to enable memcheck in applications using glibc and 
 * disable signal handlers for SIGSEGV, SIGBUS, SIGFPE and SIGABRT.
 * 
 * Please be advised that memcheck is more aggressive than MALLOC_CHECK_
 * and you're likely discovering that almost all Linux applications you
 * run daily contains many stupid bugs at initialization.
 * 
*/
#include <algorithm>
#include <vector>

#include <pthread.h>
#include <string.h>
#include <stdio.h>
#include <signal.h>
#include <dlfcn.h>
#include <sys/mman.h>

//----------------------------------------------------------------------
#define NFPAPI extern "C"

//----------------------------------------------------------------------
typedef void (*sighandler_t)(int);
typedef sighandler_t (*signal_func_t)(int, sighandler_t);

//----------------------------------------------------------------------
static signal_func_t g_signal = NULL;

//----------------------------------------------------------------------
// Prevent the target from installing a SIGSEGV, SIGFPE, etc... signal
// handler that may prevent our instrumentation interfaces to catch the
// signal.
NFPAPI sighandler_t signal(int signum, sighandler_t handler)
{
  if ( g_signal == NULL )
    g_signal = (signal_func_t)dlsym(RTLD_NEXT, "signal");

  switch ( signum )
  {
    case SIGSEGV:
    case SIGABRT:
    case SIGFPE:
    case SIGBUS:
      printf("Disabling signal handling for target, signal was %d\n", signum);
      return handler;
    default:
      return g_signal(signum, handler);
  }
}
