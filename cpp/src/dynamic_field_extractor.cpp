#include "../include/dynamic_field_extractor.h"
#include <libstdf.h>
#include <iostream>
#include <sstream>

DynamicFieldExtractor::DynamicFieldExtractor(const std::string& config_file) 
    : config_file_path_(config_file) {
    
    // Load configuration or use defaults
    if (!load_configuration(config_file)) {
        std::cout << "WARNING: Failed to load config, using defaults" << std::endl;
        
        // Default configuration - enable common fields
        enabled_fields_["PTR"] = {"TEST_NUM", "HEAD_NUM", "SITE_NUM", "TEST_FLG", "PARM_FLG", "RESULT"};
        enabled_fields_["MPR"] = {"TEST_NUM", "HEAD_NUM", "SITE_NUM", "TEST_FLG", "RTN_ICNT", "RSLT_CNT"};
        enabled_fields_["FTR"] = {"TEST_NUM", "HEAD_NUM", "SITE_NUM", "TEST_FLG", "CYCL_CNT", "NUM_FAIL"};
        enabled_fields_["HBR"] = {"HEAD_NUM", "SITE_NUM", "HBIN_NUM", "HBIN_CNT", "HBIN_PF"};
        enabled_fields_["SBR"] = {"HEAD_NUM", "SITE_NUM", "SBIN_NUM", "SBIN_CNT", "SBIN_PF"};
        enabled_fields_["PRR"] = {"HEAD_NUM", "SITE_NUM", "PART_FLG", "NUM_TEST", "HARD_BIN", "SOFT_BIN"};
    }
    
    // Validate configuration
    if (!validate_configuration()) {
        std::cout << "WARNING: Configuration validation failed" << std::endl;
    }
    
    print_configuration_summary();
}

bool DynamicFieldExtractor::load_configuration(const std::string& config_file) {
    try {
        std::ifstream file(config_file);
        if (!file.is_open()) {
            std::cout << "Config file not found: " << config_file << std::endl;
            return false;
        }
        
        std::stringstream buffer;
        buffer << file.rdbuf();
        std::string json_content = buffer.str();
        file.close();
        
        return parse_json_config(json_content);
        
    } catch (const std::exception& e) {
        std::cout << "ERROR loading config: " << e.what() << std::endl;
        return false;
    }
}

bool DynamicFieldExtractor::parse_json_config(const std::string& json_content) {
    // Simplified JSON parsing - in production use a proper JSON library
    // For now, parse basic patterns manually
    
    std::istringstream iss(json_content);
    std::string line;
    std::string current_record_type;
    
    enabled_fields_.clear();
    
    while (std::getline(iss, line)) {
        line = trim(line);
        
        // Look for record type definitions like "PTR": {
        if (line.find("\":") != std::string::npos && line.find("{") != std::string::npos) {
            size_t quote_start = line.find('"');
            size_t quote_end = line.find('"', quote_start + 1);
            if (quote_start != std::string::npos && quote_end != std::string::npos) {
                current_record_type = line.substr(quote_start + 1, quote_end - quote_start - 1);
            }
        }
        
        // Look for fields arrays like "fields": ["TEST_NUM", "TEST_FLG"]
        if (line.find("\"fields\":") != std::string::npos && !current_record_type.empty()) {
            size_t bracket_start = line.find('[');
            size_t bracket_end = line.rfind(']');
            
            if (bracket_start != std::string::npos && bracket_end != std::string::npos) {
                std::string fields_str = line.substr(bracket_start + 1, bracket_end - bracket_start - 1);
                
                // Parse individual field names
                std::set<std::string> fields;
                std::istringstream field_stream(fields_str);
                std::string field;
                
                while (std::getline(field_stream, field, ',')) {
                    field = trim(field);
                    if (field.front() == '"') field = field.substr(1);
                    if (field.back() == '"') field = field.substr(0, field.length() - 1);
                    field = trim(field);
                    
                    if (!field.empty()) {
                        fields.insert(field);
                    }
                }
                
                if (!fields.empty()) {
                    enabled_fields_[current_record_type] = fields;
                    std::cout << "Loaded " << fields.size() << " fields for " << current_record_type << std::endl;
                }
            }
        }
    }
    
    return !enabled_fields_.empty();
}

