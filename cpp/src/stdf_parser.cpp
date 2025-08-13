#include "../include/stdf_parser.h"
#include <iostream>
#include <fstream>
#include <cstring>
#include <algorithm>

// libstdf headers
#include <libstdf.h>

STDFParser::STDFParser() 
    : stdf_file_handle_(nullptr)
    , total_records_(0)
    , parsed_records_(0) {
    
    // Enable common record types by default
    enabled_types_ = {
        STDFRecordType::PTR,
        STDFRecordType::MPR,
        STDFRecordType::FTR,
        STDFRecordType::HBR,
        STDFRecordType::SBR,
        STDFRecordType::MIR,
        STDFRecordType::PRR
    };
}

STDFParser::~STDFParser() {
    close_stdf_file();
}

std::vector<STDFRecord> STDFParser::parse_file(const std::string& filepath) {
    std::vector<STDFRecord> results;
    
    std::cout << "Parsing STDF file with libstdf: " << filepath << std::endl;
    
    // Extract filename for record context
    size_t last_slash = filepath.find_last_of("/\\");
    current_filename_ = (last_slash != std::string::npos) ? 
                       filepath.substr(last_slash + 1) : filepath;
    
    total_records_ = 0;
    parsed_records_ = 0;
    
    // Open STDF file with libstdf
    stdf_file* file = stdf_open(const_cast<char*>(filepath.c_str()));
    if (!file) {
        std::cerr << "Failed to open STDF file with libstdf: " << filepath << std::endl;
        return results;
    }
    
    stdf_file_handle_ = file;
    
    // Read records using libstdf - safer approach
    rec_unknown* record;
    while ((record = stdf_read_record(file)) != nullptr) {
        total_records_++;
        
        try {
            // Get record type and subtype safely
            if (!record) {
                std::cerr << "Warning: NULL record encountered" << std::endl;
                continue;
            }
            
            uint8_t rec_typ = record->header.REC_TYP;
            uint8_t rec_sub = record->header.REC_SUB;
            
            STDFRecordType type = get_record_type(rec_typ, rec_sub);
            
            // Skip if this record type is not enabled
            if (std::find(enabled_types_.begin(), enabled_types_.end(), type) == enabled_types_.end()) {
                stdf_free_record(record);
                continue;
            }
            
            // Parse the record based on its type - with error handling
            STDFRecord parsed_record = parse_record(record, type);
            if (!parsed_record.fields.empty() || type == STDFRecordType::MIR) {
                parsed_record.filename = current_filename_;
                parsed_record.record_index = total_records_;
                results.push_back(parsed_record);
                parsed_records_++;
            }
            
        } catch (const std::exception& e) {
            std::cerr << "Error processing record " << total_records_ << ": " << e.what() << std::endl;
        }
        
        stdf_free_record(record);
    }
    
    close_stdf_file();
    
    std::cout << "libstdf parsing completed. Total records: " << total_records_ 
              << ", Parsed: " << parsed_records_ << std::endl;
    
    return results;
}

void STDFParser::create_sample_records(std::vector<STDFRecord>& results) {
    // Create sample PTR record for testing
    STDFRecord ptr_record;
    ptr_record.type = STDFRecordType::PTR;
    ptr_record.test_num = 1000512;
    ptr_record.head_num = 1;
    ptr_record.site_num = 1;
    ptr_record.result = 0.0486745648086071;
    ptr_record.alarm_id = "StaticPowerDiss:iddp_SLEEP;Mode=SLEEP;modSum;";
    ptr_record.test_txt = "TestPTR";
    ptr_record.filename = current_filename_;
    ptr_record.record_index = 1;
    
    // Add fields map
    ptr_record.fields["TEST_NUM"] = std::to_string(ptr_record.test_num);
    ptr_record.fields["HEAD_NUM"] = std::to_string(ptr_record.head_num);
    ptr_record.fields["SITE_NUM"] = std::to_string(ptr_record.site_num);
    ptr_record.fields["RESULT"] = std::to_string(ptr_record.result);
    ptr_record.fields["ALARM_ID"] = ptr_record.alarm_id;
    ptr_record.fields["TEST_TXT"] = ptr_record.test_txt;
    
    results.push_back(ptr_record);
    
    // Create sample MPR record
    STDFRecord mpr_record;
    mpr_record.type = STDFRecordType::MPR;
    mpr_record.test_num = 212;
    mpr_record.head_num = 1;
    mpr_record.site_num = 1;
    mpr_record.result = -0.23524582386016846;
    mpr_record.alarm_id = "PowerUp.ContinuityTest.DisconnectDPS.signalResult";
    mpr_record.filename = current_filename_;
    mpr_record.record_index = 2;
    
    mpr_record.fields["TEST_NUM"] = std::to_string(mpr_record.test_num);
    mpr_record.fields["HEAD_NUM"] = std::to_string(mpr_record.head_num);
    mpr_record.fields["SITE_NUM"] = std::to_string(mpr_record.site_num);
    mpr_record.fields["RESULT"] = std::to_string(mpr_record.result);
    mpr_record.fields["ALARM_ID"] = mpr_record.alarm_id;
    
    results.push_back(mpr_record);
    
    total_records_ = 2;
    parsed_records_ = 2;
}

