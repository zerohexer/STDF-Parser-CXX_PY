#include "../include/ultra_fast_processor.h"
#include "../include/measurement_macros.h"
#include <iostream>
#include <fstream>
#include <sstream>
#include <chrono>
#include <algorithm>
#include <iomanip>

// FastIDManager Implementation
FastIDManager::FastIDManager() 
    : device_counter_(0), param_counter_(0) {
}

void FastIDManager::load_existing_mappings_from_python(
    const std::vector<std::pair<std::string, uint32_t>>& device_mappings,
    const std::vector<std::pair<std::string, uint32_t>>& param_mappings) {
    
    // Load existing device mappings
    uint32_t max_device_id = 0;
    for (const auto& pair : device_mappings) {
        device_id_map_[pair.first] = pair.second;
        existing_devices_.insert(pair.first);
        max_device_id = std::max(max_device_id, pair.second);
    }
    device_counter_ = max_device_id + 1;
    
    // Load existing parameter mappings
    uint32_t max_param_id = 0;
    for (const auto& pair : param_mappings) {
        param_id_map_[pair.first] = pair.second;
        existing_params_.insert(pair.first);
        max_param_id = std::max(max_param_id, pair.second);
    }
    param_counter_ = max_param_id + 1;
    
    std::cout << "🔧 Loaded " << device_mappings.size() << " existing device mappings, " 
              << param_mappings.size() << " parameter mappings" << std::endl;
    std::cout << "🔢 Starting counters: devices=" << device_counter_ 
              << ", parameters=" << param_counter_ << std::endl;
}

uint32_t FastIDManager::get_device_id(const std::string& device_dmc) {
    auto it = device_id_map_.find(device_dmc);
    if (it != device_id_map_.end()) {
        return it->second;
    }
    
    uint32_t new_id = device_counter_++;
    device_id_map_[device_dmc] = new_id;
    return new_id;
}

uint32_t FastIDManager::get_param_id(const std::string& param_name) {
    auto it = param_id_map_.find(param_name);
    if (it != param_id_map_.end()) {
        return it->second;
    }
    
    uint32_t new_id = param_counter_++;
    param_id_map_[param_name] = new_id;
    return new_id;
}

// UltraFastProcessor Implementation
UltraFastProcessor::UltraFastProcessor()
    : enable_pixel_filtering_(true)
    , total_records_(0)
    , processed_measurements_(0)
    , parsing_time_(0.0)
    , processing_time_(0.0)
    , pixel_pattern_(R"(Pixel=R(\d+)C(\d+))")
    , pixel_clean_pattern1_(R"(;Pixel=R\d+C\d+)")
    , pixel_clean_pattern2_(R"(^Pixel=R\d+C\d+;)") {
}

UltraFastProcessor::~UltraFastProcessor() {
}

std::vector<MeasurementTuple> UltraFastProcessor::process_stdf_file(const std::string& filepath) {
    std::vector<MeasurementTuple> measurements;
    
    auto start_time = std::chrono::high_resolution_clock::now();
    
    try {
        std::cout << "🚀 Ultra-fast C++ processing: " << filepath << std::endl;
        
        // Step 1: Parse STDF file using existing parser
        auto parse_start = std::chrono::high_resolution_clock::now();
        
        STDFParser parser;
        std::vector<STDFRecord> records = parser.parse_file(filepath);
        
        auto parse_end = std::chrono::high_resolution_clock::now();
        parsing_time_ = std::chrono::duration<double>(parse_end - parse_start).count();
        total_records_ = records.size();
        
        std::cout << "⚡ C++ parsed " << total_records_ << " records in " 
                  << parsing_time_ << "s" << std::endl;
        
        // Step 2: Process records entirely in C++
        auto process_start = std::chrono::high_resolution_clock::now();
        
        // Group records by type
        auto mir_records = filter_records_by_type(records, STDFRecordType::MIR);
        auto prr_records = filter_records_by_type(records, STDFRecordType::PRR);
        auto test_records = filter_test_records(records);
        
        std::cout << "📊 Found " << mir_records.size() << " MIR, " 
                  << prr_records.size() << " PRR, " 
                  << test_records.size() << " test records" << std::endl;
        
        // Extract MIR information
        MIRInfo mir_info = extract_mir_info(mir_records);
        
        // Generate file hash if not set
        if (file_hash_.empty()) {
            file_hash_ = calculate_file_hash(filepath);
        }
        
        // Process cross-product in C++
        measurements = process_cross_product(prr_records, test_records, mir_info);
        
        auto process_end = std::chrono::high_resolution_clock::now();
        processing_time_ = std::chrono::duration<double>(process_end - process_start).count();
        processed_measurements_ = measurements.size();
        
        auto total_time = std::chrono::duration<double>(process_end - start_time).count();
        
        std::cout << "✅ Ultra-fast C++ processing completed:" << std::endl;
        std::cout << "   📊 Total records: " << total_records_ << std::endl;
        std::cout << "   📊 Measurements: " << processed_measurements_ << std::endl;
        std::cout << "   ⏱️ Parsing time: " << parsing_time_ << "s" << std::endl;
        std::cout << "   ⏱️ Processing time: " << processing_time_ << "s" << std::endl;
        std::cout << "   ⏱️ Total time: " << total_time << "s" << std::endl;
        
        if (total_time > 0) {
            double throughput = processed_measurements_ / total_time;
            std::cout << "   🚀 Throughput: " << static_cast<uint64_t>(throughput) 
                      << " measurements/second" << std::endl;
        }
        
    } catch (const std::exception& e) {
        std::cerr << "❌ Error in ultra-fast processing: " << e.what() << std::endl;
    }
    
    return measurements;
}