std::string DynamicFieldExtractor::trim(const std::string& str) const {
    size_t start = str.find_first_not_of(" \\t\\n\\r");
    if (start == std::string::npos) return "";
    
    size_t end = str.find_last_not_of(" \\t\\n\\r");
    return str.substr(start, end - start + 1);
}

std::set<std::string> DynamicFieldExtractor::get_enabled_record_types() const {
    std::set<std::string> types;
    for (const auto& pair : enabled_fields_) {
        types.insert(pair.first);
    }
    return types;
}

std::set<std::string> DynamicFieldExtractor::get_enabled_fields(const std::string& record_type) const {
    auto it = enabled_fields_.find(record_type);
    if (it != enabled_fields_.end()) {
        return it->second;
    }
    return {};
}

std::set<std::string> DynamicFieldExtractor::get_all_available_fields(const std::string& record_type) const {
    std::set<std::string> available_fields;
    
    // Use X-Macros to get all available fields for each record type
    if (record_type == "PTR") {
        #define FIELD(name, member) available_fields.insert(name);
        #include "../field_defs/ptr_fields.def"
        #undef FIELD
    }
    else if (record_type == "MPR") {
        #define FIELD(name, member) available_fields.insert(name);
        #include "../field_defs/mpr_fields.def"
        #undef FIELD
    }
    else if (record_type == "FTR") {
        #define FIELD(name, member) available_fields.insert(name);
        #include "../field_defs/ftr_fields.def"
        #undef FIELD
    }
    else if (record_type == "HBR") {
        #define FIELD(name, member) available_fields.insert(name);
        #include "../field_defs/hbr_fields.def"
        #undef FIELD
    }
    else if (record_type == "SBR") {
        #define FIELD(name, member) available_fields.insert(name);
        #include "../field_defs/sbr_fields.def"
        #undef FIELD
    }
    else if (record_type == "PRR") {
        #define FIELD(name, member) available_fields.insert(name);
        #include "../field_defs/prr_fields.def"
        #undef FIELD
    }
    
    return available_fields;
}

bool DynamicFieldExtractor::validate_configuration() const {
    bool valid = true;
    
    for (const auto& record_config : enabled_fields_) {
        const std::string& record_type = record_config.first;
        const std::set<std::string>& enabled_fields = record_config.second;
        
        // Get all available fields for this record type
        std::set<std::string> available_fields = get_all_available_fields(record_type);
        
        if (available_fields.empty()) {
            std::cout << "WARNING: Unknown record type: " << record_type << std::endl;
            valid = false;
            continue;
        }
        
        // Check if all enabled fields are valid
        for (const std::string& field : enabled_fields) {
            if (available_fields.find(field) == available_fields.end()) {
                std::cout << "WARNING: Invalid field '" << field << "' for record type " << record_type << std::endl;
                valid = false;
            }
        }
    }
    
    return valid;
}

void DynamicFieldExtractor::print_configuration_summary() const {
    std::cout << "\nDynamic Field Extractor Configuration:" << std::endl;
    std::cout << "  Config file: " << config_file_path_ << std::endl;
    std::cout << "  Enabled record types: " << enabled_fields_.size() << std::endl;
    
    for (const auto& record_config : enabled_fields_) {
        const std::string& record_type = record_config.first;
        const std::set<std::string>& fields = record_config.second;
        std::set<std::string> available = get_all_available_fields(record_type);
        
        std::cout << "    " << record_type << ": " << fields.size() << "/" << available.size() << " fields enabled" << std::endl;
    }
}

// Field conversion utilities
template<typename T>
std::string DynamicFieldExtractor::field_to_string(T value) const {
    return std::to_string(value);
}

std::string DynamicFieldExtractor::field_to_string(char* str_field) const {
    if (!str_field || str_field[0] == '\0') return "";
    // Check if this is an STDF string (first byte is length)
    if ((unsigned char)str_field[0] <= strlen(str_field + 1)) {
        return std::string(str_field + 1);  // Skip length byte
    }
    return std::string(str_field);  // Regular C string
}

