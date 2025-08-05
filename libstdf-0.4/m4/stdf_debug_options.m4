AC_DEFUN([AM_STDF_DEBUG_OPTIONS],
[
dnl ********************************************************
dnl *               Memory debug support                   *
dnl ********************************************************
DEBUG_CFLAGS=""
DEBUG_LIBS=""

enable_debug_mtrace="no"
AC_MSG_CHECKING(whether to use malloc trace for debugging)
AC_ARG_ENABLE(mtrace,
	AC_HELP_STRING([--enable-mtrace],[use mtrace for memory debugging @<:@default=no@:>@]),
	[
	if test "x$enableval" = "xyes" ; then
		enable_debug_mtrace="yes"
	else
		enable_debug_mtrace="no"
	fi
	]
)
AC_MSG_RESULT($enable_debug_mtrace)
if test "x$enable_debug_mtrace" = "xyes" ; then
	AC_CHECK_HEADERS(mcheck.h)
	AC_CHECK_LIB(c, mtrace, [], [])
	if test "x$ac_cv_header_mcheck_h$ac_cv_lib_c_mtrace" != "xyesyes" ; then
		AC_MSG_ERROR([could not find mtrace])
	fi
fi

enable_debug_dmalloc="no"
AC_MSG_CHECKING(whether to use dmalloc for debugging)
AC_ARG_ENABLE(dmalloc,
	AC_HELP_STRING([--enable-dmalloc],[use dmalloc for memory debugging @<:@default=no@:>@]),
	[
	if test "x$enableval" = "xyes" ; then
		enable_debug_dmalloc="yes"
	else
		enable_debug_dmalloc="no"
	fi
	]
)
AC_MSG_RESULT($enable_debug_dmalloc)
if test "x$enable_debug_dmalloc" = "xyes" ; then
	AC_CHECK_HEADERS(dmalloc.h)
	AC_CHECK_LIB(dmalloc, dmalloc_shutdown, [], [])
	if test "x$ac_cv_header_dmalloc_h$ac_cv_lib_dmalloc_dmalloc_shutdown" != "xyesyes" ; then
		AC_MSG_ERROR([could not find dmalloc])
	fi
	DEBUG_LIBS="-ldmalloc"
fi

enable_debug_efence="no"
AC_MSG_CHECKING(whether to use electric fence for debugging)
AC_ARG_ENABLE(efence,
	AC_HELP_STRING([--enable-efence],[use efence for memory debugging @<:@default=no@:>@]),
	[
	if test "x$enableval" = "xyes" ; then
		enable_debug_efence="yes"
	else
		enable_debug_efence="no"
	fi
	]
)
AC_MSG_RESULT($enable_debug_efence)
if test "x$enable_debug_efence" = "xyes" ; then
	AC_CHECK_HEADERS(efence.h)
	AC_CHECK_LIB(efence, _eff_init, [], [])
	if test "x$ac_cv_header_efence_h$ac_cv_lib_efence__eff_init" != "xyesyes" ; then
		AC_MSG_ERROR([could not find electric fence])
	fi
	DEBUG_LIBS="-lefence"
fi

enable_debug_mudflap="no"
AC_MSG_CHECKING(whether to use mudflap for debugging)
AC_ARG_ENABLE(mudflap,
	AC_HELP_STRING([--enable-mudflap],[use mudflap for memory debugging @<:@default=no@:>@]),
	[
	if test "x$enableval" = "xyes" ; then
		enable_debug_mudflap="yes"
	else
		enable_debug_mudflap="no"
	fi
	]
)
AC_MSG_RESULT($enable_debug_mudflap)
if test "x$enable_debug_mudflap" = "xyes" ; then
	AC_CHECK_LIB(mudflap, __mf_init, [], [])
	if test "x$ac_cv_lib_mudflap___mf_init" != "xyes" ; then
		AC_MSG_ERROR([could not find mudflap])
	fi
	DEBUG_CFLAGS="-fmudflap"
	DEBUG_LIBS="-lmudflap"
fi

AC_SUBST(DEBUG_CFLAGS)
AC_SUBST(DEBUG_LIBS)
])