MIRInfo UltraFastProcessor::extract_mir_info(const std::vector<STDFRecord>& mir_records) {
    MIRInfo mir_info;
    
    if (!mir_records.empty()) {
        const auto& mir = mir_records[0];
        
        // Extract MIR fields with fallbacks
        auto get_field = [&](const std::string& key, const std::string& fallback = "") {
            auto it = mir.fields.find(key);
            return (it != mir.fields.end()) ? it->second : fallback;
        };
        
        mir_info.facility = get_field("FACIL_ID", get_field("FLOOR_ID"));
        mir_info.operation = get_field("OPER_NAM", get_field("SPEC_NAM"));
        mir_info.lot_name = get_field("LOT_ID", get_field("PART_TYP"));
        mir_info.equipment = get_field("NODE_NAM", get_field("JOB_NAM"));
        mir_info.prog_name = get_field("JOB_REV");
        mir_info.prog_version = get_field("SBLOT_ID");
        mir_info.start_time = get_field("START_T");
    }
    
    return mir_info;
}

std::vector<MeasurementTuple> UltraFastProcessor::process_cross_product(
    const std::vector<STDFRecord>& prr_records,
    const std::vector<STDFRecord>& test_records,
    const MIRInfo& mir_info) {
    
    std::vector<MeasurementTuple> measurements;
    
    if (prr_records.empty() || test_records.empty()) {
        std::cout << "⚠️ No PRR or test records found for cross-product" << std::endl;
        return measurements;
    }
    
    // Pre-allocate measurements vector
    size_t estimated_size = prr_records.size() * test_records.size() * 3; // Estimate 3 values per test
    measurements.reserve(estimated_size);
    
    std::cout << "🚀 C++ cross-product: " << prr_records.size() << " devices × " 
              << test_records.size() << " tests = ~" << estimated_size << " estimated measurements" << std::endl;
    
    // Pre-process test records with pixel filtering
    struct ProcessedTest {
        std::vector<double> values;
        std::string cleaned_param_name;
        std::string units;
        uint32_t test_num;
        uint8_t test_flg;
        int32_t pixel_x;
        int32_t pixel_y;
        uint32_t param_id;
    };
    
    std::vector<ProcessedTest> processed_tests;
    processed_tests.reserve(test_records.size());
    
    size_t pixel_tests_found = 0;
    
    for (const auto& test : test_records) {
        // Apply pixel filtering if enabled
        if (enable_pixel_filtering_ && !is_pixel_test(test)) {
            continue;
        }
        
        pixel_tests_found++;
        
        ProcessedTest pt;
        
        // Parse test values
        pt.values = parse_test_values(test);
        
        // Clean parameter name
        std::string param_name = test.alarm_id.empty() ? test.test_txt : test.alarm_id;
        pt.cleaned_param_name = clean_param_name(param_name);
        pt.param_id = id_manager_.get_param_id(pt.cleaned_param_name);
        
        // Extract other fields
        auto get_field = [&](const std::string& key, const std::string& fallback = "") {
            auto it = test.fields.find(key);
            return (it != test.fields.end()) ? it->second : fallback;
        };
        
        pt.units = test.units;
        pt.test_num = test.test_num;
        
        // Parse TEST_FLG
        std::string test_flg_str = get_field("TEST_FLG", "0");
        pt.test_flg = static_cast<uint8_t>(std::stoul(test_flg_str));
        
        // Extract pixel coordinates
        auto coords = extract_pixel_coordinates(param_name);
        pt.pixel_x = coords.first;
        pt.pixel_y = coords.second;
        
        processed_tests.push_back(std::move(pt));
    }
    
    std::cout << "🎯 Pre-processed " << pixel_tests_found << " pixel tests from " 
              << test_records.size() << " total tests" << std::endl;
    
    // Process cross-product
    size_t measurements_created = 0;
    
    for (const auto& prr : prr_records) {
        // Extract device information
        auto get_prr_field = [&](const std::string& key, const std::string& fallback = "") {
            auto it = prr.fields.find(key);
            return (it != prr.fields.end()) ? it->second : fallback;
        };
        
        std::string device_dmc = get_prr_field("PART_ID", get_prr_field("PART_TXT"));
        std::string bin_code = get_prr_field("SOFT_BIN", get_prr_field("HARD_BIN"));
        
        // Parse coordinates with defaults
        int32_t default_x = 0, default_y = 0;
        try {
            std::string x_coord = get_prr_field("X_COORD", "0");
            std::string y_coord = get_prr_field("Y_COORD", "0");
            default_x = std::stoi(x_coord);
            default_y = std::stoi(y_coord);
        } catch (...) {
            // Use defaults if parsing fails
        }
        
        uint32_t device_id = id_manager_.get_device_id(device_dmc);
        uint8_t test_flag = calculate_test_flag(prr);
        
        // Create measurements for this device  
        for (const auto& test : processed_tests) {
            for (double value : test.values) {
                MeasurementTuple measurement;
                
                // 🚀 MACRO-DRIVEN: Initialize all fields using macro  
                INIT_MEASUREMENT(measurement, device_dmc, device_id, test, value, test_flag, file_hash_);
                
                measurements.push_back(std::move(measurement));
                measurements_created++;
            }
        }
    }
    
    std::cout << "✅ C++ cross-product completed: " << measurements_created 
              << " measurements created" << std::endl;
    
    return measurements;
}

