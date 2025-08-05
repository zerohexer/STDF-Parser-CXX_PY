/**
 * @file dump_records_to_html.c
 */
/*
 * Copyright (C) 2004-2006 Mike Frysinger <vapier@gmail.com>
 * Released under the BSD license.  For more information,
 * please see: http://opensource.org/licenses/bsd-license.php
 *
 * $Header: /cvsroot/freestdf/libstdf/examples/dump_records_to_html.c,v 1.13 2005/12/08 04:07:43 vapier Exp $
 */

#include <libstdf.h>

#if defined(HAVE_GETOPT_H)
# include <getopt.h>
#endif

#define	MAX_REC_STYLES	4
int max_width, width, rec_rot;
rec_unknown *raw_rec;

#define	OUT_HEX			1
#define	OUT_ASCII		2

void write_rec(FILE *f, rec_header *h, int type)
{
	int i;
	int towrite, written;
	byte_t *rec;
	int tagged;

	rec = raw_rec->data;
	written = 0;
	tagged = 0;
	h->REC_LEN += 4;

	do {
		towrite = max_width - width;
		if (h->REC_LEN < written + towrite)
			towrite = h->REC_LEN - written;
		for (i=0; i<towrite; ++i) {
			if (tagged > 3) {						/* raw data */
				fprintf(f, "<td class=r%i>", rec_rot);
				if (type == OUT_HEX)
					fprintf(f, "%.2X", rec[i]);
				else {
					if (rec[i] < 0x20 || rec[i] > 0x7F)
						fprintf(f, "%.2X", rec[i]);
					else
						fprintf(f, "%c", rec[i]);
				}
				fprintf(f, "</td>");
			} else {								/* record header */
				if (type == OUT_HEX) {
					fprintf(f, "<td class=r%i><span class='head", rec_rot);
					fprintf(f, (tagged<2)?"len":"type");
					fprintf(f, "'>%.2X</span></td>", rec[i]);
				} else {
					if (tagged == 0)		/* rec len */
						fprintf(f, "<td class=r%i colspan=2><span class=headlen>%i</span></td>",
						        rec_rot, h->REC_LEN - 4);
					else if (tagged == 2)	/* rec type */
						fprintf(f, "<td class=r%i colspan=2><span class=headtype>%s</span></td>",
						        rec_rot, stdf_get_rec_name_from_head((*h)));
					else if (width == 0 && i == 0)
						fprintf(f, "<td class=r%i></td>", rec_rot);
				}
				tagged++;
			}
		}
		width += towrite;
		rec += towrite;
		written += towrite;
		if (width == max_width) {
			fprintf(f, "</tr>\n<tr>");
			width = 0;
		}
	} while (written < h->REC_LEN);
}

void usage(char *prog)
{
	printf("Usage: %s [options] <stdf file> <html file>\n"
#if defined(HAVE_GETOPT_H)
	       "Options:\n"
	       "\t-h\tthis screen\n"
	       "\t-c\t# of records to output (default is 25; 0 to show all)\n"
	       "\t-w\twidth of output (default is 25)\n"
#else
	       "\nin the excellent words of netcat:\n"
	       "/* If your shitbox doesn't have getopt, step into the nineties already. */\n\n"
#endif
	       , prog);
}

int main(int argc, char *argv[])
{
	stdf_file *f;
	char cpu_name[256];
	FILE *out;
	int x, rec_count, max_recs, type;
	dtc_U4 byte_order, stdf_ver;

	max_recs = 25;
	max_width = 25;
#if defined(HAVE_GETOPT_H)
	while ((x=getopt(argc, argv, "c:w:h")) != EOF) {
		switch (x) {
			case 'c':
				max_recs = atoi(optarg);
				break;
			case 'w':
				max_width = atoi(optarg);
				break;
			case 'h':
				usage(argv[0]);
				return EXIT_SUCCESS;
			default:
				usage(argv[0]);
				return EXIT_FAILURE;
		}
	}
	x = argc - optind;
#else
	x = argc - 1;
#endif

	if (x != 2) {
		if (x == 0)
			fprintf(stderr, "Missing source/destination files!\n");
		else if (x == 1)
			fprintf(stderr, "Missing destination file!\n");
		else
			fprintf(stderr, "Too many arguements!\n");
		usage(argv[0]);
		return EXIT_FAILURE;
	}
#if defined(HAVE_GETOPT_H)
	x = optind;
#else
	x = 1;
#endif

	f = stdf_open(argv[x]);
	if (!f) {
		perror("Could not stdf_open file");
		return EXIT_FAILURE;
	}
	stdf_get_setting(f, STDF_SETTING_VERSION, &stdf_ver);
	stdf_get_setting(f, STDF_SETTING_BYTE_ORDER, &byte_order);
	if (byte_order == LITTLE_ENDIAN)
		sprintf(cpu_name, "Little Endian [intel/x86]");
	else if (byte_order == BIG_ENDIAN)
		sprintf(cpu_name, "Big Endian [sun/sparc]");
	else
		sprintf(cpu_name, "Unknown Endian [???]");

	if ((out=fopen(argv[x+1], "w")) == NULL) {
		perror("Could not open html file");
		return EXIT_FAILURE;
	}

	fprintf(out,
	        "<!DOCTYPE html PUBLIC '-//W3C//DTD HTML 4.01//EN' 'http://www.w3.org/TR/html4/strict.dtd'>\n"
	        "<html>\n"
	        "<head>\n"
			" <META HTTP-EQUIV='Content-Type' CONTENT='text/html; charset=ISO-8859-1'\n>"
	        " <title>%s</title>\n"
	        " <style type='text/css'>\n"
	        "  table { border-collapse:collapse; font-family:monospace; }\n"
	        "  td { border: 1px solid #C0C0C0; text-align:center; }\n"
	        "  th { border: 1px solid black; text-align:center; }\n"
	        "  td.r1 { background-color: #DDDAEC; }\n"
	        "  td.r2 { background-color: #D4FFA9; }\n"
	        "  td.r3 { background-color: #FED0D4; }\n"
	        "  td.r4 { background-color: #FEFFC5; }\n"
	        "  span.headlen { font-weight:bolder; }\n"
	        "  span.headtype { font-style:italic; font-weight:bolder; }\n"
	        " </style>\n"
	        "</head>\n"
	        "<body>\n"
	        "<h1>File: %s<br>STDF v%i<br>CPU Type: %i (%s)</h1>\n"
	        "<table><tr>\n",
	        argv[x], argv[x], stdf_ver, byte_order, cpu_name);

	for (type=1; type<3; type++) {
		stdf_close(f);
		f = stdf_open(argv[x]);

		width = 0;
		rec_count = max_recs;
		rec_rot = 1;

		fprintf(out, "<td><table>\n<tr>");
		for (width=0; width<max_width; ++width)
			if (type == OUT_HEX)
				fprintf(out, "<th>%.2X</th>", width);
			else
				fprintf(out, "<th>%i</th>", width);
		fprintf(out, "</tr>\n<tr>");

		while ((raw_rec=stdf_read_record_raw(f)) != NULL) {
			write_rec(out, &(raw_rec->header), type);
			stdf_free_record(raw_rec);
			if (--rec_count == 0)
				break;
			if (++rec_rot > MAX_REC_STYLES)
				rec_rot = 1;
		}
		if (width != 0)
			fprintf(out, "</tr>\n");
		fprintf(out, "</table></td>\n");
	}

	fprintf(out,
	        "</tr></table>\n"
	        "</body>\n"
	        "</html>");

	fclose(out);
	stdf_close(f);

	return EXIT_SUCCESS;
}
