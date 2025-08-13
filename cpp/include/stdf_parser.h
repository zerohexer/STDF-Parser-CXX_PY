#ifndef STDF_PARSER_H
#define STDF_PARSER_H

#include <vector>
#include <string>
#include <map>
#include <memory>
#include <cstdint>

// STDF Record Types we care about
enum class STDFRecordType {
    PTR,  // Parametric Test Record
    MPR,  // Multiple-Result Parametric Record  
    FTR,  // Functional Test Record
    HBR,  // Hardware Bin Record
    SBR,  // Software Bin Record
    PRR,  // Part Result Record
    MIR,  // Master Information Record
    UNKNOWN
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
    // libstdf integration
    bool open_stdf_file(const std::string& filepath);
    void close_stdf_file();
    STDFRecord parse_record(void* stdf_record, STDFRecordType type);
    STDFRecord parse_record_safe(void* stdf_record, STDFRecordType type);
    
    // Temporary sample data for testing (remove when libstdf is integrated)
    void create_sample_records(std::vector<STDFRecord>& results);
    
    // Record-specific parsers
    STDFRecord parse_ptr_record(void* ptr_rec);
    STDFRecord parse_mpr_record(void* mpr_rec);
    STDFRecord parse_ftr_record(void* ftr_rec);
    STDFRecord parse_hbr_record(void* hbr_rec);
    STDFRecord parse_sbr_record(void* sbr_rec);
    STDFRecord parse_mir_record(void* mir_rec);
    STDFRecord parse_prr_record(void* prr_rec);
    
    // Utility functions
    STDFRecordType get_record_type(uint8_t rec_typ, uint8_t rec_sub);
    std::string extract_string_field(const char* field, size_t max_len = 255);
    
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