std::vector<STDFRecord> UltraFastProcessor::filter_records_by_type(
    const std::vector<STDFRecord>& records, 
    STDFRecordType type) {
    
    std::vector<STDFRecord> filtered;
    
    for (const auto& record : records) {
        if (record.type == type) {
            filtered.push_back(record);
        }
    }
    
    return filtered;
}

std::vector<STDFRecord> UltraFastProcessor::filter_test_records(const std::vector<STDFRecord>& records) {
    std::vector<STDFRecord> test_records;
    
    for (const auto& record : records) {
        if (record.type == STDFRecordType::PTR || 
            record.type == STDFRecordType::MPR ||
            record.type == STDFRecordType::FTR) {
            test_records.push_back(record);
        }
    }
    
    return test_records;
}

bool UltraFastProcessor::is_pixel_test(const STDFRecord& test_record) {
    const std::string& alarm_id = test_record.alarm_id;
    const std::string& test_txt = test_record.test_txt;
    
    return (alarm_id.find("Pixel=") != std::string::npos) ||
           (test_txt.find("Pixel=") != std::string::npos);
}

std::vector<double> UltraFastProcessor::parse_test_values(const STDFRecord& test_record) {
    std::vector<double> values;
    
    // Try to get result from different sources
    std::string value_str;
    
    // For PTR records, use result field
    if (test_record.type == STDFRecordType::PTR && test_record.result != 0.0) {
        values.push_back(test_record.result);
        return values;
    }
    
    // For MPR or other records, try to parse from fields
    auto get_field = [&](const std::string& key) -> std::string {
        auto it = test_record.fields.find(key);
        return (it != test_record.fields.end()) ? it->second : "";
    };
    
    value_str = get_field("RTN_RSLT");
    if (value_str.empty()) {
        value_str = get_field("RESULT");
    }
    if (value_str.empty()) {
        value_str = test_record.test_txt;
    }
    
    if (value_str.empty()) {
        values.push_back(0.0);
        return values;
    }
    
    // Parse comma-separated values
    if (value_str.find(',') != std::string::npos) {
        std::stringstream ss(value_str);
        std::string token;
        
        while (std::getline(ss, token, ',')) {
            try {
                // Trim whitespace
                token.erase(0, token.find_first_not_of(" \t"));
                token.erase(token.find_last_not_of(" \t") + 1);
                
                if (!token.empty()) {
                    values.push_back(std::stod(token));
                }
            } catch (...) {
                // Skip invalid values
            }
        }
    } else {
        try {
            values.push_back(std::stod(value_str));
        } catch (...) {
            values.push_back(0.0);
        }
    }
    
    if (values.empty()) {
        values.push_back(0.0);
    }
    
    return values;
}

