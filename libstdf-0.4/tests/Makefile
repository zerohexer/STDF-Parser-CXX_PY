# Dirty little tests

EXAMPLE_DIR  = ../examples
STDF         = stdf.bz2
BZCMP        = bzdiff

all install:

check: ascii html stats create

ascii:
	$(EXAMPLE_DIR)/dump_records_to_ascii $(STDF) > ascii.out
	$(BZCMP) ascii.out ascii.good.bz2

html:
	$(EXAMPLE_DIR)/dump_records_to_html $(STDF) html.out
	$(BZCMP) html.out html.good.bz2

stats:
	$(EXAMPLE_DIR)/record_stats $(STDF) | sort > stats.out
	$(BZCMP) stats.out stats.good.bz2

create:
	$(EXAMPLE_DIR)/makestdf create.out
	$(BZCMP) create.out create.good.bz2

distdir:
	@cp Makefile *.bz2 $(distdir)

distclean clean:
	rm -f *.out

.PHONY: all install check ascii html stats create distdir distclean clean
