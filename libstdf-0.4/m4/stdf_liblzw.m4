AC_DEFUN([AM_STDF_LIBLZW],
[
dnl ********************************************************
dnl *                     lzw [.Z files]                   *
dnl ********************************************************
enable_lzw_compression="no"
AC_MSG_CHECKING(whether lzw support should be enabled)
AC_ARG_ENABLE(lzw,
	AC_HELP_STRING([--enable-lzw],[enable lzw (.Z) support @<:@default=no@:>@]),
	[
	if test "x$enableval" = "xyes" ; then
		enable_lzw_compression="yes"
	else
		enable_lzw_compression="no"
	fi
	]
)
AC_MSG_RESULT($enable_lzw_compression)
LZW_CFLAGS=""
LZW_LIBS=""
if test "x$enable_lzw_compression" != "xno" ; then
	AC_DEFINE(HAVE_LZW, 1, [Has lzw support])
	AM_CONDITIONAL(HAVE_LZW, true)
else
	AM_CONDITIONAL(HAVE_LZW, false)
fi
AC_SUBST(LZW_CFLAGS)
AC_SUBST(LZW_LIBS)
])