std::string DynamicFieldExtractor::field_to_string(const char* str_field) const {
    return str_field ? std::string(str_field) : "";
}

std::string field_to_string_helper(unsigned char* field) {
    return field ? "present" : "not_present";
}

// X-Macros Template Specializations

// PTR Record Extraction
template<>
void DynamicFieldExtractor::extract_fields<rec_ptr>(rec_ptr* ptr, DynamicSTDFRecord& out_record) {
    if (!ptr) return;
    
    out_record.type_name = "PTR";
    const std::set<std::string>& enabled = get_enabled_fields("PTR");
    
    if (enabled.empty()) return;  // No fields enabled for PTR
    
    // X-Macros magic: Generate field extraction code
    #define FIELD(name, member) \
        if (enabled.count(name)) { \
            out_record.fields[name] = std::to_string(ptr->member); \
        }
    
    #include "../field_defs/ptr_fields.def"
    #undef FIELD
    
    static int debug_count = 0;
    if (debug_count < 2) {
        std::cout << "PTR X-Macros extraction completed - " << out_record.fields.size() << " fields extracted" << std::endl;
        debug_count++;
    }
}

// MPR Record Extraction
template<>
void DynamicFieldExtractor::extract_fields<rec_mpr>(rec_mpr* mpr, DynamicSTDFRecord& out_record) {
    if (!mpr) return;
    
    out_record.type_name = "MPR";
    const std::set<std::string>& enabled = get_enabled_fields("MPR");
    
    if (enabled.empty()) return;
    
    #define FIELD(name, member) \
        if (enabled.count(name)) { \
            out_record.fields[name] = std::to_string(mpr->member); \
        }
    
    #include "../field_defs/mpr_fields.def"
    #undef FIELD
}

// FTR Record Extraction
template<>
void DynamicFieldExtractor::extract_fields<rec_ftr>(rec_ftr* ftr, DynamicSTDFRecord& out_record) {
    if (!ftr) return;
    
    out_record.type_name = "FTR";
    const std::set<std::string>& enabled = get_enabled_fields("FTR");
    
    if (enabled.empty()) return;
    
    #define FIELD(name, member) \
        if (enabled.count(name)) { \
            out_record.fields[name] = std::to_string(ftr->member); \
        }
    
    #include "../field_defs/ftr_fields.def"
    #undef FIELD
}

// HBR Record Extraction
template<>
void DynamicFieldExtractor::extract_fields<rec_hbr>(rec_hbr* hbr, DynamicSTDFRecord& out_record) {
    if (!hbr) return;
    
    out_record.type_name = "HBR";
    const std::set<std::string>& enabled = get_enabled_fields("HBR");
    
    if (enabled.empty()) return;
    
    #define FIELD(name, member) \
        if (enabled.count(name)) { \
            out_record.fields[name] = std::to_string(hbr->member); \
        }
    
    #include "../field_defs/hbr_fields.def"
    #undef FIELD
}

// SBR Record Extraction  
template<>
void DynamicFieldExtractor::extract_fields<rec_sbr>(rec_sbr* sbr, DynamicSTDFRecord& out_record) {
    if (!sbr) return;
    
    out_record.type_name = "SBR";
    const std::set<std::string>& enabled = get_enabled_fields("SBR");
    
    if (enabled.empty()) return;
    
    #define FIELD(name, member) \
        if (enabled.count(name)) { \
            out_record.fields[name] = std::to_string(sbr->member); \
        }
    
    #include "../field_defs/sbr_fields.def"
    #undef FIELD
}

// PRR Record Extraction
template<>
void DynamicFieldExtractor::extract_fields<rec_prr>(rec_prr* prr, DynamicSTDFRecord& out_record) {
    if (!prr) return;
    
    out_record.type_name = "PRR";
    const std::set<std::string>& enabled = get_enabled_fields("PRR");
    
    if (enabled.empty()) return;
    
    #define FIELD(name, member) \
        if (enabled.count(name)) { \
            out_record.fields[name] = std::to_string(prr->member); \
        }
    
    #include "../field_defs/prr_fields.def"
    #undef FIELD
}