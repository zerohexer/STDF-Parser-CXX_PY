/**
 * @file makestdf.c
 */
/*
 * Copyright (C) 2004-2006 Mike Frysinger <vapier@gmail.com>
 * Released under the BSD license.  For more information,
 * please see: http://opensource.org/licenses/bsd-license.php
 *
 * $Header: /cvsroot/freestdf/libstdf/examples/makestdf.c,v 1.7 2005/12/10 05:46:55 vapier Exp $
 */

#include <libstdf.h>

int main(int argc, char *argv[])
{
	stdf_file *f;

	if (argc != 2) {
		printf("Usage: %s <stdf file>\n", argv[0]);
		return EXIT_FAILURE;
	}

	f = stdf_open_ex(argv[1], STDF_OPTS_WRITE | STDF_OPTS_CREATE, 0644);
	if (!f) {
		perror("Could not open output");
		return EXIT_FAILURE;
	}

	{
		rec_far far = {
			.CPU_TYPE = CPU_TYPE_X86,
			.STDF_VER = 4
		};
		stdf_init_header(far.header, REC_FAR);
		stdf_write_record(f, &far);
	}

	{
		rec_atr atr = {
			.MOD_TIM = 3,
			.CMD_LINE = "\010CMD_LINE"
		};
		stdf_init_header(atr.header, REC_ATR);
		stdf_write_record(f, &atr);
	}

	{
		rec_mir mir = {
			.SETUP_T = 0,
			.START_T = 1,
			.STAT_NUM = 2,
			.MODE_COD = 'D',
			.RTST_COD = ' ',
			.PROT_COD = ' ',
			.BURN_TIM = 9,
			.CMOD_COD = ' ',
			.LOT_ID   = "\006LOT_ID",
			.PART_TYP = "\010PART_TYP",
			.NODE_NAM = "\010NODE_NAM",
			.TSTR_TYP = "\010TSTR_TYP",
			.JOB_NAM  = "\007JOB_NAM",
			.JOB_REV  = "\007JOB_REV",
			.SBLOT_ID = "\010SBLOT_ID",
			.OPER_NAM = "\010OPER_NAM",
			.EXEC_TYP = "\010EXEC_TYP",
			.EXEC_VER = "\010EXEC_VER",
			.TEST_COD = "\010TEST_COD",
			.TST_TEMP = "\010TST_TEMP",
			.USER_TXT = "\010USER_TXT",
			.AUX_FILE = "\010AUX_FILE",
			.PKG_TYP  = "\007PKG_TYP",
			.FAMILY_ID = "\011FAMILY_ID",
			.DATE_COD = "\010DATE_COD",
			.FACIL_ID = "\010FACIL_ID",
			.FLOOR_ID = "\010FLOOR_ID",
			.PROC_ID  = "\007PROC_ID",
			.OPER_FRQ = "\010OPER_FRQ",
			.SPEC_NAM = "\010SPEC_NAM",
			.SPEC_VER = "\010SPEC_VER",
			.FLOW_ID  = "\007FLOW_ID",
			.SETUP_ID = "\010SETUP_ID",
			.DSGN_REV = "\010DSGN_REV",
			.ENG_ID   = "\006ENG_ID",
			.ROM_COD  = "\007ROM_COD",
			.SERL_NUM = "\010SERL_NUM",
			.SUPR_NAM = "\010SUPR_NAM"
		};
		stdf_init_header(mir.header, REC_MIR);
		stdf_write_record(f, &mir);
	}

	{
		rec_mrr mrr = {
			.FINISH_T = 4,
			.DISP_COD = ' ',
			.USR_DESC = "\010USR_DESC",
			.EXC_DESC = "\010EXC_DESC"
		};
		stdf_init_header(mrr.header, REC_MRR);
		stdf_write_record(f, &mrr);
	}

	{
		dtc_U2 rtst_bin[10] = { 2, 4, 6, 8, 10, 12, 14, 16, 18, 20 };
		rec_rdr rdr = {
			.NUM_BINS = 10,
			.RTST_BIN = rtst_bin
		};
		stdf_init_header(rdr.header, REC_RDR);
		stdf_write_record(f, &rdr);
	}

	{
		rec_pcr pcr = {
			.HEAD_NUM = 1,
			.SITE_NUM = 2,
			.PART_CNT = 5,
			.RTST_CNT = 6,
			.ABRT_CNT = 7,
			.GOOD_CNT = 8,
			.FUNC_CNT = 9
		};
		stdf_init_header(pcr.header, REC_PCR);
		stdf_write_record(f, &pcr);
	}

	{
		rec_hbr hbr = {
			.HEAD_NUM = 1,
			.SITE_NUM = 2,
			.HBIN_NUM = 6,
			.HBIN_CNT = 8,
			.HBIN_PF = 'F',
			.HBIN_NAM = "\010HBIN_NAM"
		};
		stdf_init_header(hbr.header, REC_HBR);
		stdf_write_record(f, &hbr);
	}

	{
		rec_sbr sbr = {
			.HEAD_NUM = 1,
			.SITE_NUM = 2,
			.SBIN_NUM = 0,
			.SBIN_CNT = 6,
			.SBIN_PF = 'P',
			.SBIN_NAM = "\010SBIN_NAM"
		};
		stdf_init_header(sbr.header, REC_SBR);
		stdf_write_record(f, &sbr);
	}

	{
		rec_pmr pmr = {
			.PMR_INDX = 3,
			.CHAN_TYP = 78,
			.CHAN_NAM = "\010CHAN_NAM",
			.PHY_NAM = "\007PHY_NAM",
			.LOG_NAM = "\007LOG_NAM",
			.HEAD_NUM = 68,
			.SITE_NUM = 4
		};
		stdf_init_header(pmr.header, REC_PMR);
		stdf_write_record(f, &pmr);
	}

	{
		dtc_U2 pmr_indx[3] = { 10, 20, 30};
		rec_pgr pgr = {
			.GRP_INDX = 45678,
			.GRP_NAM = "\007GRP_NAM",
			.INDX_CNT = 3,
			.PMR_INDX = pmr_indx
		};
		stdf_init_header(pgr.header, REC_PGR);
		stdf_write_record(f, &pgr);
	}

	{
		dtc_U2 grp_indx[6] = { 2, 4, 6, 8, 10, 12 };
		dtc_U2 grp_mode[6] = { 00, 10, 20, 21, 22, 23 };
		dtc_U1 grp_radx[6] = { 0, 2, 8, 10, 16, 20 };
		dtc_Cn pgm_char[6] = { "\001A", "\001B", "\001C", "\001D", "\001E", "\001F" };
		dtc_Cn rtn_char[6] = { "\001G", "\001H", "\001I", "\001J", "\001K", "\001L" };
		dtc_Cn pgm_chal[6] = { "\001M", "\001N", "\001O", "\001P", "\001Q", "\001R" };
		dtc_Cn rtn_chal[6] = { "\001S", "\001T", "\001U", "\001V", "\001W", "\001X" };
		rec_plr plr = {
			.GRP_CNT = 6,
			.GRP_INDX = grp_indx,
			.GRP_MODE = grp_mode,
			.GRP_RADX = grp_radx,
			.PGM_CHAR = pgm_char,
			.RTN_CHAR = rtn_char,
			.PGM_CHAL = pgm_chal,
			.RTN_CHAL = rtn_chal
		};
		stdf_init_header(plr.header, REC_PLR);
		stdf_write_record(f, &plr);
	}

	{
		dtc_U1 site_num[4] = { 5, 10, 15, 20 };
		rec_sdr sdr = {
			.HEAD_NUM = 2,
			.SITE_GRP = 3,
			.SITE_CNT = 4,
			.SITE_NUM = site_num,
			.HAND_TYP = "\010HAND_TYP",
			.HAND_ID  = "\007HAND_ID",
			.CARD_TYP = "\010CARD_TYP",
			.CARD_ID  = "\007CARD_ID",
			.LOAD_TYP = "\010LOAD_TYP",
			.LOAD_ID  = "\007LOAD_ID",
			.DIB_TYP  = "\007DIB_TYP",
			.DIB_ID   = "\006DIB_ID",
			.CABL_TYP = "\010CABL_TYP",
			.CABL_ID  = "\007CABL_ID",
			.CONT_TYP = "\010CONT_TYP",
			.CONT_ID  = "\007CONT_ID",
			.LASR_TYP = "\010LASR_TYP",
			.LASR_ID  = "\007LASR_ID",
			.EXTR_TYP = "\010EXTR_TYP",
			.EXTR_ID  = "\007EXTR_ID"
		};
		stdf_init_header(sdr.header, REC_SDR);
		stdf_write_record(f, &sdr);
	}

	{
		rec_wir wir = {
			.HEAD_NUM = 2,
			.SITE_GRP = 3,
			.START_T = 4,
			.WAFER_ID = "\010WAFER_ID"
		};
		stdf_init_header(wir.header, REC_WIR);
		stdf_write_record(f, &wir);
	}

	{
		rec_wrr wrr = {
			.HEAD_NUM = 20,
			.SITE_GRP = 10,
			.FINISH_T = 5,
			.PART_CNT = 1000,
			.RTST_CNT = 2000,
			.ABRT_CNT = 3000,
			.GOOD_CNT = 4000,
			.FUNC_CNT = 5000,
			.WAFER_ID = "\010WAFER_ID",
			.FABWF_ID = "\010FABWF_ID",
			.FRAME_ID = "\010FRAME_ID",
			.MASK_ID  = "\007MASK_ID",
			.USR_DESC = "\010USR_DESC",
			.EXC_DESC = "\010EXC_DESC"
		};
		stdf_init_header(wrr.header, REC_WRR);
		stdf_write_record(f, &wrr);
	}

	{
		rec_wcr wcr = {
			.WAFR_SIZ = 4.1,
			.DIE_HT = 2500.2,
			.DIE_WID = 5200.3,
			.WF_UNITS = 2,
			.WF_FLAT = 'D',
			.CENTER_X = 50,
			.CENTER_Y = 70,
			.POS_X = 'L',
			.POS_Y = 'U'
		};
		stdf_init_header(wcr.header, REC_WCR);
		stdf_write_record(f, &wcr);
	}

	{
		rec_pir pir = {
			.HEAD_NUM = 30,
			.SITE_NUM = 60
		};
		stdf_init_header(pir.header, REC_PIR);
		stdf_write_record(f, &pir);
	}

/*
	{
		rec_prr prr = {
		};
		stdf_init_header(prr.header, REC_PRR);
		stdf_write_record(f, &prr);
	}
*/

	{
		rec_tsr tsr = {
			.HEAD_NUM = 13,
			.SITE_NUM = 23,
			.TEST_TYP = 'P',
			.TEST_NUM = 33,
			.EXEC_CNT = 101010,
			.FAIL_CNT = 202020,
			.ALRM_CNT = 303030,
			.TEST_NAM = "\010TEST_NAM",
			.SEQ_NAME = "\010SEQ_NAME",
			.TEST_LBL = "\010TEST_LBL",
			.OPT_FLAG = 0x4 | 0x6 | 0x7,
			.TEST_TIM = 1.0,
			.TEST_MIN = 1.5,
			.TEST_MAX = 33.33,
			.TST_SUMS = 66.66,
			.TST_SQRS = 8.125
		};
		stdf_init_header(tsr.header, REC_TSR);
		stdf_write_record(f, &tsr);
	}

/*
	{
		rec_ptr ptr = {
		};
		stdf_init_header(ptr.header, REC_PTR);
		stdf_write_record(f, &ptr);
	}
*/

	{
		dtc_N1 rtn_stat[] = { 0xAB, 0xCD, 0xEF, 0x12, 0x34, 0x56, 0x78, 0x90 };
		dtc_R4 rtn_rslt[] = { 1.2, 2.3, 3.4, 4.5, 5.6, 6.7, 7.8, 8.9 };
		dtc_U2 rtn_indx[] = { 1, 3, 5, 7, 9, 11, 13, 15, 17, 19, 21, 23, 25, 27, 29, 31, 33 };
		rec_mpr mpr = {
			.TEST_NUM = 2024,
			.HEAD_NUM = 1,
			.SITE_NUM = 2,
			.TEST_FLG = 0,
			.PARM_FLG = 0xC0,
			.RTN_ICNT = 15,
			.RSLT_CNT = 6,
			.RTN_STAT = rtn_stat,
			.RTN_RSLT = rtn_rslt,
			.TEST_TXT = "\010TEST_TXT",
			.OPT_FLAG = 0xE,
			.RES_SCAL = 6,
			.LLM_SCAL = 7,
			.HLM_SCAL = 8,
			.LO_LIMIT = 1.9,
			.HI_LIMIT = 9.1,
			.START_IN = 0.2,
			.INCR_IN  = 0.3,
			.RTN_INDX = rtn_indx,
			.UNITS    = "\005UNITS",
			.UNITS_IN = "\010UNITS_IN",
			.C_RESFMT = "\005%1.2f",
			.C_LLMFMT = "\005%3.4f",
			.C_HLMFMT = "\005%5.6f",
			.LO_SPEC  = 0.9,
			.HI_SPEC  = 9.0
		};
		stdf_init_header(mpr.header, REC_MPR);
		stdf_write_record(f, &mpr);
	}

	{
		dtc_U2 rtn_indx[] = { 1010, 2020, 3030, 4040, 5050, 6060, 7070, 8080 };
		dtc_N1 rtn_stat[] = { 0x13, 0x24, 0x57, 0x68 };
		dtc_U2 pgm_indx[] = { 101, 202, 303, 404, 505 };
		dtc_N1 pgm_stat[] = { 0x42, 0x75, 0x86 };
		char   fail_pin[] = { 0x00, 0x00 };
		char   spin_map[] = { 0x00, 0x00 };
		rec_ftr ftr = {
			.TEST_NUM = 2024,
			.HEAD_NUM = 1,
			.SITE_NUM = 2,
			.TEST_FLG = 0x14,
			.OPT_FLAG = 0x00,
			.CYCL_CNT = 1234,
			.REL_VADR = 5678,
			.REPT_CNT = 9012,
			.NUM_FAIL = 3456,
			.XFAIL_AD = 7890,
			.YFAIL_AD = 5432,
			.VECT_OFF = 10,
			.RTN_ICNT = 6,
			.PGM_ICNT = 3,
			.RTN_INDX = rtn_indx,
			.RTN_STAT = rtn_stat,
			.PGM_INDX = pgm_indx,
			.PGM_STAT = pgm_stat,
			.FAIL_PIN = fail_pin,
			.VECT_NAM = "\010VECT_NAM",
			.TIME_SET = "\010TIME_SET",
			.OP_CODE  = "\007OP_CODE",
			.TEST_TXT = "\010TEST_TXT",
			.ALARM_ID = "\010ALARM_ID",
			.PROG_TXT = "\010PROG_TXT",
			.RSLT_TXT = "\010RSLT_TXT",
			.PATG_NUM = 254,
			.SPIN_MAP = spin_map
		};
		stdf_init_header(ftr.header, REC_FTR);
		stdf_write_record(f, &ftr);
	}

	{
		rec_bps bps = {
			.SEQ_NAME = "\010SEQ_NAME"
		};
		stdf_init_header(bps.header, REC_BPS);
		stdf_write_record(f, &bps);
	}

	{
		rec_eps eps;
		stdf_init_header(eps.header, REC_EPS);
		stdf_write_record(f, &eps);
	}

/*
	{
		rec_gdr gdr = {
		};
		stdf_init_header(gdr.header, REC_GDR);
		stdf_write_record(f, &gdr);
	}
*/

	{
		rec_dtr dtr = {
			.TEXT_DAT = "\010TEXT_DAT"
		};
		stdf_init_header(dtr.header, REC_DTR);
		stdf_write_record(f, &dtr);
	}

	stdf_close(f);

	return EXIT_SUCCESS;
}
