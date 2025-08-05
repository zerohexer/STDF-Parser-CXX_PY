/**
 * @file is_valid_stdf.c
 */
/*
 * Copyright (C) 2004-2006 Mike Frysinger <vapier@gmail.com>
 * Released under the BSD license.  For more information,
 * please see: http://opensource.org/licenses/bsd-license.php
 *
 * $Header: /cvsroot/freestdf/libstdf/examples/is_valid_stdf.c,v 1.6 2005/11/13 08:56:58 vapier Exp $
 */

#include <libstdf.h>

#define	print_msg(m) printf("\t" m "\n");
#define	print_err(m) printf("\tERROR: " m "\n");

int main(int argc, char *argv[])
{
	stdf_file *f;
	rec_unknown *rec;
	rec_header prev_rec;
	long rec_mrr_cnt, rec_pcr_cnt, rec_hbr_cnt, rec_sbr_cnt, rec_wcr_cnt;
	int i;

	if (argc <= 1) {
		printf("Need some files to open!\n");
		return EXIT_FAILURE;
	}

for (i=1; i<argc; ++i) {
	printf("Validating %s", argv[i]);
	f = stdf_open(argv[i]);
	if (!f) {
		perror("Could not open file");
		return EXIT_FAILURE;
	}

	/* STDF spec requires every STDF file have an initial sequence.
	 * A valid sequence can be any of these:
	 FAR -      - MIR
	 FAR - ATRs - MIR
	 FAR -      - MIR - RDR
	 FAR - ATRs - MIR - RDR
	 FAR -      - MIR -     - SDRs
	 FAR - ATRs - MIR -     - SDRs
	 FAR -      - MIR - RDR - SDRs
	 FAR - ATRs - MIR - RDR - SDRs
	 */

	/* Find the FAR record */
	rec = stdf_read_record(f);
	if (rec == NULL || HEAD_TO_REC(rec->header) != REC_FAR) {
		print_err("First record is not FAR!");
		goto next_file;
	}
	stdf_free_record(rec);
	/* Try to read all the ATR records (if they exist) */
	while ((rec=stdf_read_record(f)) != NULL) {
		if (HEAD_TO_REC(rec->header) != REC_ATR)
			break;
		else
			stdf_free_record(rec);
	}
	if (rec == NULL) {
		print_err("Initial sequence not found!");
		goto next_file;
	}
	/* We should now have the MIR record already read in */
	if (HEAD_TO_REC(rec->header) != REC_MIR) {
		print_err("Initial sequence wrong: MIR not located!");
		goto next_file;
	}
	/* Try to read the RDR record (if it exists) */
	stdf_free_record(rec);
	if ((rec=stdf_read_record(f)) == NULL) {
		print_err("EOF found after initial sequence!");
		goto next_file;
	}
	if (HEAD_TO_REC(rec->header) == REC_RDR) {
		stdf_free_record(rec);
		rec = stdf_read_record(f);
		if (rec == NULL) {
			print_err("EOF found after initial sequence!");
			goto next_file;
		}
	}
	/* Try to read the SDR records (if they exist) */
	while (HEAD_TO_REC(rec->header) == REC_SDR) {
		stdf_free_record(rec);
		rec = stdf_read_record(f);
		if (rec == NULL) {
			print_err("EOF found after initial sequence!");
			goto next_file;
		}
	}

	/* Now we read the rest of the file */
	rec_mrr_cnt = rec_pcr_cnt = rec_hbr_cnt = rec_sbr_cnt = rec_wcr_cnt = 0;
	while (1) {
		memcpy(&prev_rec, &rec->header, sizeof(rec_header));
		stdf_free_record(rec);
		rec = stdf_read_record(f);
		if (rec == NULL)
			break;

		switch (HEAD_TO_REC(rec->header)) {
			case REC_FAR:
			case REC_ATR:
			case REC_MIR:
			case REC_RDR:
			case REC_SDR:
				printf("\tFound %s outside of initial sequence!\n",
				       stdf_get_rec_name(rec->header.REC_TYP, rec->header.REC_SUB));
				goto next_file;
			case REC_MRR:
				if (++rec_mrr_cnt > 1) {
					print_err("More than one REC_MRR was found!");
					goto next_file;
				}
				break;
			case REC_PCR: ++rec_pcr_cnt; break;
			case REC_HBR: ++rec_hbr_cnt; break;
			case REC_SBR: ++rec_sbr_cnt; break;

			/* need some logic with these ... */
			case REC_PMR: break;
			case REC_PGR: break;
			case REC_PLR: break;

			case REC_WIR: break; /* only 1 per wafer */
			case REC_WRR: break; /* only 1 per wafer */

			case REC_WCR:
				if (++rec_wcr_cnt > 1) {
					print_err("More than one REC_WCR was found!");
					goto next_file;
				}
				break;

			/* each PIR must have a PRR for same HEAD/SITE */
			/* PTR/MPR/FTR records must appear between the right PIR/PRR pairs */
			/* each BPS/EPS pair must be inside the PIR/PRR pair */
			case REC_PIR: break; /* only 1 per part tested */
			case REC_PTR: break; /* only 1 per part tested */
			case REC_MPR: break; /* only 1 per part tested */
			case REC_FTR: break; /* only 1 per part tested */
			case REC_BPS: break;
			case REC_EPS: break;
			case REC_PRR: break; /* only 1 per part tested */

			case REC_TSR: break;
			case REC_GDR: break;
	
			default:
				print_err("Uknown record found!");
				goto next_file;
		}
	}
	if (HEAD_TO_REC(prev_rec) != REC_MRR) {
		print_err("REC_MRR was not the last record in the stream!");
		goto next_file;
	}

	print_msg("... is valid");
next_file:
	stdf_free_record(rec);
	stdf_close(f);
}
	return EXIT_SUCCESS;
}
