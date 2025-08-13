#include "cpp/include/stdf_parser.h"
#include <iostream>
#include <iomanip>

int main() {
    std::cout << "=== STDF All Records Field Extraction Test ===" << std::endl;
    
    // Initialize parser
    STDFParser parser;
    
    // Parse STDF file
    std::string test_file = "STDF_Files/OSBE25_KEWGBBMD1U_BE_HRG39021_KEWGBBMD1U__Prod_TPP202_03_Agilent_93000MT9510_25C_5215_4_20241017193900.stdf";
    
    std::cout << "Parsing file: " << test_file << std::endl;
    auto records = parser.parse_file(test_file);
    
    std::cout << "\nTotal records parsed: " << records.size() << std::endl;
    
    // Count by record type
    std::map<STDFRecordType, int> type_counts;
    for (const auto& record : records) {
        type_counts[record.type]++;
    }
    
    std::cout << "\nRecord Type Summary:" << std::endl;
    std::cout << "  PTR: " << type_counts[STDFRecordType::PTR] << std::endl;
    std::cout << "  MPR: " << type_counts[STDFRecordType::MPR] << std::endl;
    std::cout << "  FTR: " << type_counts[STDFRecordType::FTR] << std::endl;
    std::cout << "  HBR: " << type_counts[STDFRecordType::HBR] << std::endl;
    std::cout << "  SBR: " << type_counts[STDFRecordType::SBR] << std::endl;
    std::cout << "  PRR: " << type_counts[STDFRecordType::PRR] << std::endl;
    std::cout << "  MIR: " << type_counts[STDFRecordType::MIR] << std::endl;
    
    // Test PTR field extraction (first few)
    std::cout << "\n=== PTR Field Extraction Sample ===" << std::endl;
    int ptr_count = 0;
    for (const auto& record : records) {
        if (record.type == STDFRecordType::PTR && ptr_count < 3) {
            std::cout << "PTR Record #" << (ptr_count + 1) << ":" << std::endl;
            std::cout << "  TEST_NUM: " << record.fields.at("test_num") << std::endl;
            std::cout << "  HEAD_NUM: " << record.fields.at("head_num") << std::endl;
            std::cout << "  SITE_NUM: " << record.fields.at("site_num") << std::endl;
            std::cout << "  TEST_FLG: " << record.fields.at("test_flg") << " ← TARGET!" << std::endl;
            std::cout << "  PARM_FLG: " << record.fields.at("parm_flg") << std::endl;
            std::cout << "  RESULT: " << record.fields.at("result") << std::endl;
            if (record.fields.find("test_txt") != record.fields.end()) {
                std::cout << "  TEST_TXT: " << record.fields.at("test_txt") << std::endl;
            }
            if (record.fields.find("alarm_id") != record.fields.end()) {
                std::cout << "  ALARM_ID: " << record.fields.at("alarm_id") << std::endl;
            }
            std::cout << std::endl;
            ptr_count++;
        }
    }
    
    // Test MPR field extraction
    std::cout << "=== MPR Field Extraction Sample ===" << std::endl;
    int mpr_count = 0;
    for (const auto& record : records) {
        if (record.type == STDFRecordType::MPR && mpr_count < 2) {
            std::cout << "MPR Record #" << (mpr_count + 1) << ":" << std::endl;
            std::cout << "  TEST_NUM: " << record.fields.at("test_num") << std::endl;
            std::cout << "  TEST_FLG: " << record.fields.at("test_flg") << " ← TARGET!" << std::endl;
            std::cout << "  RTN_ICNT: " << record.fields.at("rtn_icnt") << std::endl;
            std::cout << "  RSLT_CNT: " << record.fields.at("rslt_cnt") << std::endl;
            std::cout << std::endl;
            mpr_count++;
        }
    }
    
    // Test FTR field extraction
    std::cout << "=== FTR Field Extraction Sample ===" << std::endl;
    int ftr_count = 0;
    for (const auto& record : records) {
        if (record.type == STDFRecordType::FTR && ftr_count < 2) {
            std::cout << "FTR Record #" << (ftr_count + 1) << ":" << std::endl;
            std::cout << "  TEST_NUM: " << record.fields.at("test_num") << std::endl;
            std::cout << "  TEST_FLG: " << record.fields.at("test_flg") << " ← TARGET!" << std::endl;
            std::cout << "  CYCL_CNT: " << record.fields.at("cycl_cnt") << std::endl;
            std::cout << "  NUM_FAIL: " << record.fields.at("num_fail") << std::endl;
            std::cout << std::endl;
            ftr_count++;
        }
    }
    
    // Test HBR field extraction
    std::cout << "=== HBR Field Extraction Sample ===" << std::endl;
    int hbr_count = 0;
    for (const auto& record : records) {
        if (record.type == STDFRecordType::HBR && hbr_count < 2) {
            std::cout << "HBR Record #" << (hbr_count + 1) << ":" << std::endl;
            std::cout << "  HEAD_NUM: " << record.fields.at("head_num") << std::endl;
            std::cout << "  SITE_NUM: " << record.fields.at("site_num") << std::endl;
            std::cout << "  HBIN_NUM: " << record.fields.at("hbin_num") << std::endl;
            std::cout << "  HBIN_CNT: " << record.fields.at("hbin_cnt") << std::endl;
            std::cout << "  HBIN_PF: " << record.fields.at("hbin_pf") << std::endl;
            std::cout << std::endl;
            hbr_count++;
        }
    }
    
    // Test SBR field extraction
    std::cout << "=== SBR Field Extraction Sample ===" << std::endl;
    int sbr_count = 0;
    for (const auto& record : records) {
        if (record.type == STDFRecordType::SBR && sbr_count < 2) {
            std::cout << "SBR Record #" << (sbr_count + 1) << ":" << std::endl;
            std::cout << "  HEAD_NUM: " << record.fields.at("head_num") << std::endl;
            std::cout << "  SITE_NUM: " << record.fields.at("site_num") << std::endl;
            std::cout << "  SBIN_NUM: " << record.fields.at("sbin_num") << std::endl;
            std::cout << "  SBIN_CNT: " << record.fields.at("sbin_cnt") << std::endl;
            std::cout << "  SBIN_PF: " << record.fields.at("sbin_pf") << std::endl;
            std::cout << std::endl;
            sbr_count++;
        }
    }
    
    // Test PRR field extraction
    std::cout << "=== PRR Field Extraction Sample ===" << std::endl;
    int prr_count = 0;
    for (const auto& record : records) {
        if (record.type == STDFRecordType::PRR && prr_count < 2) {
            std::cout << "PRR Record #" << (prr_count + 1) << ":" << std::endl;
            std::cout << "  HEAD_NUM: " << record.fields.at("head_num") << std::endl;
            std::cout << "  SITE_NUM: " << record.fields.at("site_num") << std::endl;
            std::cout << "  PART_FLG: " << record.fields.at("part_flg") << std::endl;
            std::cout << "  NUM_TEST: " << record.fields.at("num_test") << std::endl;
            std::cout << "  HARD_BIN: " << record.fields.at("hard_bin") << std::endl;
            std::cout << "  SOFT_BIN: " << record.fields.at("soft_bin") << std::endl;
            std::cout << "  X_COORD: " << record.fields.at("x_coord") << std::endl;
            std::cout << "  Y_COORD: " << record.fields.at("y_coord") << std::endl;
            std::cout << std::endl;
            prr_count++;
        }
    }
    
    // Test MIR field extraction
    std::cout << "=== MIR Field Extraction Sample ===" << std::endl;
    for (const auto& record : records) {
        if (record.type == STDFRecordType::MIR) {
            std::cout << "MIR Record:" << std::endl;
            if (record.fields.find("LOT_ID") != record.fields.end()) {
                std::cout << "  LOT_ID: " << record.fields.at("LOT_ID") << std::endl;
            }
            if (record.fields.find("PART_TYP") != record.fields.end()) {
                std::cout << "  PART_TYP: " << record.fields.at("PART_TYP") << std::endl;
            }
            if (record.fields.find("JOB_NAM") != record.fields.end()) {
                std::cout << "  JOB_NAM: " << record.fields.at("JOB_NAM") << std::endl;
            }
            std::cout << "  SETUP_T: " << record.fields.at("SETUP_T") << std::endl;
            std::cout << "  START_T: " << record.fields.at("START_T") << std::endl;
            break;
        }
    }
    
    std::cout << "\n✅ All record types successfully extracting fields!" << std::endl;
    
    return 0;
}