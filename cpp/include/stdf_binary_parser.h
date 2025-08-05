#ifndef STDF_BINARY_PARSER_H
#define STDF_BINARY_PARSER_H

#include <vector>
#include <string>
#include <map>
#include <memory>
#include <fstream>
#include <cstdint>

#ifdef _WIN32
    #include <windows.h>
    #define STDF_EXPORT __declspec(dllexport)
#else
    #define STDF_EXPORT
#endif

// STDF V4 Record Types and Subtypes
enum class STDFRecordType : uint8_t {
    MIR = 0x01,  // Master Information Record (1,10)
    SDR = 0x02,  // Site Description Record (1,80) 
    PRR = 0x05,  // Part Result Record (5,20)
    PTR = 0x0F,  // Parametric Test Record (15,20)
    MPR = 0x0F,  // Multiple-Result Parametric Record (15,15)
    FTR = 0x0F,  // Functional Test Record (15,25)
    HBR = 0x01,  // Hardware Bin Record (1,40)
    SBR = 0x01,  // Software Bin Record (1,50)
    UNKNOWN = 0xFF
};

// STDF Record Header
#pragma pack(push, 1)
struct STDFHeader {
    uint16_t length;     // Record length (excluding header)
    uint8_t rec_type;    // Record type
    uint8_t rec_subtype; // Record subtype
};
#pragma pack(pop)

// Parsed STDF record structure
struct STDFRecord {
    STDFRecordType type;
    uint8_t rec_type;
    uint8_t rec_subtype;
    std::map<std::string, std::string> fields;
    
    // Common fields
    uint32_t test_num = 0;
    uint32_t head_num = 0;
    uint32_t site_num = 0;
    
    // PTR/MPR specific
    double result = 0.0;
    std::string alarm_id;
    std::string test_txt;
    std::string units;
    double lo_limit = 0.0;
    double hi_limit = 0.0;
    
    // Context
    std::string filename;
    uint32_t record_index = 0;
    size_t file_position = 0;
};

// Native Windows STDF Binary Parser
class STDF_EXPORT STDFBinaryParser {
public:
    STDFBinaryParser();
    ~STDFBinaryParser();
    
    // Main parsing functions
    bool open_file(const std::string& filepath);
    void close_file();
    std::vector<STDFRecord> parse_all_records();
    STDFRecord parse_next_record();
    bool has_more_records();
    
    // Configuration
    void set_enabled_record_types(const std::vector<STDFRecordType>& types);
    void enable_record_type(uint8_t rec_type, uint8_t rec_subtype);
    void disable_record_type(uint8_t rec_type, uint8_t rec_subtype);
    
    // Statistics
    size_t get_total_records() const { return total_records_; }
    size_t get_parsed_records() const { return parsed_records_; }
    size_t get_file_size() const { return file_size_; }
    
    // Error handling
    std::string get_last_error() const { return last_error_; }
    
private:
    // File operations
    bool read_header(STDFHeader& header);
    std::vector<uint8_t> read_record_data(uint16_t length);
    bool skip_record(uint16_t length);
    
    // STDF data type parsers
    uint8_t read_u1(const uint8_t* data, size_t& offset);
    uint16_t read_u2(const uint8_t* data, size_t& offset);
    uint32_t read_u4(const uint8_t* data, size_t& offset);
    int8_t read_i1(const uint8_t* data, size_t& offset);
    int16_t read_i2(const uint8_t* data, size_t& offset);
    int32_t read_i4(const uint8_t* data, size_t& offset);
    float read_r4(const uint8_t* data, size_t& offset);
    double read_r8(const uint8_t* data, size_t& offset);
    std::string read_cn(const uint8_t* data, size_t& offset);
    std::string read_cf(const uint8_t* data, size_t& offset, uint8_t length);
    
    // Record-specific parsers
    STDFRecord parse_mir_record(const uint8_t* data, uint16_t length);
    STDFRecord parse_ptr_record(const uint8_t* data, uint16_t length);
    STDFRecord parse_mpr_record(const uint8_t* data, uint16_t length);
    STDFRecord parse_ftr_record(const uint8_t* data, uint16_t length);
    STDFRecord parse_prr_record(const uint8_t* data, uint16_t length);
    STDFRecord parse_hbr_record(const uint8_t* data, uint16_t length);
    STDFRecord parse_sbr_record(const uint8_t* data, uint16_t length);
    
    // Utility functions
    STDFRecordType classify_record(uint8_t rec_type, uint8_t rec_subtype);
    bool is_record_enabled(uint8_t rec_type, uint8_t rec_subtype);
    std::string record_type_to_string(STDFRecordType type);
    void set_error(const std::string& error);
    
    // File handling
    std::ifstream file_;
    std::string current_filename_;
    size_t file_size_;
    size_t current_position_;
    
    // Configuration
    std::map<std::pair<uint8_t, uint8_t>, bool> enabled_records_;
    
    // Statistics
    size_t total_records_;
    size_t parsed_records_;
    uint32_t current_record_index_;
    
    // Error handling
    std::string last_error_;
    
    // Context from MIR record
    std::string mir_lot_id_;
    std::string mir_part_typ_;
    std::string mir_job_nam_;
    std::string mir_setup_id_;
};

#endif // STDF_BINARY_PARSER_H