/**
 * @file stdf2img.c
 */
/*
 * Copyright (C) 2005-2006 Mike Frysinger <vapier@gmail.com>
 * Released under the BSD license.  For more information,
 * please see: http://opensource.org/licenses/bsd-license.php
 *
 * $Header: /cvsroot/freestdf/libstdf/examples/stdf2img.c,v 1.3 2005/11/13 08:56:58 vapier Exp $
 */

#include <libstdf.h>
#include <gd.h>

int main(int argc, char *argv[])
{
	stdf_file *f;
	rec_unknown *r;

	dtc_I2 x_min, y_min, x_max, y_max, x, y, x_range, y_range;
	dtc_U2 *hard_bins, *soft_bins;

	if (argc != 2) {
		printf("Usage: %s <stdf file>\n", argv[0]);
		return EXIT_FAILURE;
	}

	f = stdf_open(argv[1]);
	if (!f)
		return EXIT_FAILURE;

	x_min = y_min = x_max = y_max = 0;

	while ((r=stdf_read_record(f)) != NULL) {
		switch (HEAD_TO_REC(r->header)) {
			case REC_MIR:
				break;
			case REC_PRR: {
				rec_prr *prr = (rec_prr*)r;
				if (x_min > prr->X_COORD) x_min = prr->X_COORD;
				if (y_min > prr->Y_COORD) y_min = prr->Y_COORD;
				if (x_max < prr->X_COORD) x_max = prr->X_COORD;
				if (y_max < prr->Y_COORD) y_max = prr->Y_COORD;
				break;
			}
		}
		stdf_free_record(r);
	}
	stdf_close(f);

	x_range = x_max - x_min + 1	;
	y_range = y_max - y_min + 1;

	hard_bins = (dtc_U2*)malloc(sizeof(dtc_U2) * x_range * y_range);
	if (!hard_bins) perror("hard_bins malloc failed");
	memset(hard_bins, 0, sizeof(dtc_U2) * x_range * y_range);

	soft_bins = (dtc_U2*)malloc(sizeof(dtc_U2) * x_range * y_range);
	if (!soft_bins) perror("soft_bins malloc failed");
	memset(soft_bins, 0, sizeof(dtc_U2) * x_range * y_range);

	f = stdf_open(argv[1]);
	if (!f)
		return EXIT_FAILURE;
	while ((r=stdf_read_record(f)) != NULL) {
		switch (HEAD_TO_REC(r->header)) {
			case REC_PRR: {
				rec_prr *prr = (rec_prr*)r;
				x = prr->X_COORD - x_min;
				y = prr->Y_COORD - y_min;
				hard_bins[x*x_range + y] = prr->HARD_BIN;
				soft_bins[x*x_range + y] = prr->SOFT_BIN;
				break;
			}
		}
		stdf_free_record(r);
	}
	stdf_close(f);

	{
		dtc_U2 bin;
		gdImagePtr hardim, softim;
		int hard_colors[50], soft_colors[50];
		FILE *outimg;
		memset(hard_colors, 0x00, sizeof(hard_colors));
		memset(soft_colors, 0x00, sizeof(soft_colors));
		hardim = gdImageCreate(x_range, y_range);
		softim = gdImageCreate(x_range, y_range);
		for (x = 0; x < x_range; ++x)
			for (y = 0; y < y_range; ++y) {
				int r, g, b, hc = 0, sc = 0;
				bin = hard_bins[x*x_range+y];
				if (bin < sizeof(hard_colors)/sizeof(*hard_colors)) {
					if (hard_colors[bin] == 0) {
						r = rand()%255;
						g = rand()%255;
						b = rand()%255;
						hc = hard_colors[bin] = gdImageColorAllocate(hardim, r, g, b);
						sc = soft_colors[bin] = gdImageColorAllocate(softim, r, g, b);
					}
				} else {
					fprintf(stderr, "whoops, got a big bin ... using black color %i\n", bin);
					hc = gdImageColorAllocate(hardim, 0, 0, 0);
					sc = gdImageColorAllocate(softim, 0, 0, 0);
				}
				gdImageSetPixel(hardim, x, y, hc);
				gdImageSetPixel(softim, x, y, sc);
			}

		outimg = fopen("hard.gif", "wb");
		gdImageGif(hardim, outimg);
		fclose(outimg);
		gdImageDestroy(hardim);
		outimg = fopen("soft.gif", "wb");
		gdImageGif(softim, outimg);
		fclose(outimg);
		gdImageDestroy(softim);
	}

	free(hard_bins);
	free(soft_bins);

	return EXIT_SUCCESS;
}
