/**
 * @file extract_records.c
 */
/*
 * Copyright (C) 2004-2006 Mike Frysinger <vapier@gmail.com>
 * Released under the BSD license.  For more information,
 * please see: http://opensource.org/licenses/bsd-license.php
 *
 * $Header: /cvsroot/freestdf/libstdf/examples/extract_records.c,v 1.4 2005/11/13 08:56:58 vapier Exp $
 */

#include <libstdf.h>

void usage(char *prog)
{
	printf("Usage: %s <stdf input file> <stdf output file>\n", prog);
}

int main(int argc, char *argv[])
{
	rec_unknown *raw_rec, *parsed_rec;
	stdf_file *f;
	char *filename_in, *filename_out;
	FILE *out;
	char *input, *in;
	long count;

	if (argc != 3) {
		if (argc == 1)
			fprintf(stderr, "Missing source/destination files!\n");
		else if (argc == 2)
			fprintf(stderr, "Missing destination file!\n");
		else
			fprintf(stderr, "Too many arguements!\n");
		usage(argv[0]);
		return EXIT_FAILURE;
	}
	filename_in = argv[1];
	filename_out = argv[2];

	f = stdf_open(filename_in);
	if (!f) {
		perror("Could not stdf_open file");
		return EXIT_FAILURE;
	}

	if ((out=fopen(filename_out, "w")) == NULL) {
		perror("Could not open html file");
		return EXIT_FAILURE;
	}

	printf("Record Extractor\n"
	       "Source: '%s'\n"
	       "Output: '%s'\n"
	       "Options: [Y]es [N]o [A]ll ne[V]er [Q]uit\n",
	       filename_in, filename_out);

	input = calloc(stdf_rec_to_idx_count(), sizeof(char));
	count = 1;

	printf("\nAuto saving the FAR record\n");
	raw_rec = stdf_read_record_raw(f);
	parsed_rec = stdf_parse_raw_record(raw_rec);
	fwrite(raw_rec->data, parsed_rec->header.REC_LEN+4, 1, out);
	stdf_free_record(parsed_rec);
	stdf_free_record(raw_rec);

	while ((raw_rec=stdf_read_record_raw(f)) != NULL) {
		parsed_rec = stdf_parse_raw_record(raw_rec);

		in = &(input[stdf_rec_to_idx(parsed_rec)]);
printf("%i\n", stdf_rec_to_idx(parsed_rec));
		if (*in != 'A' && *in != 'V') {
			printf("Found a %s, extract? ", stdf_get_rec_name_from_rec(parsed_rec));
			do {
				scanf("%c", in);
				*in = toupper(*in);
			} while (strchr("YNAVQ", *in) == NULL);
		}

		if (*in == 'Y' || *in == 'A') {
			fwrite(raw_rec->data, parsed_rec->header.REC_LEN+4, 1, out);
			count++;
		}

		stdf_free_record(parsed_rec);
		stdf_free_record(raw_rec);

		if (*in == 'Q' || *in == '\0') {
			printf("\n");
			break;
		}
	}
	printf("\n\nExtracted %li records\n", count);

	free(input);

	fclose(out);
	stdf_close(f);

	return EXIT_SUCCESS;
}