STDFRecord STDFParser::parse_record(void* raw_record, STDFRecordType type) {
    STDFRecord record;
    record.type = type;
    
    rec_unknown* rec = static_cast<rec_unknown*>(raw_record);
    record.rec_type = rec->header.REC_TYP;
    record.rec_subtype = rec->header.REC_SUB;
    
    // Parse based on record type - ALL ENABLED: Safe parsing for all types
    switch (type) {
        case STDFRecordType::MIR:
            return parse_mir_record(raw_record);
        case STDFRecordType::PTR:
            return parse_ptr_record(raw_record);  // Enable PTR parser
        case STDFRecordType::MPR:
            return parse_mpr_record(raw_record);  // Enable MPR parser
        case STDFRecordType::FTR:
            return parse_ftr_record(raw_record);  // Enable FTR parser
        case STDFRecordType::HBR:
            return parse_hbr_record(raw_record);  // Enable HBR parser
        case STDFRecordType::SBR:
            return parse_sbr_record(raw_record);  // Enable SBR parser
        case STDFRecordType::PRR:
            return parse_prr_record(raw_record);  // Enable PRR parser
        default:
            // For unsupported record types, store basic info
            record.fields["REC_TYPE"] = std::to_string(record.rec_type);
            record.fields["REC_SUB"] = std::to_string(record.rec_subtype);
            break;
    }
    
    return record;
}

bool STDFParser::open_stdf_file(const std::string& filepath) {
    // Check if file exists
    std::ifstream file(filepath, std::ios::binary);
    if (!file.good()) {
        return false;
    }
    file.close();
    
    return true;
}

void STDFParser::close_stdf_file() {
    if (stdf_file_handle_) {
        stdf_close(static_cast<stdf_file*>(stdf_file_handle_));
        stdf_file_handle_ = nullptr;
    }
}

STDFRecordType STDFParser::get_record_type(uint8_t rec_typ, uint8_t rec_sub) {
    // STDF V4 record type mapping (corrected per libstdf specification)
    if (rec_typ == 15 && rec_sub == 10) return STDFRecordType::PTR;  // Parametric Test Record (REC_SUB_PTR = 10)
    if (rec_typ == 15 && rec_sub == 15) return STDFRecordType::MPR;  // Multiple-Result Parametric Record (REC_SUB_MPR = 15)
    if (rec_typ == 15 && rec_sub == 20) return STDFRecordType::FTR;  // Functional Test Record (REC_SUB_FTR = 20)
    if (rec_typ == 1 && rec_sub == 40)  return STDFRecordType::HBR;  // Hardware Bin Record
    if (rec_typ == 1 && rec_sub == 50)  return STDFRecordType::SBR;  // Software Bin Record
    if (rec_typ == 5 && rec_sub == 20)  return STDFRecordType::PRR;  // Part Result Record
    if (rec_typ == 1 && rec_sub == 10)  return STDFRecordType::MIR;  // Master Information Record
    
    return STDFRecordType::UNKNOWN;
}

std::string STDFParser::extract_string_field(const char* field, size_t max_len) {
    if (!field) return "";
    
    size_t len = strnlen(field, max_len);
    return std::string(field, len);
}

void STDFParser::set_enabled_record_types(const std::vector<STDFRecordType>& types) {
    enabled_types_ = types;
}

void STDFParser::set_field_config(const std::string& config_json) {
    // TODO: Parse JSON configuration for field extraction
    // This would determine which fields to extract for each record type
}

// Record-specific parsers using libstdf structures

