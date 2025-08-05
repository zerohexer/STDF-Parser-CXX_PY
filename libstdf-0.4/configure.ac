AC_INIT(libstdf, 0.4, [vapier@gmail.com])
AM_INIT_AUTOMAKE
AC_CONFIG_HEADER(include/libstdf_sys_config.h)

AC_PROG_CC
AC_STDF_LIBTOOL

AC_HEADER_STDC
AC_C_CONST
AC_CHECK_HEADERS([ \
stdint.h inttypes.h sys/types.h sys/stat.h ctype.h \
errno.h unistd.h fcntl.h stdio.h stdlib.h time.h \
string.h endian.h sys/endian.h machine/endian.h \
cmplrs/host.h sys/isa_defs.h byteswap.h \
features.h stdarg.h sys/cdefs.h assert.h \
])

AC_TYPE_SIZE_T
AC_CHECK_TYPE([uintptr_t], [size_t])

AM_STDF_VAPIER_DEV
AM_STDF_DEBUG_OPTIONS

dnl ********************************************************
dnl *                 SDTF v3 [stdf-ver3]                  *
dnl ********************************************************
enable_stdf_ver3_support="no"
AC_MSG_CHECKING(whether STDFv3 support should be enabled)
AC_ARG_ENABLE(stdf-ver3,
	AC_HELP_STRING([--enable-stdf-ver3],[enable support for STDFv3 @<:@default=v4 only@:>@]),
	[
	if test "x$enableval" = "xyes" ; then
		enable_stdf_ver3_support="yes"
	else
		enable_stdf_ver3_support="no"
	fi
	]
)
if test "x$enable_stdf_ver3_support" = "xyes" ; then
	AC_DEFINE(STDF_VER3, 1, [Enable support for STDFv3])
fi
AC_MSG_RESULT($enable_stdf_ver3_support)

dnl ********************************************************
dnl *                 Force endian types                   *
dnl ********************************************************
stdf_force_endian="auto"
AC_MSG_CHECKING(for endian type)
AC_ARG_ENABLE(endian,
	AC_HELP_STRING([--enable-endian],[force endian type @<:@default=detect@:>@]),
	[stdf_force_endian=$enableval])
if test "x$stdf_force_endian" = "xlittle" ; then
	AC_DEFINE(STDF_FORCE_ENDIAN, 1234, [Force endian type to little])
elif test "x$stdf_force_endian" = "xbig" ; then
	AC_DEFINE(STDF_FORCE_ENDIAN, 4321, [Force endian type to big])
elif test "x$stdf_force_endian" != "xauto" ; then
	AC_MSG_ERROR(Valid values for endian are "little", "big", or "auto")
fi
AC_MSG_RESULT($stdf_force_endian)

AM_STDF_ZZIPLIB
AM_STDF_LIBLZW
AM_STDF_GZIP
AM_STDF_BZIP2

dnl ********************************************************
dnl *                 Example Apps [examples]              *
dnl ********************************************************
enable_example_programs="yes"
AC_MSG_CHECKING(whether example programs should be built)
AC_ARG_ENABLE(examples,
	AC_HELP_STRING([--disable-examples],[disable building the examples @<:@default=build@:>@]),
	[
	if test "x$enableval" = "xyes" ; then
		enable_example_programs="yes"
	else
		enable_example_programs="no"
	fi
	]
)
AC_MSG_RESULT($enable_example_programs)
if test "x$enable_example_programs" = "xyes" ; then
	AC_CHECK_HEADERS([getopt.h])
	AM_CONDITIONAL(BUILD_EXAMPLES, true)
else
	AM_CONDITIONAL(BUILD_EXAMPLES, false)
fi

dnl ********************************************************
dnl *                     HASH [hash / ecore / glib]       *
dnl ********************************************************
if test "x$enable_example_programs" = "xyes" ; then
dnl First check for libhash ...
HASH_CFLAGS=""
HASH_LIBS=""
AC_CHECK_LIB(hash, hash_initialise,
	[
		AC_CHECK_HEADERS([hash.h], [HASH_LIBS="-lhash"])
	])
