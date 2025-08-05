AC_DEFUN([AM_STDF_ZZIPLIB],
[
dnl ********************************************************
dnl *                     zip [zziplib]                    *
dnl ********************************************************
enable_zip_compression="maybe"
AC_MSG_CHECKING(whether zip support should be enabled)
AC_ARG_ENABLE(zip,
	AC_HELP_STRING([--enable-zip],[enable zip support (zziplib) @<:@default=auto@:>@]),
	[
	if test "x$enableval" = "xyes" ; then
		enable_zip_compression="yes"
	else
		enable_zip_compression="no"
	fi
	]
)
AC_MSG_RESULT($enable_zip_compression)
zip_found="no"
if test "x$enable_zip_compression" != "xno" ; then
	PKG_CHECK_MODULES(ZZIPLIB, zziplib >= 0.13,
		[
			zip_found="yes"
			AC_DEFINE(HAVE_ZIP, 1, [Has zip support])
			AM_CONDITIONAL(HAVE_ZIP, true)
			ZIP_CFLAGS="${ZZIPLIB_CFLAGS}"
			ZIP_LIBS="${ZZIPLIB_LIBS}"
		], [ dontdie="" ])
fi
if test "x$zip_found" = "xno" ; then
	if test "x$enable_zip_compression" = "xyes" ; then
		echo ""
		echo "zip support was requested but zziplib was not found!"
		echo ""
		echo "You can grab it from http://zziplib.sourceforge.net/"
		echo ""
		AC_MSG_ERROR([zziplib not found!])
	fi
	AM_CONDITIONAL(HAVE_ZIP, false)
	ZIP_CFLAGS=""
	ZIP_LIBS=""
fi
AC_SUBST(ZIP_CFLAGS)
AC_SUBST(ZIP_LIBS)
])
