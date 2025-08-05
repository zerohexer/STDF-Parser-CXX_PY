/**
 * @file dump_records_to_ascii.c
 */
/*
 * Copyright (C) 2004-2006 Mike Frysinger <vapier@gmail.com>
 * Released under the BSD license.  For more information,
 * please see: http://opensource.org/licenses/bsd-license.php
 *
 * $Header: /cvsroot/freestdf/libstdf/examples/dump_records_to_ascii.c,v 1.23 2005/12/08 04:07:43 vapier Exp $
 */

#include <libstdf.h>

#define print_fmt(n,f,v) printf("\t" n ": " f, v)
#define print_int(n,i) print_fmt(n, "%i\n", i)
#define print_str(n,s) print_fmt(n, "%s\n", (*(s) ? (s)+1 : "(null)"))
#define print_chr(n,c) print_fmt(n, "%c\n", c)
#define print_hex(n,h) print_fmt(n, "%X\n", h)
#define print_rel(n,r) print_fmt(n, "%f\n", r)
#define print_tim(n,d) \
	do { time_t t = d; print_fmt(n, "%s", ctime(&t)); } while(0)

#define MAKE_PRINT_X(DTC, OUTPUT_FUNC, FORMAT) \
void print_x ## DTC(char *n, dtc_x ## DTC u, dtc_U2 c) \
{ \
	dtc_U2 i; \
	printf("\t%s: ", n); \
	for (i=0; i<c; ++i) { \
		OUTPUT_FUNC(FORMAT, u[i]); \
		if (i+1 < c) printf(", "); \
	} \
	printf("\n"); \
}
MAKE_PRINT_X(U1, printf, "%u")
MAKE_PRINT_X(U2, printf, "%u")
MAKE_PRINT_X(R4, printf, "%f")

#define _printf_xCn(fmt,Cn) printf(fmt, (*Cn ? Cn+1 : "(null)"))
MAKE_PRINT_X(Cn, _printf_xCn, "%s")

void print_xN1(char *member, dtc_xN1 xN1, dtc_U2 c)
{
	dtc_N1 *n = xN1;
	printf("\t%s: ", member);
	while (c > 0) {
		if (c > 1) {
			printf("%X %X ", ((*n) & 0xF0) >> 4, (*n) & 0x0F);
			c -= 2;
		} else {
			printf("%X", ((*n) & 0xF0) >> 4);
			break;
		}
		++n;
	}
	printf("\n");
}

void print_Vn(char *n, dtc_Vn v, int c)
{
	int i;
	--c;
	printf("\t%s:\n", n);
	for (i=0; i<=c; ++i) {
		printf("\t\t%s: ", stdf_get_Vn_name(v[i].type));
		switch (v[i].type) {
			case GDR_B0: printf("(pad)"); break;
			case GDR_U1: printf("%i", *((dtc_U1*)v[i].data)); break;
			case GDR_U2: printf("%i", *((dtc_U2*)v[i].data)); break;
			case GDR_U4: printf("%i", *((dtc_U4*)v[i].data)); break;
			case GDR_I1: printf("%i", *((dtc_I1*)v[i].data)); break;
			case GDR_I2: printf("%i", *((dtc_I2*)v[i].data)); break;
			case GDR_I4: printf("%i", *((dtc_I4*)v[i].data)); break;
			case GDR_R4: printf("%f", *((dtc_R4*)v[i].data)); break;
			case GDR_R8: printf("%f", *((dtc_R8*)v[i].data)); break;
			case GDR_Cn: {
				dtc_Cn Cn = *((dtc_Cn*)v[i].data);
				printf("%s", (*Cn ? Cn+1 : "(null"));
				break;
			}
			case GDR_Bn: printf("[??]"); break;
			case GDR_Dn: printf("[??]"); break;
			case GDR_N1: printf("%X", *((dtc_N1*)v[i].data)); break;
		}
		printf("\n");
	}
	if (c == -1)
		printf("\n");
}
void print_Bn(dtc_C1 *n, dtc_Bn b)
{
	int i;
	printf("\t%s:", n);
	for (i=1; i<=*b; ++i)
		printf(" %X", *(b+i));
	if (*b == 0)
		printf(" (null)");
	printf("\n");
}
void print_Dn(dtc_C1 *n, dtc_Dn d)
{
	int i;
	dtc_U2 *num_bits = (dtc_U2*)d, len;
	len = *num_bits / 8;
	if (*num_bits % 8) ++len;
	printf("\t%s:", n);
	for (i=2; i<len; ++i)
		printf(" %X", *(d+i));
	if (len == 0)
		printf(" (null)");
	printf("\n");
}

