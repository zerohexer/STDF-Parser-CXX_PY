AC_DEFUN([AM_STDF_BZIP2],
[
dnl ********************************************************
dnl *                     bzip2                            *
dnl ********************************************************
enable_bzip2_compression="maybe"
AC_MSG_CHECKING(whether bzip2 support should be enabled)
AC_ARG_ENABLE(bzip2,
	AC_HELP_STRING([--enable-bzip2],[enable bzip2 support (bzlib) @<:@default=auto@:>@]),
	[
	if test "x$enableval" = "xyes" ; then
		enable_bzip2_compression="yes"
	else
		enable_bzip2_compression="no"
	fi
	]
)
AC_MSG_RESULT($enable_bzip2_compression)
bzip2_found="no"
if test "x$enable_bzip2_compression" != "xno" ; then
	AC_CHECK_LIB(bz2, BZ2_bzRead,
		[
			AC_CHECK_HEADERS([bzlib.h],
				[
					bzip2_found="yes"
					AC_DEFINE(HAVE_BZIP2, 1, [Has bzip2 support])
					AM_CONDITIONAL(HAVE_BZIP2, true)
					BZIP2_CFLAGS=""
					BZIP2_LIBS="-lbz2"
				])
		])
fi
if test "x$bzip2_found" = "xno" ; then
	if test "x$enable_bzip2_compression" = "xyes" ; then
		echo ""
		echo "bzip2 support was requested but bzlib was not found!"
		echo ""
		echo "You can grab it from http://sources.redhat.com/bzip2/"
		echo ""
 		AC_MSG_ERROR([bzlib not found!])
	fi
	AM_CONDITIONAL(HAVE_BZIP2, false)
	BZIP2_CFLAGS=""
	BZIP2_LIBS=""
fi
AC_SUBST(BZIP2_CFLAGS)
AC_SUBST(BZIP2_LIBS)
])
