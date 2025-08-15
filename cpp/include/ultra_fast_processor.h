#ifndef ULTRA_FAST_PROCESSOR_H
#define ULTRA_FAST_PROCESSOR_H

#include <vector>
#include <string>
#include <map>
#include <unordered_map>
#include <unordered_set>
#include <memory>
#include <cstdint>
#include <regex>
#include "stdf_parser.h"

/**
 * Ultra-Fast STDF to ClickHouse Processor
 * 
 * Bypasses Python bridge bottleneck by doing ALL processing in C++
 * and only returning final measurement tuples for ClickHouse insertion.
 */

// 🚀 MACRO-DRIVEN: Measurement structure auto-generated from measurement_fields.def
struct MeasurementTuple {
    // Define MEASUREMENT_FIELD macro to generate struct members
    #define MEASUREMENT_FIELD(name, cpp_type, python_conversion, clickhouse_type) \
        cpp_type name;
    
    // Include all fields from measurement_fields.def
    #include "measurement_fields.def"
    
    // Undefine the macro
    #undef MEASUREMENT_FIELD
    
    // Constructor for easy initialization
    MeasurementTuple() = default;
};

// MIR information extracted from STDF
struct MIRInfo {
    std::string facility;
    std::string operation;
    std::string lot_name;
    std::string equipment;
    std::string prog_name;
    std::string prog_version;
    std::string start_time;
};

// Device and parameter ID management with database integration
class FastIDManager {
public:
    FastIDManager();
    
    // Database integration methods
    void load_existing_mappings_from_python(
        const std::vector<std::pair<std::string, uint32_t>>& device_mappings,
        const std::vector<std::pair<std::string, uint32_t>>& param_mappings
    );
    
    uint32_t get_device_id(const std::string& device_dmc);
    uint32_t get_param_id(const std::string& param_name);
    
    const std::unordered_map<std::string, uint32_t>& get_device_map() const { return device_id_map_; }
    const std::unordered_map<std::string, uint32_t>& get_param_map() const { return param_id_map_; }
    
    // Get only new mappings (for database insertion)
    std::vector<std::pair<std::string, uint32_t>> get_new_device_mappings() const;
    std::vector<std::pair<std::string, uint32_t>> get_new_param_mappings() const;
    
private:
    std::unordered_map<std::string, uint32_t> device_id_map_;
    std::unordered_map<std::string, uint32_t> param_id_map_;
    std::unordered_set<std::string> existing_devices_;  // Track pre-existing entries
    std::unordered_set<std::string> existing_params_;   // Track pre-existing entries
    uint32_t device_counter_;
    uint32_t param_counter_;
};

// Ultra-fast STDF processor
class UltraFastProcessor {
public:
    UltraFastProcessor();
    ~UltraFastProcessor();
    
    // Main processing function
    std::vector<MeasurementTuple> process_stdf_file(const std::string& filepath);
    
    // Configuration
    void set_enable_pixel_filtering(bool enable) { enable_pixel_filtering_ = enable; }
    void set_file_hash(const std::string& hash) { file_hash_ = hash; }
    
    // Statistics
    size_t get_total_records() const { return total_records_; }
    size_t get_processed_measurements() const { return processed_measurements_; }
    double get_parsing_time() const { return parsing_time_; }
    double get_processing_time() const { return processing_time_; }
    
    // Get ID mappings for Python bridge
    const FastIDManager& get_id_manager() const { return id_manager_; }
    
private:
    // Core processing functions
    MIRInfo extract_mir_info(const std::vector<STDFRecord>& mir_records);
    std::vector<MeasurementTuple> process_cross_product(
        const std::vector<STDFRecord>& prr_records,
        const std::vector<STDFRecord>& test_records,
        const MIRInfo& mir_info
    );
    
    // Record filtering and processing
    std::vector<STDFRecord> filter_records_by_type(
        const std::vector<STDFRecord>& records, 
        STDFRecordType type
    );
    std::vector<STDFRecord> filter_test_records(const std::vector<STDFRecord>& records);
    
    // Test processing utilities
    bool is_pixel_test(const STDFRecord& test_record);
    std::vector<double> parse_test_values(const STDFRecord& test_record);
    std::pair<int32_t, int32_t> extract_pixel_coordinates(const std::string& text);
    std::string clean_param_name(const std::string& param_name);
    
    // Utility functions
    std::string calculate_file_hash(const std::string& filepath);
    uint8_t calculate_test_flag(const STDFRecord& prr_record);
    
    // Configuration
    bool enable_pixel_filtering_;
    std::string file_hash_;
    
    // ID management
    FastIDManager id_manager_;
    
    // Statistics
    size_t total_records_;
    size_t processed_measurements_;
    double parsing_time_;
    double processing_time_;
    
    // Regex patterns (compiled once)
    std::regex pixel_pattern_;
    std::regex pixel_clean_pattern1_;
    std::regex pixel_clean_pattern2_;
};

#endif // ULTRA_FAST_PROCESSOR_H