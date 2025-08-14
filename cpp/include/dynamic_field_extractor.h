#ifndef DYNAMIC_FIELD_EXTRACTOR_H
#define DYNAMIC_FIELD_EXTRACTOR_H

#include <string>
#include <map>
#include <set>
#include <vector>
#include <fstream>
#include <sstream>
#include <iostream>
#include <memory>
#include <libstdf.h>

// Use STDFRecord from stdf_parser.h - avoid redefinition
struct STDFRecord;

// STDF Dynamic Record structure (different from parser's STDFRecord)
struct DynamicSTDFRecord {
    std::string type_name;
    std::map<std::string, std::string> fields;
    int record_index;
    std::string filename;
};

/**
 * Dynamic Field Extractor using X-Macros approach
 * 
 * Features:
 * - JSON configuration-driven field selection
 * - Compile-time safety with X-Macros
 * - Zero runtime overhead when fields disabled
 * - Automatic field validation
 */
class DynamicFieldExtractor {
public:
    DynamicFieldExtractor(const std::string& config_file = "stdf_field_config.json");
    
    // Configuration management
    bool load_configuration(const std::string& config_file);
    bool reload_configuration();
    void set_config_from_json(const std::string& json_content);
    
    // Field extraction interface
    template<typename RecordType>
    void extract_fields(RecordType* record, DynamicSTDFRecord& out_record);
    
    // Utility functions
    std::set<std::string> get_enabled_record_types() const;
    std::set<std::string> get_enabled_fields(const std::string& record_type) const;
    std::set<std::string> get_all_available_fields(const std::string& record_type) const;
    
    // Validation
    bool validate_configuration() const;
    void print_configuration_summary() const;
    
private:
    std::string config_file_path_;
    std::map<std::string, std::set<std::string>> enabled_fields_;
    
    // Helper functions
    std::string trim(const std::string& str) const;
    bool parse_json_config(const std::string& json_content);
};

// Template specializations for each record type (implemented in .cpp file)
template<> void DynamicFieldExtractor::extract_fields<rec_ptr>(rec_ptr* record, DynamicSTDFRecord& out_record);
template<> void DynamicFieldExtractor::extract_fields<rec_mpr>(rec_mpr* record, DynamicSTDFRecord& out_record);
template<> void DynamicFieldExtractor::extract_fields<rec_ftr>(rec_ftr* record, DynamicSTDFRecord& out_record);
template<> void DynamicFieldExtractor::extract_fields<rec_hbr>(rec_hbr* record, DynamicSTDFRecord& out_record);
template<> void DynamicFieldExtractor::extract_fields<rec_sbr>(rec_sbr* record, DynamicSTDFRecord& out_record);
template<> void DynamicFieldExtractor::extract_fields<rec_prr>(rec_prr* record, DynamicSTDFRecord& out_record);

#endif // DYNAMIC_FIELD_EXTRACTOR_H