STDFRecord STDFParser::parse_ptr_record(void* ptr_rec) {
    static int ptr_count = 0;
    ptr_count++;
    if (ptr_count <= 3) printf("PTR Parser called #%d\n", ptr_count);
    
    STDFRecord record;
    record.type = STDFRecordType::PTR;
    
    rec_unknown* rec = static_cast<rec_unknown*>(ptr_rec);
    
    if (ptr_count <= 3) printf("rec pointer: %p\n", rec);
    
    // Store header info safely
    record.rec_type = rec->header.REC_TYP;
    record.rec_subtype = rec->header.REC_SUB;
    record.fields["REC_TYPE"] = std::to_string(record.rec_type);
    record.fields["REC_SUB"] = std::to_string(record.rec_subtype);
    record.fields["RECORD_TYPE"] = "PTR";
    
    // PROPER LIBSTDF APPROACH: Direct casting (as shown in libstdf examples)
    // This is the official way according to dump_records_to_ascii.c
    try {
        // Check if it's actually a PTR record using libstdf macros
        if (HEAD_TO_REC(rec->header) == REC_PTR) {
            // Official libstdf approach: cast rec_unknown* to rec_ptr*
            rec_ptr* ptr = (rec_ptr*)rec;
            
            static int debug_count = 0;
            if (debug_count < 2) {
                printf("\n=== PTR Proper Extraction #%d ===\n", debug_count + 1);
                printf("Using official libstdf casting approach\n");
                debug_count++;
            }
            
            // Extract all PTR fields using proper libstdf structures
            record.fields["test_num"] = std::to_string(ptr->TEST_NUM);
            record.fields["head_num"] = std::to_string(ptr->HEAD_NUM);
            record.fields["site_num"] = std::to_string(ptr->SITE_NUM);
            record.fields["test_flg"] = std::to_string(ptr->TEST_FLG);  // ← TARGET FIELD!
            record.fields["parm_flg"] = std::to_string(ptr->PARM_FLG);
            record.fields["result"] = std::to_string(ptr->RESULT);
            
            // Store in record structure for compatibility
            record.test_num = ptr->TEST_NUM;
            record.head_num = ptr->HEAD_NUM;
            record.site_num = ptr->SITE_NUM;
            record.result = ptr->RESULT;
          
        }
    } catch (...) {
        // If casting fails, continue with basic approach
        printf("PTR casting failed, using basic approach\n");
    }
    
    if (false) {  // Disable old approach
        uint8_t* raw_data = static_cast<uint8_t*>(rec->data);
        
        static int debug_count = 0;
        if (debug_count < 2) {  // Only debug first 2 PTR records
            printf("\n=== PTR Debug #%d ===\n", debug_count + 1);
            printf("Length: %d bytes\n", rec->header.REC_LEN);
            printf("Data pointer: %p\n", rec->data);
            
            // HYPOTHESIS: Maybe rec->data doesn't point to the actual record data
            // Let's try a different approach based on libstdf documentation
            printf("Record state: %d\n", rec->header.state);
            printf("Investigating data structure...\n");
            
            // Maybe we need to cast the entire rec_unknown to rec_ptr?
            // But we know this is dangerous - let's just skip memory access for now
            printf("SKIPPING direct memory access for safety\n");
            
            // Try to interpret the bytes according to STDF PTR spec:
            // TEST_NUM (U4) - 4 bytes
            // HEAD_NUM (U1) - 1 byte  
            // SITE_NUM (U1) - 1 byte
            // TEST_FLG (B1) - 1 byte ← TARGET!
            // PARM_FLG (B1) - 1 byte
            // RESULT (R4) - 4 bytes
            
            if (rec->header.REC_LEN >= 8) {
                uint32_t test_num = *reinterpret_cast<uint32_t*>(raw_data + 0);
                uint8_t head_num = raw_data[4];
                uint8_t site_num = raw_data[5]; 
                uint8_t test_flg = raw_data[6];  // ← This is what we want!
                uint8_t parm_flg = raw_data[7];
                
                printf("Fields: TEST_NUM=%u HEAD=%d SITE=%d TEST_FLG=%d PARM_FLG=%d\n", 
                       test_num, head_num, site_num, test_flg, parm_flg);
                
                if (rec->header.REC_LEN >= 12) {
                    float result = *reinterpret_cast<float*>(raw_data + 8);
                    printf("RESULT=%.6f\n", result);
                }
            }
            debug_count++;
        }
        
        // If debugging looks correct, extract the fields for real
        if (rec->header.REC_LEN >= 8) {
            try {
                uint32_t test_num = *reinterpret_cast<uint32_t*>(raw_data + 0);
                uint8_t head_num = raw_data[4];
                uint8_t site_num = raw_data[5];
                uint8_t test_flg = raw_data[6];  // ← The field you want!
                uint8_t parm_flg = raw_data[7];
                
                // Store in fields map
                record.fields["test_num"] = std::to_string(test_num);
                record.fields["head_num"] = std::to_string(head_num); 
                record.fields["site_num"] = std::to_string(site_num);
                record.fields["test_flg"] = std::to_string(test_flg);
                record.fields["parm_flg"] = std::to_string(parm_flg);
                
                // Store in record structure
                record.test_num = test_num;
                record.head_num = head_num;
                record.site_num = site_num;
                
                if (rec->header.REC_LEN >= 12) {
                    float result = *reinterpret_cast<float*>(raw_data + 8);
                    record.fields["result"] = std::to_string(result);
                    record.result = result;
                }
                
            } catch (...) {
                // If parsing fails, just use basic info
            }
        }
    }
    
    return record;
}

