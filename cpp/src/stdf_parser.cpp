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
    STDFRecord record;
    record.type = STDFRecordType::PTR;
    
    // SAFE APPROACH: Don't cast, just extract basic info from rec_unknown
    rec_unknown* rec = static_cast<rec_unknown*>(ptr_rec);
    
    // For now, just store header info to avoid casting issues
    record.rec_type = rec->header.REC_TYP;
    record.rec_subtype = rec->header.REC_SUB;
    
    // Store basic record info without unsafe casting
    record.fields["REC_TYPE"] = std::to_string(record.rec_type);
    record.fields["REC_SUB"] = std::to_string(record.rec_subtype);
    record.fields["RECORD_TYPE"] = "PTR";
    
    return record;
}

STDFRecord STDFParser::parse_mpr_record(void* mpr_rec) {
    STDFRecord record;
    record.type = STDFRecordType::MPR;
    
    // SAFE APPROACH: Don't cast, just extract basic info from rec_unknown
    rec_unknown* rec = static_cast<rec_unknown*>(mpr_rec);
    
    // For now, just store header info to avoid casting issues
    record.rec_type = rec->header.REC_TYP;
    record.rec_subtype = rec->header.REC_SUB;
    
    // Store basic record info without unsafe casting
    record.fields["REC_TYPE"] = std::to_string(record.rec_type);
    record.fields["REC_SUB"] = std::to_string(record.rec_subtype);
    record.fields["RECORD_TYPE"] = "MPR";
    
    return record;
}

STDFRecord STDFParser::parse_ftr_record(void* ftr_rec) {
    STDFRecord record;
    record.type = STDFRecordType::FTR;
    
    // SAFE APPROACH: Don't cast, just extract basic info from rec_unknown
    rec_unknown* rec = static_cast<rec_unknown*>(ftr_rec);
    
    // For now, just store header info to avoid casting issues
    record.rec_type = rec->header.REC_TYP;
    record.rec_subtype = rec->header.REC_SUB;
    
    // Store basic record info without unsafe casting
    record.fields["REC_TYPE"] = std::to_string(record.rec_type);
    record.fields["REC_SUB"] = std::to_string(record.rec_subtype);
    record.fields["RECORD_TYPE"] = "FTR";
    
    return record;
}

STDFRecord STDFParser::parse_hbr_record(void* hbr_rec) {
    STDFRecord record;
    record.type = STDFRecordType::HBR;
    
    // SAFE APPROACH: Don't cast, just extract basic info from rec_unknown
    rec_unknown* rec = static_cast<rec_unknown*>(hbr_rec);
    
    // For now, just store header info to avoid casting issues
    record.rec_type = rec->header.REC_TYP;
    record.rec_subtype = rec->header.REC_SUB;
    
    // Store basic record info without unsafe casting
    record.fields["REC_TYPE"] = std::to_string(record.rec_type);
    record.fields["REC_SUB"] = std::to_string(record.rec_subtype);
    record.fields["RECORD_TYPE"] = "HBR";
    
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
    
    // SAFE APPROACH: Don't cast, just extract basic info from rec_unknown
    rec_unknown* rec = static_cast<rec_unknown*>(prr_rec);
    
    // For now, just store header info to avoid casting issues
    record.rec_type = rec->header.REC_TYP;
    record.rec_subtype = rec->header.REC_SUB;
    
    // Store basic record info without unsafe casting
    record.fields["REC_TYPE"] = std::to_string(record.rec_type);
    record.fields["REC_SUB"] = std::to_string(record.rec_subtype);
    record.fields["RECORD_TYPE"] = "PRR";
    
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