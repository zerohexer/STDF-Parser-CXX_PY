#include "../include/stdf_parser.h"
#include "../include/dynamic_field_extractor.h"
#include <iostream>
#include <fstream>
#include <cstring>
#include <algorithm>

// libstdf headers
#include <libstdf.h>

// Global shared DynamicFieldExtractor (created once, reused everywhere)
static DynamicFieldExtractor g_field_extractor;

STDFParser::STDFParser()
    : stdf_file_handle_(nullptr)
    , total_records_(0)
    , parsed_records_(0) {

    // Enable common record types by default - auto-generated from registry
    enabled_types_ = {
        #define RECORD_TYPE(name, ...) STDFRecordType::name,
        #include "../field_defs/record_types.def"
        #undef RECORD_TYPE
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
    // Note: STDF fields now handled by .def files
    // Only set internal/non-STDF fields:
    ptr_record.alarm_id = "StaticPowerDiss:iddp_SLEEP;Mode=SLEEP;modSum;";
    ptr_record.test_txt = "TestPTR";
    ptr_record.filename = current_filename_;
    ptr_record.record_index = 1;
    ptr_record.fields["ALARM_ID"] = ptr_record.alarm_id;
    ptr_record.fields["TEST_TXT"] = ptr_record.test_txt;
    
    results.push_back(ptr_record);
    
    // Create sample MPR record
    STDFRecord mpr_record;
    mpr_record.type = STDFRecordType::MPR;
    // Note: STDF fields now handled by .def files
    // Only set internal/non-STDF fields:
    mpr_record.alarm_id = "PowerUp.ContinuityTest.DisconnectDPS.signalResult";
    mpr_record.filename = current_filename_;
    mpr_record.record_index = 2;
    mpr_record.fields["ALARM_ID"] = mpr_record.alarm_id;
    
    results.push_back(mpr_record);
    
    total_records_ = 2;
    parsed_records_ = 2;
}

// ============================================================================
// HYBRID APPROACH: Generic Template Parser
// ============================================================================
// ONE template handles ALL record types - no duplication!
template<typename RecordStruct, int LibstdfMacro>
STDFRecord STDFParser::parse_generic_record(void* raw_record, STDFRecordType type, const char* type_name) {
    STDFRecord record;
    record.type = type;

    rec_unknown* rec = static_cast<rec_unknown*>(raw_record);

    // Store header info
    record.rec_type = rec->header.REC_TYP;
    record.rec_subtype = rec->header.REC_SUB;
    record.fields["REC_TYPE"] = std::to_string(record.rec_type);
    record.fields["REC_SUB"] = std::to_string(record.rec_subtype);
    record.fields["RECORD_TYPE"] = type_name;

    try {
        // Check if it's actually the expected record type using libstdf macros
        if (HEAD_TO_REC(rec->header) == LibstdfMacro) {
            // Cast to specific type
            RecordStruct* typed_rec = (RecordStruct*)rec;

            // Extract ALL fields using global shared extractor
            DynamicSTDFRecord dynamic_record;
            g_field_extractor.extract_fields(typed_rec, dynamic_record);

            // Copy ALL extracted fields from X-Macros to main record
            for (const auto& field : dynamic_record.fields) {
                record.fields[field.first] = field.second;
            }

            static int debug_count = 0;
            if (debug_count < 2 && type == STDFRecordType::PTR) {
                std::cout << type_name << " generic parser: Extracted "
                          << dynamic_record.fields.size() << " fields" << std::endl;
                debug_count++;
            }
        } else {
            std::cerr << "Warning: Record header mismatch in parse_generic_record for "
                      << type_name << std::endl;
        }

    } catch (const std::exception& e) {
        std::cerr << "Exception in parse_generic_record (" << type_name << "): "
                  << e.what() << std::endl;
        record.fields["ERROR"] = e.what();
    }

    return record;
}

// ============================================================================
// Auto-generated Switch - Uses X-Macros but keeps template calls explicit
// ============================================================================
STDFRecord STDFParser::parse_record(void* raw_record, STDFRecordType type) {
    STDFRecord record;
    record.type = type;

    rec_unknown* rec = static_cast<rec_unknown*>(raw_record);
    record.rec_type = rec->header.REC_TYP;
    record.rec_subtype = rec->header.REC_SUB;

    // X-Macro generates switch cases from record_types.def
    switch (type) {
        #define RECORD_TYPE(name, struct_type, typ, sub, macro) \
            case STDFRecordType::name: \
                return parse_generic_record<struct_type, macro>(raw_record, type, #name);

        #include "../field_defs/record_types.def"
        #undef RECORD_TYPE

        default:
            // Unknown record type
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

// ============================================================================
// Auto-generated Record Type Detection - from field_defs/record_types.def
// ============================================================================
STDFRecordType STDFParser::get_record_type(uint8_t rec_typ, uint8_t rec_sub) {
    // X-Macro generates if-else chain from record_types.def
    #define RECORD_TYPE(name, struct_type, typ, sub, macro) \
        if (rec_typ == typ && rec_sub == sub) return STDFRecordType::name;

    #include "../field_defs/record_types.def"
    #undef RECORD_TYPE

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