STDFRecord STDFParser::parse_mpr_record(void* mpr_rec) {
    STDFRecord record;
    record.type = STDFRecordType::MPR;
    
    rec_unknown* rec = static_cast<rec_unknown*>(mpr_rec);
    
    // Store header info safely
    record.rec_type = rec->header.REC_TYP;
    record.rec_subtype = rec->header.REC_SUB;
    record.fields["REC_TYPE"] = std::to_string(record.rec_type);
    record.fields["REC_SUB"] = std::to_string(record.rec_subtype);
    record.fields["RECORD_TYPE"] = "MPR";
    
    // PROPER LIBSTDF APPROACH: Direct casting (as shown in libstdf examples)
    try {
        // Check if it's actually a MPR record using libstdf macros
        if (HEAD_TO_REC(rec->header) == REC_MPR) {
            // Official libstdf approach: cast rec_unknown* to rec_mpr*
            rec_mpr* mpr = (rec_mpr*)rec;
            
            // Extract all MPR fields using proper libstdf structures
            record.fields["test_num"] = std::to_string(mpr->TEST_NUM);
            record.fields["head_num"] = std::to_string(mpr->HEAD_NUM);
            record.fields["site_num"] = std::to_string(mpr->SITE_NUM);
            record.fields["test_flg"] = std::to_string(mpr->TEST_FLG);
            record.fields["parm_flg"] = std::to_string(mpr->PARM_FLG);
            record.fields["rtn_icnt"] = std::to_string(mpr->RTN_ICNT);
            record.fields["rslt_cnt"] = std::to_string(mpr->RSLT_CNT);
            
            // Store in record structure for compatibility
            record.test_num = mpr->TEST_NUM;
            record.head_num = mpr->HEAD_NUM;
            record.site_num = mpr->SITE_NUM;
            
            // Optional: Extract text fields
            if (mpr->TEST_TXT) {
                record.fields["test_txt"] = std::string(mpr->TEST_TXT + 1);  // Skip length byte
                record.test_txt = record.fields["test_txt"];
            }
            if (mpr->ALARM_ID) {
                record.fields["alarm_id"] = std::string(mpr->ALARM_ID + 1);  // Skip length byte
                record.alarm_id = record.fields["alarm_id"];
            }
            
            // Extract additional MPR-specific fields
            record.fields["opt_flag"] = std::to_string(mpr->OPT_FLAG);
            record.fields["res_scal"] = std::to_string(mpr->RES_SCAL);
            record.fields["llm_scal"] = std::to_string(mpr->LLM_SCAL);
            record.fields["hlm_scal"] = std::to_string(mpr->HLM_SCAL);
            record.fields["lo_limit"] = std::to_string(mpr->LO_LIMIT);
            record.fields["hi_limit"] = std::to_string(mpr->HI_LIMIT);
            record.fields["start_in"] = std::to_string(mpr->START_IN);
            record.fields["incr_in"] = std::to_string(mpr->INCR_IN);
            
            // Extract result arrays if present
            if (mpr->RTN_STAT && mpr->RSLT_CNT > 0) {
                // Note: RTN_STAT and RTN_RSLT are arrays - for now just store count
                record.fields["rtn_stat_count"] = std::to_string(mpr->RSLT_CNT);
            }
        }
    } catch (...) {
        // If casting fails, continue with basic approach
    }
    
    return record;
}

