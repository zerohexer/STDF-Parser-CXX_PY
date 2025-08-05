SUBDIRS = doc include src examples tests

bin_SCRIPTS = libstdf-config

EXTRA_DIST = AUTHORS COPYING ChangeLog INSTALL NEWS README

pkgconfigdir = $(libdir)/pkgconfig
pkgconfig_DATA = libstdf.pc

install-data-hook:
if BUILD_DOCS
	doxygen
	$(INSTALL) -d $(DESTDIR)/$(pkgdatadir)/
	cp -pR $(top_srcdir)/doc/html/* $(DESTDIR)/$(pkgdatadir)/
endif

ACLOCAL_AMFLAGS = -I m4
AUTOMAKE_OPTIONS = dist-bzip2 no-dist-gzip