std::pair<int32_t, int32_t> UltraFastProcessor::extract_pixel_coordinates(const std::string& text) {
    std::smatch match;
    
    if (std::regex_search(text, match, pixel_pattern_)) {
        try {
            int32_t row = std::stoi(match[1].str());  // R = Row = Y
            int32_t col = std::stoi(match[2].str());  // C = Column = X
            return {col, row}; // Return as (X, Y)
        } catch (...) {
            // Parsing failed
        }
    }
    
    return {0, 0}; // Default coordinates
}

std::string UltraFastProcessor::clean_param_name(const std::string& param_name) {
    if (param_name.empty()) {
        return param_name;
    }
    
    std::string cleaned = param_name;
    
    // Remove ;Pixel=R##C## pattern
    cleaned = std::regex_replace(cleaned, pixel_clean_pattern1_, "");
    
    // Remove Pixel=R##C##; at beginning
    cleaned = std::regex_replace(cleaned, pixel_clean_pattern2_, "");
    
    return cleaned;
}

std::string UltraFastProcessor::calculate_file_hash(const std::string& filepath) {
    std::ifstream file(filepath, std::ios::binary);
    if (!file) {
        return "";
    }
    
    // Simple hash calculation without OpenSSL dependency
    std::hash<std::string> hasher;
    std::string file_content;
    
    // Read file content
    file.seekg(0, std::ios::end);
    file_content.reserve(file.tellg());
    file.seekg(0, std::ios::beg);
    
    file_content.assign((std::istreambuf_iterator<char>(file)),
                        std::istreambuf_iterator<char>());
    
    // Generate hash
    size_t hash_value = hasher(file_content);
    
    std::stringstream ss;
    ss << std::hex << hash_value;
    
    return ss.str();
}

std::vector<std::pair<std::string, uint32_t>> FastIDManager::get_new_device_mappings() const {
    std::vector<std::pair<std::string, uint32_t>> new_mappings;
    
    for (const auto& pair : device_id_map_) {
        // Only include devices that weren't in the existing set
        if (existing_devices_.find(pair.first) == existing_devices_.end()) {
            new_mappings.push_back(pair);
        }
    }
    
    return new_mappings;
}

std::vector<std::pair<std::string, uint32_t>> FastIDManager::get_new_param_mappings() const {
    std::vector<std::pair<std::string, uint32_t>> new_mappings;
    
    for (const auto& pair : param_id_map_) {
        // Only include parameters that weren't in the existing set
        if (existing_params_.find(pair.first) == existing_params_.end()) {
            new_mappings.push_back(pair);
        }
    }
    
    return new_mappings;
}

uint8_t UltraFastProcessor::calculate_test_flag(const STDFRecord& prr_record) {
    auto get_field = [&](const std::string& key) -> std::string {
        auto it = prr_record.fields.find(key);
        return (it != prr_record.fields.end()) ? it->second : "";
    };
    
    std::string bin_code = get_field("SOFT_BIN");
    if (bin_code.empty()) {
        bin_code = get_field("HARD_BIN");
    }
    
    try {
        return (std::stoi(bin_code) == 1) ? 1 : 0;
    } catch (...) {
        return 0;
    }
}