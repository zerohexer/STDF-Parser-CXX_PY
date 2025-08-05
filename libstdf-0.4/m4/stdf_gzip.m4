AC_DEFUN([AM_STDF_GZIP],
[
dnl ********************************************************
dnl *                     gzip [zlib]                      *
dnl ********************************************************
enable_gzip_compression="maybe"
AC_MSG_CHECKING(whether gzip support should be enabled)
AC_ARG_ENABLE(gzip,
	AC_HELP_STRING([--enable-gzip],[enable gzip support (zlib) @<:@default=auto@:>@]),
	[
	if test "x$enableval" = "xyes" ; then
		enable_gzip_compression="yes"
	else
		enable_gzip_compression="no"
	fi
	]
)
AC_MSG_RESULT($enable_gzip_compression)
gzip_found="no"
if test "x$enable_gzip_compression" != "xno" ; then
	AC_CHECK_LIB(z, uncompress,
		[
			AC_CHECK_HEADERS([zlib.h],
				[
					gzip_found="yes"
					AC_DEFINE(HAVE_GZIP, 1, [Has gzip support])
					AM_CONDITIONAL(HAVE_GZIP, true)
					GZIP_CFLAGS=""
					GZIP_LIBS="-lz"
				])
		])
fi
if test "x$gzip_found" = "xno" ; then
	if test "x$enable_gzip_compression" = "xyes" ; then
		echo ""
		echo "gzip support was requested but zlib was not found!"
		echo ""
		echo "You can grab it from http://www.gzip.org/zlib/"
		echo ""
		AC_MSG_ERROR([zlib not found!])
	fi
	AM_CONDITIONAL(HAVE_GZIP, false)
	GZIP_CFLAGS=""
	GZIP_LIBS=""
fi
AC_SUBST(GZIP_CFLAGS)
AC_SUBST(GZIP_LIBS)
])