STDFRecord STDFParser::parse_ftr_record(void* ftr_rec) {
    STDFRecord record;
    record.type = STDFRecordType::FTR;
    
    rec_unknown* rec = static_cast<rec_unknown*>(ftr_rec);
    
    // Store header info safely
    record.rec_type = rec->header.REC_TYP;
    record.rec_subtype = rec->header.REC_SUB;
    record.fields["REC_TYPE"] = std::to_string(record.rec_type);
    record.fields["REC_SUB"] = std::to_string(record.rec_subtype);
    record.fields["RECORD_TYPE"] = "FTR";
    
    // PROPER LIBSTDF APPROACH: Direct casting (as shown in libstdf examples)
    try {
        // Check if it's actually a FTR record using libstdf macros
        if (HEAD_TO_REC(rec->header) == REC_FTR) {
            // Official libstdf approach: cast rec_unknown* to rec_ftr*
            rec_ftr* ftr = (rec_ftr*)rec;
            
            // Extract all FTR fields using proper libstdf structures
            record.fields["test_num"] = std::to_string(ftr->TEST_NUM);
            record.fields["head_num"] = std::to_string(ftr->HEAD_NUM);
            record.fields["site_num"] = std::to_string(ftr->SITE_NUM);
            record.fields["test_flg"] = std::to_string(ftr->TEST_FLG);
            record.fields["opt_flag"] = std::to_string(ftr->OPT_FLAG);
            record.fields["cycl_cnt"] = std::to_string(ftr->CYCL_CNT);
            record.fields["rel_vadr"] = std::to_string(ftr->REL_VADR);
            record.fields["rept_cnt"] = std::to_string(ftr->REPT_CNT);
            record.fields["num_fail"] = std::to_string(ftr->NUM_FAIL);
            record.fields["xfail_ad"] = std::to_string(ftr->XFAIL_AD);
            record.fields["yfail_ad"] = std::to_string(ftr->YFAIL_AD);
            
            // Store in record structure for compatibility
            record.test_num = ftr->TEST_NUM;
            record.head_num = ftr->HEAD_NUM;
            record.site_num = ftr->SITE_NUM;
            
            // Optional: Extract text fields
            if (ftr->VECT_NAM) {
                record.fields["vect_nam"] = std::string(ftr->VECT_NAM + 1);  // Skip length byte
            }
            if (ftr->TIME_SET) {
                record.fields["time_set"] = std::string(ftr->TIME_SET + 1);  // Skip length byte
            }
            if (ftr->OP_CODE) {
                record.fields["op_code"] = std::string(ftr->OP_CODE + 1);  // Skip length byte
            }
            if (ftr->TEST_TXT) {
                record.fields["test_txt"] = std::string(ftr->TEST_TXT + 1);  // Skip length byte
                record.test_txt = record.fields["test_txt"];
            }
            if (ftr->ALARM_ID) {
                record.fields["alarm_id"] = std::string(ftr->ALARM_ID + 1);  // Skip length byte
                record.alarm_id = record.fields["alarm_id"];
            }
            if (ftr->PROG_TXT) {
                record.fields["prog_txt"] = std::string(ftr->PROG_TXT + 1);  // Skip length byte
            }
            if (ftr->RSLT_TXT) {
                record.fields["rslt_txt"] = std::string(ftr->RSLT_TXT + 1);  // Skip length byte
            }
            
            record.fields["patg_num"] = std::to_string(ftr->PATG_NUM);
            
            // SPIN_MAP is a bit array - for now just indicate if present
            if (ftr->SPIN_MAP) {
                record.fields["spin_map"] = "present";
            }
        }
    } catch (...) {
        // If casting fails, continue with basic approach
    }
    
    return record;
}