#define print_UNK(n) \
	do { \
		fprintf(stderr, "******************************************\n"); \
		fprintf(stderr, "This field (" n ") has not been tested!\n"); \
		fprintf(stderr, "Please consider sending this file to\n"); \
		fprintf(stderr, "vapier@gmail.com to help out the\n"); \
		fprintf(stderr, "FreeSTDF project and make sure this code\n"); \
		fprintf(stderr, "works exactly the way it should!\n"); \
		fprintf(stderr, "******************************************\n"); \
	} while (0)

int main(int argc, char *argv[])
{
	stdf_file *f;
	char *recname;
	rec_unknown *rec;
	int i;
	dtc_U4 stdf_ver;

	if (argc <= 1) {
		printf("Need some files to open!\n");
		return EXIT_FAILURE;
	}

for (i=1; i<argc; ++i) {
	printf("Dumping %s\n", argv[i]);
	f = stdf_open(argv[i]);
	if (!f) {
		perror("Could not open file");
		continue;
	}
	stdf_get_setting(f, STDF_SETTING_VERSION, &stdf_ver);

	while ((rec=stdf_read_record(f)) != NULL) {
		recname = stdf_get_rec_name(rec->header.REC_TYP, rec->header.REC_SUB);
		printf("Record %s (%3i,%3i) %i bytes:\n", recname, rec->header.REC_TYP,
		       rec->header.REC_SUB, rec->header.REC_LEN);
		switch (HEAD_TO_REC(rec->header)) {
			case REC_FAR: {
				rec_far *far = (rec_far*)rec;
				print_int("CPU_TYPE", far->CPU_TYPE);
				print_int("STDF_VER", far->STDF_VER);
				break;
			}
			case REC_ATR: {
				rec_atr *atr = (rec_atr*)rec;
				print_tim("MOD_TIM", atr->MOD_TIM);
				print_str("CMD_LINE", atr->CMD_LINE);
				break;
			}
			case REC_MIR: {
				rec_mir *mir = (rec_mir*)rec;
#ifdef STDF_VER3
				if (stdf_ver == 4) {
#endif
				print_tim("SETUP_T", mir->SETUP_T);
				print_tim("START_T", mir->START_T);
				print_int("STAT_NUM", mir->STAT_NUM);
				print_chr("MODE_COD", mir->MODE_COD);
				print_chr("RTST_COD", mir->RTST_COD);
				print_chr("PROT_COD", mir->PROT_COD);
				print_int("BURN_TIM", mir->BURN_TIM);
				print_chr("CMOD_COD", mir->CMOD_COD);
				print_str("LOT_ID", mir->LOT_ID);
				print_str("PART_TYP", mir->PART_TYP);
				print_str("NODE_NAM", mir->NODE_NAM);
				print_str("TSTR_TYP", mir->TSTR_TYP);
				print_str("JOB_NAM", mir->JOB_NAM);
				print_str("JOB_REV", mir->JOB_REV);
				print_str("SBLOT_ID", mir->SBLOT_ID);
				print_str("OPER_NAM", mir->OPER_NAM);
				print_str("EXEC_TYP", mir->EXEC_TYP);
				print_str("EXEC_VER", mir->EXEC_VER);
				print_str("TEST_COD", mir->TEST_COD);
				print_str("TST_TEMP", mir->TST_TEMP);
				print_str("USER_TXT", mir->USER_TXT);
				print_str("AUX_FILE", mir->AUX_FILE);
				print_str("PKG_TYP", mir->PKG_TYP);
				print_str("FAMILY_ID", mir->FAMILY_ID);
				print_str("DATE_COD", mir->DATE_COD);
				print_str("FACIL_ID", mir->FACIL_ID);
				print_str("FLOOR_ID", mir->FLOOR_ID);
				print_str("PROC_ID", mir->PROC_ID);
				print_str("OPER_FRQ", mir->OPER_FRQ);
				print_str("SPEC_NAM", mir->SPEC_NAM);
				print_str("SPEC_VER", mir->SPEC_VER);
				print_str("FLOW_ID", mir->FLOW_ID);
				print_str("SETUP_ID", mir->SETUP_ID);
				print_str("DSGN_REV", mir->DSGN_REV);
				print_str("ENG_ID", mir->ENG_ID);
				print_str("ROM_COD", mir->ROM_COD);
				print_str("SERL_NUM", mir->SERL_NUM);
				print_str("SUPR_NAM", mir->SUPR_NAM);
#ifdef STDF_VER3
				} else {
				print_int("CPU_TYPE", mir->CPU_TYPE);
				print_int("STDF_VER", mir->STDF_VER);
				print_chr("MODE_COD", mir->MODE_COD);
				print_int("STAT_NUM", mir->STAT_NUM);
				print_str("TEST_COD", mir->TEST_COD);
				print_chr("RTST_COD", mir->RTST_COD);
				print_chr("PROT_COD", mir->PROT_COD);
				print_chr("CMOD_COD", mir->CMOD_COD);
				print_tim("SETUP_T", mir->SETUP_T);
				print_tim("START_T", mir->START_T);
				print_str("LOT_ID", mir->LOT_ID);
				print_str("PART_TYP", mir->PART_TYP);
				print_str("JOB_NAM", mir->JOB_NAM);
				print_str("OPER_NAM", mir->OPER_NAM);
				print_str("NODE_NAM", mir->NODE_NAM);
				print_str("TSTR_TYP", mir->TSTR_TYP);
				print_str("EXEC_TYP", mir->EXEC_TYP);
				print_str("SUPR_NAM", mir->SUPR_NAM);
				print_str("HAND_ID", mir->HAND_ID);
				print_str("SBLOT_ID", mir->SBLOT_ID);
				print_str("JOB_REV", mir->JOB_REV);
				print_str("PROC_ID", mir->PROC_ID);
				print_str("PRB_CARD", mir->PRB_CARD);
				}
#endif
				break;
			}
			case REC_MRR: {
				rec_mrr *mrr = (rec_mrr*)rec;
				print_tim("FINISH_T", mrr->FINISH_T);
#ifdef STDF_VER3
				if (stdf_ver == 3) {
				print_int("PART_CNT", mrr->PART_CNT);
				print_int("RTST_CNT", mrr->RTST_CNT);
				print_int("ABRT_CNT", mrr->ABRT_CNT);
				print_int("GOOD_CNT", mrr->GOOD_CNT);
				print_int("FUNC_CNT", mrr->FUNC_CNT);
				}
#endif
				print_chr("DISP_COD", mrr->DISP_COD);
				print_str("USR_DESC", mrr->USR_DESC);
				print_str("EXC_DESC", mrr->EXC_DESC);
				break;
			}
			case REC_PCR: {
				rec_pcr *pcr = (rec_pcr*)rec;
				print_int("HEAD_NUM", pcr->HEAD_NUM);
				print_int("SITE_NUM", pcr->SITE_NUM);
				print_int("PART_CNT", pcr->PART_CNT);
				print_int("RTST_CNT", pcr->RTST_CNT);
				print_int("ABRT_CNT", pcr->ABRT_CNT);
				print_int("GOOD_CNT", pcr->GOOD_CNT);
				print_int("FUNC_CNT", pcr->FUNC_CNT);
				break;
			}
			case REC_HBR: {
				rec_hbr *hbr = (rec_hbr*)rec;
				print_int("HEAD_NUM", hbr->HEAD_NUM);
				print_int("SITE_NUM", hbr->SITE_NUM);
				print_int("HBIN_NUM", hbr->HBIN_NUM);
				print_int("HBIN_CNT", hbr->HBIN_CNT);
				print_chr("HBIN_PF", hbr->HBIN_PF);
				print_str("HBIN_NAM", hbr->HBIN_NAM);
				break;
			}
			case REC_SBR: {
				rec_sbr *sbr = (rec_sbr*)rec;
				print_int("HEAD_NUM", sbr->HEAD_NUM);
				print_int("SITE_NUM", sbr->SITE_NUM);
				print_int("SBIN_NUM", sbr->SBIN_NUM);
				print_int("SBIN_CNT", sbr->SBIN_CNT);
				print_chr("SBIN_PF", sbr->SBIN_PF);
				print_str("SBIN_NAM", sbr->SBIN_NAM);
				break;
			}
			case REC_PMR: {
				rec_pmr *pmr = (rec_pmr*)rec;
				print_int("PMR_INDX", pmr->PMR_INDX);
				print_int("CHAN_TYP", pmr->CHAN_TYP);
				print_str("CHAN_NAM", pmr->CHAN_NAM);
				print_str("PHY_NAM", pmr->PHY_NAM);
				print_str("LOG_NAM", pmr->LOG_NAM);
				print_int("HEAD_NUM", pmr->HEAD_NUM);
				print_int("SITE_NUM", pmr->SITE_NUM);
				break;
			}
			case REC_PGR: {
				rec_pgr *pgr = (rec_pgr*)rec;
				print_int("GRP_INDX", pgr->GRP_INDX);
				print_str("GRP_NAM", pgr->GRP_NAM);
				print_int("INDX_CNT", pgr->INDX_CNT);
				print_xU2("PMR_INDX", pgr->PMR_INDX, pgr->INDX_CNT);
				break;
			}
			case REC_PLR: {
				rec_plr *plr = (rec_plr*)rec;
				print_int("GRP_CNT", plr->GRP_CNT);
				print_xU2("GRP_INDX", plr->GRP_INDX, plr->GRP_CNT);
				print_xU2("GRP_MODE", plr->GRP_MODE, plr->GRP_CNT);
				print_xU1("GRP_RADX", plr->GRP_RADX, plr->GRP_CNT);
				print_xCn("PGM_CHAR", plr->PGM_CHAR, plr->GRP_CNT);
				print_xCn("RTN_CHAR", plr->RTN_CHAR, plr->GRP_CNT);
				print_xCn("PGM_CHAL", plr->PGM_CHAL, plr->GRP_CNT);
				print_xCn("RTN_CHAL", plr->RTN_CHAL, plr->GRP_CNT);
				break;
			}
			case REC_RDR: {
				rec_rdr *rdr = (rec_rdr*)rec;
				print_int("NUM_BINS", rdr->NUM_BINS);
				print_xU2("RTST_BIN", rdr->RTST_BIN, rdr->NUM_BINS);
				break;
			}
			case REC_SDR: {
				rec_sdr *sdr = (rec_sdr*)rec;
				print_int("HEAD_NUM", sdr->HEAD_NUM);
				print_int("SITE_GRP", sdr->SITE_GRP);
				print_int("SITE_CNT", sdr->SITE_CNT);
				print_xU1("SITE_NUM", sdr->SITE_NUM, sdr->SITE_CNT);
				print_str("HAND_TYP", sdr->HAND_TYP);
				print_str("HAND_ID", sdr->HAND_ID);
				print_str("CARD_TYP", sdr->CARD_TYP);
				print_str("CARD_ID", sdr->CARD_ID);
				print_str("LOAD_TYP", sdr->LOAD_TYP);
				print_str("LOAD_ID", sdr->LOAD_ID);
				print_str("DIB_TYP", sdr->DIB_TYP);
				print_str("DIB_ID", sdr->DIB_ID);
				print_str("CABL_TYP", sdr->CABL_TYP);
				print_str("CABL_ID", sdr->CABL_ID);
				print_str("CONT_TYP", sdr->CONT_TYP);
				print_str("CONT_ID", sdr->CONT_ID);
				print_str("LASR_TYP", sdr->LASR_TYP);
				print_str("LASR_ID", sdr->LASR_ID);
				print_str("EXTR_TYP", sdr->EXTR_TYP);
				print_str("EXTR_ID", sdr->EXTR_ID);
				break;
			}
			case REC_WIR: {
				rec_wir *wir = (rec_wir*)rec;
				print_int("HEAD_NUM", wir->HEAD_NUM);
#ifdef STDF_VER3
				if (stdf_ver == 3)
				print_hex("PAD_BYTE", wir->PAD_BYTE);
				else
#endif
				print_int("SITE_GRP", wir->SITE_GRP);
				print_tim("START_T", wir->START_T);
				print_str("WAFER_ID", wir->WAFER_ID);
				break;
			}
			case REC_WRR: {
				rec_wrr *wrr = (rec_wrr*)rec;
#ifdef STDF_VER3
				if (stdf_ver == 4) {
#endif
				print_int("HEAD_NUM", wrr->HEAD_NUM);
				print_int("SITE_GRP", wrr->SITE_GRP);
				print_tim("FINISH_T", wrr->FINISH_T);
#ifdef STDF_VER3
				} else {
				print_tim("FINISH_T", wrr->FINISH_T);
				print_int("HEAD_NUM", wrr->HEAD_NUM);
				print_hex("PAD_BYTE", wrr->PAD_BYTE);
				}
#endif
				print_int("PART_CNT", wrr->PART_CNT);
				print_int("RTST_CNT", wrr->RTST_CNT);
				print_int("ABRT_CNT", wrr->ABRT_CNT);
				print_int("GOOD_CNT", wrr->GOOD_CNT);
				print_int("FUNC_CNT", wrr->FUNC_CNT);
				print_str("WAFER_ID", wrr->WAFER_ID);
#ifdef STDF_VER3
				if (stdf_ver == 4) {
#endif
				print_str("FABWF_ID", wrr->FABWF_ID);
				print_str("FRAME_ID", wrr->FRAME_ID);
				print_str("MASK_ID", wrr->MASK_ID);
#ifdef STDF_VER3
				} else {
				print_str("HAND_ID", wrr->HAND_ID);
				print_str("PRB_CARD", wrr->PRB_CARD);
				}
#endif
				print_str("USR_DESC", wrr->USR_DESC);
				print_str("EXC_DESC", wrr->EXC_DESC);
				break;
			}
			case REC_WCR: {
				rec_wcr *wcr = (rec_wcr*)rec;
				print_rel("WAFR_SIZ", wcr->WAFR_SIZ);
				print_rel("DIE_HT", wcr->DIE_HT);
				print_rel("DIE_WID", wcr->DIE_WID);
				print_int("WF_UNITS", wcr->WF_UNITS);
				print_chr("WF_FLAT", wcr->WF_FLAT);
				print_int("CENTER_X", wcr->CENTER_X);
				print_int("CENTER_Y", wcr->CENTER_Y);
				print_chr("POS_X", wcr->POS_X);
				print_chr("POS_Y", wcr->POS_Y);
				break;
			}
			case REC_PIR: {
				rec_pir *pir = (rec_pir*)rec;
				print_int("HEAD_NUM", pir->HEAD_NUM);
				print_int("SITE_NUM", pir->SITE_NUM);
#ifdef STDF_VER3
				if (stdf_ver == 3) {
				print_int("X_COORD", pir->X_COORD);
				print_int("Y_COORD", pir->Y_COORD);
				print_str("PART_ID", pir->PART_ID);
				}
#endif
				break;
			}
			case REC_PRR: {
				rec_prr *prr = (rec_prr*)rec;
				print_int("HEAD_NUM", prr->HEAD_NUM);
				print_int("SITE_NUM", prr->SITE_NUM);
#ifdef STDF_VER3
				if (stdf_ver == 4)
#endif
				print_hex("PART_FLG", prr->PART_FLG);
				print_int("NUM_TEST", prr->NUM_TEST);
				print_int("HARD_BIN", prr->HARD_BIN);
				print_int("SOFT_BIN", prr->SOFT_BIN);
#ifdef STDF_VER3
				if (stdf_ver == 3) {
				print_hex("PART_FLG", prr->PART_FLG);
				print_hex("PAD_BYTE", prr->PAD_BYTE);
				}
#endif
				print_int("X_COORD", prr->X_COORD);
				print_int("Y_COORD", prr->Y_COORD);
#ifdef STDF_VER3
				if (stdf_ver == 4)
#endif
				print_tim("TEST_T", prr->TEST_T);
				print_str("PART_ID", prr->PART_ID);
				print_str("PART_TXT", prr->PART_TXT);
				print_Bn("PART_FIX", prr->PART_FIX);
				break;
			}
#ifdef STDF_VER3
			case REC_PDR: {
				rec_pdr *pdr = (rec_pdr*)rec;
				print_int("TEST_NUM", pdr->TEST_NUM);
				print_hex("DESC_FLG", pdr->DESC_FLG);
				print_hex("OPT_FLAG", pdr->OPT_FLAG);
				print_int("RES_SCAL", pdr->RES_SCAL);
				print_str("UNITS", pdr->UNITS);
				print_int("RES_LDIG", pdr->RES_LDIG);
				print_int("RES_RDIG", pdr->RES_RDIG);
				print_int("LLM_SCAL", pdr->LLM_SCAL);
				print_int("HLM_SCAL", pdr->HLM_SCAL);
				print_int("LLM_LDIG", pdr->LLM_LDIG);
				print_int("LLM_RDIG", pdr->LLM_RDIG);
				print_int("HLM_LDIG", pdr->HLM_LDIG);
				print_int("HLM_RDIG", pdr->HLM_RDIG);
				print_rel("LO_LIMIT", pdr->LO_LIMIT);
				print_rel("HI_LIMIT", pdr->HI_LIMIT);
				print_str("TEST_NAM", pdr->TEST_NAM);
				print_str("SEQ_NAME", pdr->SEQ_NAME);
				break;
			}
			case REC_FDR: {
				rec_fdr *fdr = (rec_fdr*)rec;
				print_int("TEST_NUM", fdr->TEST_NUM);
				print_hex("DESC_FLG", fdr->DESC_FLG);
				print_str("TEST_NAM", fdr->TEST_NAM);
				print_str("SEQ_NAME", fdr->SEQ_NAME);
				break;
			}
#endif
			case REC_TSR: {
				rec_tsr *tsr = (rec_tsr*)rec;
				print_int("HEAD_NUM", tsr->HEAD_NUM);
				print_int("SITE_NUM", tsr->SITE_NUM);
#ifdef STDF_VER3
				if (stdf_ver == 4)
#endif
				print_chr("TEST_TYP", tsr->TEST_TYP);
				print_int("TEST_NUM", tsr->TEST_NUM);
				print_int("EXEC_CNT", tsr->EXEC_CNT);
				print_int("FAIL_CNT", tsr->FAIL_CNT);
				print_int("ALRM_CNT", tsr->ALRM_CNT);
#ifdef STDF_VER3
				if (stdf_ver == 4) {
#endif
				print_str("TEST_NAM", tsr->TEST_NAM);
				print_str("SEQ_NAME", tsr->SEQ_NAME);
				print_str("TEST_LBL", tsr->TEST_LBL);
				print_hex("OPT_FLAG", tsr->OPT_FLAG);
				print_rel("TEST_TIM", tsr->TEST_TIM);
				print_rel("TEST_MIN", tsr->TEST_MIN);
				print_rel("TEST_MAX", tsr->TEST_MAX);
				print_rel("TST_SUMS", tsr->TST_SUMS);
				print_rel("TST_SQRS", tsr->TST_SQRS);
#ifdef STDF_VER3
				} else {
				print_hex("OPT_FLAG", tsr->OPT_FLAG);
				print_hex("PAD_BYTE", tsr->PAD_BYTE);
				print_rel("TEST_MIN", tsr->TEST_MIN);
				print_rel("TEST_MAX", tsr->TEST_MAX);
				print_rel("TST_MEAN", tsr->TST_MEAN);
				print_rel("TST_SDEV", tsr->TST_SDEV);
				print_rel("TST_SUMS", tsr->TST_SUMS);
				print_rel("TST_SQRS", tsr->TST_SQRS);
				print_str("TEST_NAM", tsr->TEST_NAM);
				print_str("SEQ_NAME", tsr->SEQ_NAME);
				}
#endif
				break;
			}
			case REC_PTR: {
				rec_ptr *ptr = (rec_ptr*)rec;
				print_int("TEST_NUM", ptr->TEST_NUM);
				print_int("HEAD_NUM", ptr->HEAD_NUM);
				print_int("SITE_NUM", ptr->SITE_NUM);
				print_hex("TEST_FLG", ptr->TEST_FLG);
				print_hex("PARM_FLG", ptr->PARM_FLG);
				print_rel("RESULT", ptr->RESULT);
				print_str("TEST_TXT", ptr->TEST_TXT);
				print_str("ALARM_ID", ptr->ALARM_ID);
				print_hex("OPT_FLAG", ptr->OPT_FLAG);
				print_int("RES_SCAL", ptr->RES_SCAL);
				print_int("LLM_SCAL", ptr->LLM_SCAL);
				print_int("HLM_SCAL", ptr->HLM_SCAL);
				print_rel("LO_LIMIT", ptr->LO_LIMIT);
				print_rel("HI_LIMIT", ptr->HI_LIMIT);
				print_str("UNITS", ptr->UNITS);
				print_str("C_RESFMT", ptr->C_RESFMT);
				print_str("C_LLMFMT", ptr->C_LLMFMT);
				print_str("C_HLMFMT", ptr->C_HLMFMT);
				print_rel("LO_SPEC", ptr->LO_SPEC);
				print_rel("HI_SPEC", ptr->HI_SPEC);
				break;
			}
			case REC_MPR: {
				rec_mpr *mpr = (rec_mpr*)rec;
				print_int("TEST_NUM", mpr->TEST_NUM);
				print_int("HEAD_NUM", mpr->HEAD_NUM);
				print_int("SITE_NUM", mpr->SITE_NUM);
				print_hex("TEST_FLG", mpr->TEST_FLG);
				print_hex("PARM_FLG", mpr->PARM_FLG);
				print_int("RTN_ICNT", mpr->RTN_ICNT);
				print_int("RSLT_CNT", mpr->RSLT_CNT);
				print_xN1("RTN_STAT", mpr->RTN_STAT, mpr->RTN_ICNT);
				print_xR4("RTN_RSLT", mpr->RTN_RSLT, mpr->RSLT_CNT);
				print_str("TEST_TXT", mpr->TEST_TXT);
				print_str("ALARM_ID", mpr->ALARM_ID);
				print_hex("OPT_FLAG", mpr->OPT_FLAG);
				print_int("RES_SCAL", mpr->RES_SCAL);
				print_int("LLM_SCAL", mpr->LLM_SCAL);
				print_int("HLM_SCAL", mpr->HLM_SCAL);
				print_rel("LO_LIMIT", mpr->LO_LIMIT);
				print_rel("HI_LIMIT", mpr->HI_LIMIT);
				print_rel("START_IN", mpr->START_IN);
				print_rel("INCR_IN", mpr->INCR_IN);
				print_xU2("RTN_INDX", mpr->RTN_INDX, mpr->RTN_ICNT);
				print_str("UNITS", mpr->UNITS);
				print_str("UNITS_IN", mpr->UNITS_IN);
				print_str("C_RESFMT", mpr->C_RESFMT);
				print_str("C_LLMFMT", mpr->C_LLMFMT);
				print_str("C_HLMFMT", mpr->C_HLMFMT);
				print_rel("LO_SPEC", mpr->LO_SPEC);
				print_rel("HI_SPEC", mpr->HI_SPEC);
				break;
			}
			case REC_FTR: {
				rec_ftr *ftr = (rec_ftr*)rec;
				print_int("TEST_NUM", ftr->TEST_NUM);
				print_int("HEAD_NUM", ftr->HEAD_NUM);
				print_int("SITE_NUM", ftr->SITE_NUM);
				print_hex("TEST_FLG", ftr->TEST_FLG);
				print_hex("OPT_FLAG", ftr->OPT_FLAG);
				print_int("CYCL_CNT", ftr->CYCL_CNT);
				print_int("REL_VADR", ftr->REL_VADR);
				print_int("REPT_CNT", ftr->REPT_CNT);
				print_int("NUM_FAIL", ftr->NUM_FAIL);
				print_int("XFAIL_AD", ftr->XFAIL_AD);
				print_int("YFAIL_AD", ftr->YFAIL_AD);
				print_int("VECT_OFF", ftr->VECT_OFF);
				print_int("RTN_ICNT", ftr->RTN_ICNT);
				print_int("PGM_ICNT", ftr->PGM_ICNT);
				print_xU2("RTN_INDX", ftr->RTN_INDX, ftr->RTN_ICNT);
				print_xN1("RTN_STAT", ftr->RTN_STAT, ftr->RTN_ICNT);
				print_xU2("PGM_INDX", ftr->PGM_INDX, ftr->PGM_ICNT);
				print_xN1("PGM_STAT", ftr->PGM_STAT, ftr->PGM_ICNT);
				print_Dn("FAIL_PIN", ftr->FAIL_PIN);
				print_str("VECT_NAM", ftr->VECT_NAM);
				print_str("TIME_SET", ftr->TIME_SET);
				print_str("OP_CODE", ftr->OP_CODE);
				print_str("TEST_TXT", ftr->TEST_TXT);
				print_str("ALARM_ID", ftr->ALARM_ID);
				print_str("PROG_TXT", ftr->PROG_TXT);
				print_str("RSLT_TXT", ftr->RSLT_TXT);
				print_int("PATG_NUM", ftr->PATG_NUM);
				print_Dn("SPIN_MAP", ftr->SPIN_MAP);
				break;
			}
			case REC_BPS: {
				rec_bps *bps = (rec_bps*)rec;
				print_str("SEQ_NAME", bps->SEQ_NAME);
				break;
			}
			case REC_EPS: {
				/*rec_eps *eps = (rec_eps*)rec;*/
				break;
			}
#ifdef STDF_VER3
			case REC_SHB: {
				rec_shb *shb = (rec_shb*)rec;
				print_int("HEAD_NUM", shb->HEAD_NUM);
				print_int("SITE_NUM", shb->SITE_NUM);
				print_int("HBIN_NUM", shb->HBIN_NUM);
				print_int("HBIN_CNT", shb->HBIN_CNT);
				print_str("HBIN_NAM", shb->HBIN_NAM);
				break;
			}
			case REC_SSB: {
				rec_ssb *ssb = (rec_ssb*)rec;
				print_int("HEAD_NUM", ssb->HEAD_NUM);
				print_int("SITE_NUM", ssb->SITE_NUM);
				print_int("SBIN_NUM", ssb->SBIN_NUM);
				print_int("SBIN_CNT", ssb->SBIN_CNT);
				print_str("SBIN_NAM", ssb->SBIN_NAM);
				break;
			}
			case REC_STS: {
				rec_sts *sts = (rec_sts*)rec;
				print_int("HEAD_NUM", sts->HEAD_NUM);
				print_int("SITE_NUM", sts->SITE_NUM);
				print_int("TEST_NUM", sts->TEST_NUM);
				print_int("EXEC_CNT", sts->EXEC_CNT);
				print_int("FAIL_CNT", sts->FAIL_CNT);
				print_int("ALRM_CNT", sts->ALRM_CNT);
				print_hex("OPT_FLAG", sts->OPT_FLAG);
				print_hex("PAD_BYTE", sts->PAD_BYTE);
				print_rel("TEST_MIN", sts->TEST_MIN);
				print_rel("TEST_MAX", sts->TEST_MAX);
				print_rel("TST_MEAN", sts->TST_MEAN);
				print_rel("TST_SDEV", sts->TST_SDEV);
				print_rel("TST_SUMS", sts->TST_SUMS);
				print_rel("TST_SQRS", sts->TST_SQRS);
				print_str("TEST_NAM", sts->TEST_NAM);
				print_str("SEQ_NAME", sts->SEQ_NAME);
				print_str("TEST_LBL", sts->TEST_LBL);
				break;
			}
			case REC_SCR: {
				rec_scr *scr = (rec_scr*)rec;
				print_int("HEAD_NUM", scr->HEAD_NUM);
				print_int("SITE_NUM", scr->SITE_NUM);
				print_int("FINISH_T", scr->FINISH_T);
				print_int("PART_CNT", scr->PART_CNT);
				print_int("RTST_CNT", scr->RTST_CNT);
				print_int("ABRT_CNT", scr->ABRT_CNT);
				print_int("GOOD_CNT", scr->GOOD_CNT);
				print_int("FUNC_CNT", scr->FUNC_CNT);
				break;
			}
#endif
			case REC_GDR: {
				rec_gdr *gdr = (rec_gdr*)rec;
				print_int("FLD_CNT", gdr->FLD_CNT);
				print_Vn("GEN_DATA", gdr->GEN_DATA, gdr->FLD_CNT);
				break;
			}
			case REC_DTR: {
				rec_dtr *dtr = (rec_dtr*)rec;
				print_str("TEXT_DAT", dtr->TEXT_DAT);
				break;
			}
			case REC_UNKNOWN: {
				rec_unknown *unk = (rec_unknown*)rec;
				printf("\tBytes: %i\n", unk->header.REC_LEN);
				printf("\tTYP: 0x%X [%i]\n", unk->header.REC_TYP, unk->header.REC_TYP);
				printf("\tSUB: 0x%X [%i]\n", unk->header.REC_SUB, unk->header.REC_SUB);
			}
		}
		stdf_free_record(rec);
	}
	stdf_close(f);
}
	return EXIT_SUCCESS;
}
