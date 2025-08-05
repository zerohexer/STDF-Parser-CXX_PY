AC_DEFUN([AM_STDF_VAPIER_DEV],
[dnl Let's get anal with compiling while on my dev box
if test "x$HOSTNAME" = "xvapier" ; then
	CFLAGS="$CFLAGS -Wall -Wextra -Werror"
	enable_annoy_untested="no"
else
	enable_annoy_untested="yes"
fi

dnl ********************************************************
dnl *                 Disable Warnings                     *
dnl ********************************************************
AC_MSG_CHECKING(whether to annoy you about untested code)
AC_ARG_ENABLE(warn-untested,
	AC_HELP_STRING([--disable-warn-untested],[don't warn about untested code @<:@default=warn@:>@]),
	[
	if test "x$enableval" = "xyes" ; then
		enable_annoy_untested="yes"
	else
		enable_annoy_untested="no"
	fi
	]
)
if test "x$enable_annoy_untested" = "xyes" ; then
	AC_DEFINE(WARN_UNTESTED, 1, [Annoy people about unimplemented code])
fi
AC_MSG_RESULT($enable_annoy_untested)
])