STDFRecord STDFParser::parse_hbr_record(void* hbr_rec) {
    STDFRecord record;
    record.type = STDFRecordType::HBR;
    
    rec_unknown* rec = static_cast<rec_unknown*>(hbr_rec);
    
    // Store header info safely
    record.rec_type = rec->header.REC_TYP;
    record.rec_subtype = rec->header.REC_SUB;
    record.fields["REC_TYPE"] = std::to_string(record.rec_type);
    record.fields["REC_SUB"] = std::to_string(record.rec_subtype);
    record.fields["RECORD_TYPE"] = "HBR";
    
    // PROPER LIBSTDF APPROACH: Direct casting (as shown in libstdf examples)
    try {
        // Check if it's actually a HBR record using libstdf macros
        if (HEAD_TO_REC(rec->header) == REC_HBR) {
            // Official libstdf approach: cast rec_unknown* to rec_hbr*
            rec_hbr* hbr = (rec_hbr*)rec;
            
            // Extract all HBR fields using proper libstdf structures
            record.fields["head_num"] = std::to_string(hbr->HEAD_NUM);
            record.fields["site_num"] = std::to_string(hbr->SITE_NUM);
            record.fields["hbin_num"] = std::to_string(hbr->HBIN_NUM);
            record.fields["hbin_cnt"] = std::to_string(hbr->HBIN_CNT);
            record.fields["hbin_pf"] = std::string(1, hbr->HBIN_PF);  // Pass/Fail flag
            
            // Store in record structure for compatibility
            record.head_num = hbr->HEAD_NUM;
            record.site_num = hbr->SITE_NUM;
            
            // Optional: Extract text field
            if (hbr->HBIN_NAM) {
                record.fields["hbin_nam"] = std::string(hbr->HBIN_NAM + 1);  // Skip length byte
            }
        }
    } catch (...) {
        // If casting fails, continue with basic approach
    }
    
    return record;
}

STDFRecord STDFParser::parse_sbr_record(void* sbr_rec) {
    STDFRecord record;
    record.type = STDFRecordType::SBR;
    
    rec_unknown* rec = static_cast<rec_unknown*>(sbr_rec);
    
    // Store header info safely
    record.rec_type = rec->header.REC_TYP;
    record.rec_subtype = rec->header.REC_SUB;
    record.fields["REC_TYPE"] = std::to_string(record.rec_type);
    record.fields["REC_SUB"] = std::to_string(record.rec_subtype);
    record.fields["RECORD_TYPE"] = "SBR";
    
    // PROPER LIBSTDF APPROACH: Direct casting (as shown in libstdf examples)
    try {
        // Check if it's actually a SBR record using libstdf macros
        if (HEAD_TO_REC(rec->header) == REC_SBR) {
            // Official libstdf approach: cast rec_unknown* to rec_sbr*
            rec_sbr* sbr = (rec_sbr*)rec;
            
            // Extract all SBR fields using proper libstdf structures
            record.fields["head_num"] = std::to_string(sbr->HEAD_NUM);
            record.fields["site_num"] = std::to_string(sbr->SITE_NUM);
            record.fields["sbin_num"] = std::to_string(sbr->SBIN_NUM);
            record.fields["sbin_cnt"] = std::to_string(sbr->SBIN_CNT);
            record.fields["sbin_pf"] = std::string(1, sbr->SBIN_PF);  // Pass/Fail flag
            
            // Store in record structure for compatibility
            record.head_num = sbr->HEAD_NUM;
            record.site_num = sbr->SITE_NUM;
            
            // Optional: Extract text field
            if (sbr->SBIN_NAM) {
                record.fields["sbin_nam"] = std::string(sbr->SBIN_NAM + 1);  // Skip length byte
            }
        }
    } catch (...) {
        // If casting fails, continue with basic approach
    }
    
    return record;
}

STDFRecord STDFParser::parse_mir_record(void* mir_rec) {
    STDFRecord record;
    record.type = STDFRecordType::MIR;
    
    rec_mir* mir = static_cast<rec_mir*>(mir_rec);
    
    // Store MIR context for other records
    if (mir->LOT_ID) {
        mir_lot_id_ = std::string(mir->LOT_ID);
        record.fields["LOT_ID"] = mir_lot_id_;
    }
    if (mir->PART_TYP) {
        mir_part_typ_ = std::string(mir->PART_TYP);
        record.fields["PART_TYP"] = mir_part_typ_;
    }
    if (mir->JOB_NAM) {
        mir_job_nam_ = std::string(mir->JOB_NAM);
        record.fields["JOB_NAM"] = mir_job_nam_;
    }
    
    record.fields["SETUP_T"] = std::to_string(mir->SETUP_T);
    record.fields["START_T"] = std::to_string(mir->START_T);
    record.fields["STAT_NUM"] = std::to_string(mir->STAT_NUM);
    
    if (mir->MODE_COD) {
        record.fields["MODE_COD"] = std::string(1, mir->MODE_COD);
    }
    if (mir->RTST_COD) {
        record.fields["RTST_COD"] = std::string(1, mir->RTST_COD);
    }
    if (mir->PROT_COD) {
        record.fields["PROT_COD"] = std::string(1, mir->PROT_COD);
    }
    
    if (mir->NODE_NAM) {
        record.fields["NODE_NAM"] = std::string(mir->NODE_NAM);
    }
    if (mir->TSTR_TYP) {
        record.fields["TSTR_TYP"] = std::string(mir->TSTR_TYP);
    }
    if (mir->EXEC_TYP) {
        record.fields["EXEC_TYP"] = std::string(mir->EXEC_TYP);
    }
    if (mir->EXEC_VER) {
        record.fields["EXEC_VER"] = std::string(mir->EXEC_VER);
    }
    
    return record;
}