AC_SUBST(HASH_CFLAGS)
AC_SUBST(HASH_LIBS)

dnl If that fails, check for ecore ...
ECORE_LIBS=""
PKG_CHECK_MODULES(ECORE, ecore,
[
	AC_DEFINE(HAVE_ECORE, 1, [Has ecore support (used by example programs)])
	AM_CONDITIONAL(HAVE_ECORE, true)
],[
	AM_CONDITIONAL(HAVE_ECORE, false)
	ECORE_CFLAGS=""
	ECORE_LIBS=""
	AC_MSG_RESULT(no)
])
if test "x$HASH_LIBS" != "x" ; then
	ECORE_CFLAGS=""
	ECORE_LIBS=""
fi
AC_SUBST(ECORE_CFLAGS)
AC_SUBST(ECORE_LIBS)

dnl If that fails, check for glib ...
PKG_CHECK_MODULES(GLIB, glib-2.0 >= 2.0,
[
	AC_DEFINE(HAVE_GLIB, 1, [Has glib support (used by example programs)])
	AM_CONDITIONAL(HAVE_GLIB, true)
],[
	AM_CONDITIONAL(HAVE_GLIB, false)
	GLIB_CFLAGS=""
	GLIB_LIBS=""
	AC_MSG_RESULT(no)
])
if test "x$HASH_LIBS" != "x" -o "x$ECORE_LIBS" != "x" ; then
	GLIB_CFLAGS=""
	GLIB_LIBS=""
fi
AC_SUBST(GLIB_CFLAGS)
AC_SUBST(GLIB_LIBS)
fi

dnl ********************************************************
dnl *                        GD                            *
dnl ********************************************************
if test "x$enable_example_programs" = "xyes" ; then
AC_PATH_PROG(GDLIB_CONFIG, "gdlib-config", "")
if test "x$GDLIB_CONFIG" != "x" ; then
	AC_DEFINE(HAVE_GDLIB, 1, [Has gd support (used by example programs)])
	AM_CONDITIONAL(HAVE_GDLIB, true)
	GDLIB_CFLAGS=`gdlib-config --cflags`
	GDLIB_LIBS="-lgd `gdlib-config --libs`"
else
	AM_CONDITIONAL(HAVE_GDLIB, false)
	GDLIB_CFLAGS=""
	GDLIB_LIBS=""
fi
AC_SUBST(GDLIB_CFLAGS)
AC_SUBST(GDLIB_LIBS)
fi

dnl ********************************************************
dnl *                     docs [doxygen]                   *
dnl ********************************************************
enable_doxygen="no"
AC_MSG_CHECKING(whether to build documentation with doxygen)
AC_ARG_ENABLE(docs,
	AC_HELP_STRING([--enable-docs],[generate a lot of API docs @<:@default=no@:>@]),
	[
	if test "x$enableval" = "xyes" ; then
		enable_doxygen="yes"
	else
		enable_doxygen="no"
	fi
	]
)
AC_MSG_RESULT($enable_doxygen)
if test "x$enable_doxygen" = "xyes" ; then
	AC_CHECK_PROG(enable_doxygen_detect, doxygen, yes, no)
	if test "x$enable_doxygen_detect" = "xno" ; then
		echo ""
		echo "documentation building was requested by doxygen was not found!"
		echo ""
		echo "You can grab it from http://www.doxygen.org/"
		echo ""
 		AC_MSG_ERROR([doxygen not found!])
	fi
	AM_CONDITIONAL(BUILD_DOCS, true)
else
	AM_CONDITIONAL(BUILD_DOCS, false)
fi





AC_OUTPUT([
Makefile
include/Makefile
src/Makefile
doc/Makefile
doc/man/Makefile
doc/man/man3/Makefile
examples/Makefile
libstdf-config
libstdf.pc
libstdf-doc.c
],[
chmod +x libstdf-config
])
