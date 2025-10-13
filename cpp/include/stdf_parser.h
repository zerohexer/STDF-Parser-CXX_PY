#ifndef STDF_PARSER_H
#define STDF_PARSER_H

#include <vector>
#include <string>
#include <map>
#include <memory>
#include <cstdint>

// ============================================================================
// STDF Record Type Enum - Auto-generated from field_defs/record_types.def
// ============================================================================
enum class STDFRecordType {
    UNKNOWN,

    // X-Macro auto-generates enum values from registry
    #define RECORD_TYPE(name, struct_type, typ, sub, macro) name,
    #include "../field_defs/record_types.def"
    #undef RECORD_TYPE
};

// Parsed STDF record structure
struct STDFRecord {
    STDFRecordType type;
    std::map<std::string, std::string> fields;
    uint32_t test_num = 0;
    uint32_t head_num = 0;
    uint32_t site_num = 0;
    
    // Raw record header fields
    uint8_t rec_type = 0;
    uint8_t rec_subtype = 0;
    
    // PTR/MPR specific
    double result = 0.0;
    std::string alarm_id;
    std::string test_txt;
    std::string units;
    
    // Timestamps and context
    std::string wld_id;
    std::string filename;
    uint32_t record_index = 0;
};

// Main STDF Parser class
class STDFParser {
public:
    STDFParser();
    ~STDFParser();
    
    // Main parsing function
    std::vector<STDFRecord> parse_file(const std::string& filepath);
    
    // Configuration
    void set_enabled_record_types(const std::vector<STDFRecordType>& types);
    void set_field_config(const std::string& config_json);
    
    // Statistics
    size_t get_total_records() const { return total_records_; }
    size_t get_parsed_records() const { return parsed_records_; }
    
private:
    // ========================================================================
    // HYBRID APPROACH: Generic Template Parser
    // ========================================================================
    // ONE template handles ALL record types - no more per-type functions!
    template<typename RecordStruct, int LibstdfMacro>
    STDFRecord parse_generic_record(void* raw_record, STDFRecordType type, const char* type_name);

    // Main dispatcher - uses X-Macros to auto-generate switch cases
    STDFRecord parse_record(void* stdf_record, STDFRecordType type);

    // ========================================================================
    // Auto-generated from field_defs/record_types.def
    // ========================================================================
    STDFRecordType get_record_type(uint8_t rec_typ, uint8_t rec_sub);

    // ========================================================================
    // File handling
    // ========================================================================
    bool open_stdf_file(const std::string& filepath);
    void close_stdf_file();

    // Utility functions
    std::string extract_string_field(const char* field, size_t max_len = 255);

    // Temporary sample data for testing (remove when libstdf is integrated)
    void create_sample_records(std::vector<STDFRecord>& results);
    
    // Configuration and state
    std::vector<STDFRecordType> enabled_types_;
    std::map<std::string, std::vector<std::string>> field_config_;
    
    // File handling
    void* stdf_file_handle_;
    std::string current_filename_;
    
    // Statistics
    size_t total_records_;
    size_t parsed_records_;
    
    // Context from MIR record
    std::string mir_lot_id_;
    std::string mir_part_typ_;
    std::string mir_job_nam_;
};

#endif // STDF_PARSER_H