STDFRecord STDFParser::parse_prr_record(void* prr_rec) {
    STDFRecord record;
    record.type = STDFRecordType::PRR;
    
    rec_unknown* rec = static_cast<rec_unknown*>(prr_rec);
    
    // Store header info safely
    record.rec_type = rec->header.REC_TYP;
    record.rec_subtype = rec->header.REC_SUB;
    record.fields["REC_TYPE"] = std::to_string(record.rec_type);
    record.fields["REC_SUB"] = std::to_string(record.rec_subtype);
    record.fields["RECORD_TYPE"] = "PRR";
    
    // PROPER LIBSTDF APPROACH: Direct casting (as shown in libstdf examples)
    try {
        // Check if it's actually a PRR record using libstdf macros
        if (HEAD_TO_REC(rec->header) == REC_PRR) {
            // Official libstdf approach: cast rec_unknown* to rec_prr*
            rec_prr* prr = (rec_prr*)rec;
            
            // Extract all PRR fields using proper libstdf structures
            record.fields["head_num"] = std::to_string(prr->HEAD_NUM);
            record.fields["site_num"] = std::to_string(prr->SITE_NUM);
            record.fields["part_flg"] = std::to_string(prr->PART_FLG);
            record.fields["num_test"] = std::to_string(prr->NUM_TEST);
            record.fields["hard_bin"] = std::to_string(prr->HARD_BIN);
            record.fields["soft_bin"] = std::to_string(prr->SOFT_BIN);
            record.fields["x_coord"] = std::to_string(prr->X_COORD);
            record.fields["y_coord"] = std::to_string(prr->Y_COORD);
            record.fields["test_t"] = std::to_string(prr->TEST_T);
            
            // Store in record structure for compatibility
            record.head_num = prr->HEAD_NUM;
            record.site_num = prr->SITE_NUM;
            
            // Optional: Extract text fields
            if (prr->PART_ID) {
                record.fields["part_id"] = std::string(prr->PART_ID + 1);  // Skip length byte
            }
            if (prr->PART_TXT) {
                record.fields["part_txt"] = std::string(prr->PART_TXT + 1);  // Skip length byte
            }
            
            // Extract binary field
            if (prr->PART_FIX) {
                // PART_FIX is a binary field - for now just indicate if present
                record.fields["part_fix"] = "present";
            }
        }
    } catch (...) {
        // If casting fails, continue with basic approach
    }
    
    return record;
}

// Safer record parsing with null checks and error handling
STDFRecord STDFParser::parse_record_safe(void* raw_record, STDFRecordType type) {
    STDFRecord record;
    record.type = type;
    
    if (!raw_record) {
        std::cerr << "Warning: NULL record pointer" << std::endl;
        return record;
    }
    
    try {
        rec_unknown* rec = static_cast<rec_unknown*>(raw_record);
        record.rec_type = rec->header.REC_TYP;
        record.rec_subtype = rec->header.REC_SUB;
        
        // Only parse MIR record for now to avoid casting issues
        if (type == STDFRecordType::MIR) {
            return parse_mir_record(raw_record);
        } else {
            // For other records, just store basic header info
            record.fields["REC_TYPE"] = std::to_string(record.rec_type);
            record.fields["REC_SUB"] = std::to_string(record.rec_subtype);
        }
        
    } catch (const std::exception& e) {
        std::cerr << "Exception in parse_record_safe: " << e.what() << std::endl;
        record.fields["ERROR"] = e.what();
    }
    
    return record;
}