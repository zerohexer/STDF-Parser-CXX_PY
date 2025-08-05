/* Windows compatibility header for features.h */
#ifndef _FEATURES_H
#define _FEATURES_H

/* This is a stub replacement for GNU libc features.h on Windows */

#ifdef _WIN32
/* Windows doesn't use GNU libc feature test macros */
/* Define common GNU feature macros as no-ops or Windows equivalents */

#ifndef __USE_ISOC99
#define __USE_ISOC99 1
#endif

#ifndef __USE_POSIX
#define __USE_POSIX 1
#endif

#ifndef __USE_MISC
#define __USE_MISC 1
#endif

/* Compiler and system identification */
#ifndef __GNUC_PREREQ
#define __GNUC_PREREQ(maj, min) 0
#endif

#else
/* On Unix systems with GNU libc, include the real features.h */
#include_next <features.h>
#endif

#endif /* _FEATURES_H */