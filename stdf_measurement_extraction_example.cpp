#include <iostream>
#include <vector>
#include <chrono>
#include <iomanip>
#include <string>
#include <memory>
#include <unordered_map>
#include <sstream>
#include <regex>

// Include project headers
#include "cpp/include/stdf_parser.h"
#include "cpp/include/ultra_fast_processor.h"
#include "cpp/include/dynamic_field_extractor.h"

/**
 * Standalone C++ STDF Measurement Extraction Example
 *
 * This program demonstrates how to:
 * 1. Load an STDF file using the STDFParser
 * 2. Extract measurements using the UltraFastProcessor
 * 3. Display comprehensive timing statistics
 * 4. Show sample measurements data
 */

class PerformanceTimer {
private:
    std::chrono::high_resolution_clock::time_point start_time;
    std::string operation_name;

public:
    PerformanceTimer(const std::string& name) : operation_name(name) {
        start_time = std::chrono::high_resolution_clock::now();
        std::cout << "🚀 Starting: " << operation_name << "..." << std::endl;
    }

    ~PerformanceTimer() {
        auto end_time = std::chrono::high_resolution_clock::now();
        auto duration = std::chrono::duration<double>(end_time - start_time).count();
        std::cout << "✅ Completed: " << operation_name << " in "
                  << std::fixed << std::setprecision(3) << duration << "s" << std::endl;
    }

    double elapsed() const {
        auto current_time = std::chrono::high_resolution_clock::now();
        return std::chrono::duration<double>(current_time - start_time).count();
    }
};

void print_banner() {
    std::cout << "===============================================================" << std::endl;
    std::cout << "🔬 STDF Measurement Extraction Example" << std::endl;
    std::cout << "   Ultra-Fast C++ Processing with Timing Statistics" << std::endl;
    std::cout << "===============================================================" << std::endl;
}

void print_measurement_sample(const std::vector<MeasurementTuple>& measurements, int sample_count = 5) {
    std::cout << "\n📊 SAMPLE MEASUREMENTS (first " << std::min(sample_count, (int)measurements.size()) << "):" << std::endl;
    std::cout << "─────────────────────────────────────────────────────────────" << std::endl;

    int count = 0;
    for (const auto& measurement : measurements) {
        if (count >= sample_count) break;

        std::cout << "Measurement #" << (count + 1) << ":" << std::endl;

        // 🚀 MACRO-DRIVEN: Display all fields automatically
        #define MEASUREMENT_FIELD(name, cpp_type, python_conversion, clickhouse_type) \
            std::cout << "  " << #name << ": " << measurement.name << std::endl;

        #include "cpp/field_defs/measurement_fields.def"
        #undef MEASUREMENT_FIELD

        std::cout << std::endl;
        count++;
    }
}

// Forward declarations
std::vector<double> parse_comma_separated_values(const std::string& input);
void print_2phase_with_comma_statistics(size_t total_records, size_t total_measurements, double parsing_time, double processing_time, double total_time);
double safe_string_to_double(const std::string& str);
std::string clean_param_name(const std::string& param_name);
std::pair<int32_t, int32_t> extract_pixel_coordinates(const std::string& alarm_id, const std::string& test_txt, int32_t default_x, int32_t default_y);
std::pair<int32_t, int32_t> parse_pixel_coords(const std::string& text);
bool is_pixel_test(const STDFRecord& record);
std::vector<MeasurementTuple> process_records_to_measurements(const std::vector<STDFRecord>& mir_records, const std::vector<STDFRecord>& prr_records, const std::vector<STDFRecord>& test_records);

void print_ultrafast_statistics(const UltraFastProcessor& processor, size_t total_measurements, double total_time) {
    std::cout << "\n📈 🚀 ULTRA-FAST PROCESSING STATISTICS:" << std::endl;
    std::cout << "═════════════════════════════════════════════════════════════" << std::endl;

    // Parsing statistics
    std::cout << "📄 STDF Parsing:" << std::endl;
    std::cout << "  Total records:        " << processor.get_total_records() << std::endl;
    std::cout << "  Parsing time:         " << std::fixed << std::setprecision(3)
              << processor.get_parsing_time() << "s" << std::endl;

    if (processor.get_parsing_time() > 0) {
        double parse_throughput = processor.get_total_records() / processor.get_parsing_time();
        std::cout << "  Parse throughput:     " << std::fixed << std::setprecision(0)
                  << parse_throughput << " records/second" << std::endl;
    }

    std::cout << std::endl;

    // Processing statistics (with pre-compute)
    std::cout << "⚡ Ultra-Fast Processing (with pre-compute):" << std::endl;
    std::cout << "  Measurements created: " << total_measurements << std::endl;
    std::cout << "  Processing time:      " << std::fixed << std::setprecision(3)
              << processor.get_processing_time() << "s" << std::endl;

    if (processor.get_processing_time() > 0) {
        double process_throughput = total_measurements / processor.get_processing_time();
        std::cout << "  Process throughput:   " << std::fixed << std::setprecision(0)
                  << process_throughput << " measurements/second" << std::endl;
    }

    std::cout << std::endl;

    // Overall statistics
    std::cout << "🎯 Overall Performance:" << std::endl;
    std::cout << "  Total time:           " << std::fixed << std::setprecision(3)
              << total_time << "s" << std::endl;

    if (total_time > 0) {
        double overall_throughput = total_measurements / total_time;
        std::cout << "  Overall throughput:   " << std::fixed << std::setprecision(0)
                  << overall_throughput << " measurements/second" << std::endl;
    }

    // Time breakdown
    double parsing_time = processor.get_parsing_time();
    double processing_time = processor.get_processing_time();
    std::cout << "  Time breakdown:" << std::endl;
    std::cout << "    Parsing:            " << std::fixed << std::setprecision(1)
              << (parsing_time / total_time * 100) << "%" << std::endl;
    std::cout << "    Processing:         " << std::fixed << std::setprecision(1)
              << (processing_time / total_time * 100) << "%" << std::endl;

    std::cout << "═════════════════════════════════════════════════════════════" << std::endl;
}

void print_processor_statistics(const UltraFastProcessor& processor, const std::vector<MeasurementTuple>& measurements, double total_time) {
    const auto& id_manager = processor.get_id_manager();
    const auto& device_map = id_manager.get_device_map();
    const auto& param_map = id_manager.get_param_map();

    std::cout << "\n🔢 ID MANAGEMENT STATISTICS:" << std::endl;
    std::cout << "─────────────────────────────────────────────────────────────" << std::endl;
    std::cout << "Device mappings:       " << device_map.size() << std::endl;
    std::cout << "Parameter mappings:    " << param_map.size() << std::endl;
    std::cout << "Measurements created:  " << measurements.size() << std::endl;

    if (measurements.size() > 0 && param_map.size() > 0) {
        double avg_measurements_per_param = static_cast<double>(measurements.size()) / param_map.size();
        std::cout << "Avg measurements/param: " << std::fixed << std::setprecision(1) << avg_measurements_per_param << std::endl;
    }

    // Sample device mappings
    std::cout << "\nSample Device Mappings (first 3):" << std::endl;
    int count = 0;
    for (const auto& pair : device_map) {
        if (count >= 3) break;
        std::cout << "  " << pair.second << " -> \"" << pair.first << "\"" << std::endl;
        count++;
    }

    // Sample parameter mappings
    std::cout << "\nSample Parameter Mappings (first 3):" << std::endl;
    count = 0;
    for (const auto& pair : param_map) {
        if (count >= 3) break;
        std::cout << "  " << pair.second << " -> \"" << pair.first.substr(0, 50) << "...\"" << std::endl;
        count++;
    }
}

void print_2phase_with_comma_statistics(size_t total_records, size_t total_measurements, double parsing_time, double processing_time, double total_time) {
    std::cout << "\n📈 2-PHASE PROCESSING STATISTICS (with comma parsing):" << std::endl;
    std::cout << "═════════════════════════════════════════════════════════════" << std::endl;

    // Phase 1: Parsing statistics
    std::cout << "📄 Phase 1 - STDF Parsing:" << std::endl;
    std::cout << "  Total records:        " << total_records << std::endl;
    std::cout << "  Parsing time:         " << std::fixed << std::setprecision(3)
              << parsing_time << "s" << std::endl;

    if (parsing_time > 0) {
        double parse_throughput = total_records / parsing_time;
        std::cout << "  Parse throughput:     " << std::fixed << std::setprecision(0)
                  << parse_throughput << " records/second" << std::endl;
    }

    std::cout << std::endl;

    // Phase 2: Processing statistics (with comma parsing creating multiple measurements per test)
    std::cout << "⚡ Phase 2 - Measurement Processing (with comma parsing):" << std::endl;
    std::cout << "  Measurements created: " << total_measurements << std::endl;
    std::cout << "  Processing time:      " << std::fixed << std::setprecision(3)
              << processing_time << "s" << std::endl;

    if (processing_time > 0) {
        double process_throughput = total_measurements / processing_time;
        std::cout << "  Process throughput:   " << std::fixed << std::setprecision(0)
                  << process_throughput << " measurements/second" << std::endl;
    }

    std::cout << std::endl;

    // Overall statistics
    std::cout << "🎯 Overall Performance:" << std::endl;
    std::cout << "  Total time:           " << std::fixed << std::setprecision(3)
              << total_time << "s" << std::endl;

    if (total_time > 0) {
        double overall_throughput = total_measurements / total_time;
        std::cout << "  Overall throughput:   " << std::fixed << std::setprecision(0)
                  << overall_throughput << " measurements/second" << std::endl;
    }

    // Show the pre-compute benefit
    if (total_measurements > 1000000) {
        std::cout << "  🚀 MEGA PERFORMANCE:  " << std::fixed << std::setprecision(1)
                  << (total_measurements / 1000000.0) << "M measurements created!" << std::endl;
    }

    // Time breakdown
    std::cout << "  Time breakdown:" << std::endl;
    std::cout << "    Parsing:            " << std::fixed << std::setprecision(1)
              << (parsing_time / total_time * 100) << "%" << std::endl;
    std::cout << "    Processing:         " << std::fixed << std::setprecision(1)
              << (processing_time / total_time * 100) << "%" << std::endl;

    std::cout << "═════════════════════════════════════════════════════════════" << std::endl;
}

std::vector<double> parse_comma_separated_values(const std::string& input) {
    /**
     * Parse comma-separated values like Python extract_all_measurements.py line 349-360
     */
    std::vector<double> values;
    if (input.empty()) {
        return {0.0};
    }

    if (input.find(',') != std::string::npos) {
        // Split by comma and parse each value
        std::stringstream ss(input);
        std::string item;
        while (std::getline(ss, item, ',')) {
            // Trim whitespace
            item.erase(0, item.find_first_not_of(" \t"));
            item.erase(item.find_last_not_of(" \t") + 1);
            if (!item.empty()) {
                values.push_back(safe_string_to_double(item));
            }
        }
        return values.empty() ? std::vector<double>{0.0} : values;
    }

    // Single value
    return {safe_string_to_double(input)};
}

double safe_string_to_double(const std::string& str) {
    /**
     * Safely convert string to double (like Python _safe_float)
     */
    if (str.empty()) return 0.0;
    try {
        return std::stod(str);
    } catch (...) {
        return 0.0;
    }
}

std::string clean_param_name(const std::string& param_name) {
    /**
     * Clean parameter name by removing pixel patterns (like Python extract_all_measurements.py line 339-347)
     */
    if (param_name.empty()) return param_name;

    std::string cleaned = param_name;

    // Remove ;Pixel=R##C## patterns
    std::regex pattern1(";Pixel=R\\d+C\\d+");
    cleaned = std::regex_replace(cleaned, pattern1, "");

    // Remove ^Pixel=R##C##; patterns
    std::regex pattern2("^Pixel=R\\d+C\\d+;");
    cleaned = std::regex_replace(cleaned, pattern2, "");

    return cleaned;
}

std::pair<int32_t, int32_t> extract_pixel_coordinates(const std::string& alarm_id,
                                                      const std::string& test_txt,
                                                      int32_t default_x, int32_t default_y) {
    /**
     * Extract pixel coordinates like Python extract_all_measurements.py line 327-337
     */
    // Try alarm_id first
    auto coords = parse_pixel_coords(alarm_id);
    if (coords.first != -1) {
        return coords;
    }

    // Try test_txt
    coords = parse_pixel_coords(test_txt);
    if (coords.first != -1) {
        return coords;
    }

    // Use defaults
    return {default_x, default_y};
}

std::pair<int32_t, int32_t> parse_pixel_coords(const std::string& text) {
    /**
     * Parse Pixel=R##C## pattern (like Python extract_all_measurements.py line 314-325)
     */
    if (text.empty() || text.find("Pixel=") == std::string::npos) {
        return {-1, -1};
    }

    std::regex pattern("Pixel=R(\\d+)C(\\d+)");
    std::smatch match;

    if (std::regex_search(text, match, pattern)) {
        int row = std::stoi(match[1].str());  // R = Row = Y
        int col = std::stoi(match[2].str());  // C = Column = X
        return {col, row};  // Return as (X, Y)
    }

    return {-1, -1};
}

bool is_pixel_test(const STDFRecord& record) {
    /**
     * Check if test involves pixel coordinates (same logic as Python extract_all_measurements.py line 363)
     */
    auto alarm_it = record.fields.find("ALARM_ID");
    auto test_txt_it = record.fields.find("TEST_TXT");

    std::string alarm_id = (alarm_it != record.fields.end()) ? alarm_it->second : "";
    std::string test_txt = (test_txt_it != record.fields.end()) ? test_txt_it->second : "";

    return (alarm_id.find("Pixel=") != std::string::npos) ||
           (test_txt.find("Pixel=") != std::string::npos);
}

std::vector<MeasurementTuple> process_records_to_measurements(
    const std::vector<STDFRecord>& mir_records,
    const std::vector<STDFRecord>& prr_records,
    const std::vector<STDFRecord>& test_records) {
    /**
     * Process records to measurements using the SAME logic as Python extract_all_measurements.py
     * This includes the critical pixel filtering that makes it fast!
     */

    std::vector<MeasurementTuple> measurements;

    if (prr_records.empty()) {
        std::cout << "❌ No PRR records found - cannot create measurements" << std::endl;
        return measurements;
    }

    // Phase 2a: Filter for pixel tests FIRST (like Python line 192-193)
    std::vector<STDFRecord> pixel_tests;
    std::cout << "🎯 Filtering for pixel tests..." << std::endl;

    for (const auto& test : test_records) {
        if (is_pixel_test(test)) {
            pixel_tests.push_back(test);
        }
    }

    std::cout << "📊 Filtered: " << pixel_tests.size() << " pixel tests from "
              << test_records.size() << " total tests" << std::endl;

    if (pixel_tests.empty()) {
        std::cout << "⚠️ No pixel tests found - no measurements will be created" << std::endl;
        return measurements;
    }

    // Phase 2b: Cross-product with ONLY pixel tests (much faster!)
    std::cout << "🔄 Cross-product: " << prr_records.size() << " devices × "
              << pixel_tests.size() << " pixel tests = "
              << (prr_records.size() * pixel_tests.size()) << " operations" << std::endl;

    // Create simple ID managers
    std::unordered_map<std::string, uint32_t> device_ids;
    std::unordered_map<std::string, uint32_t> param_ids;

    size_t measurements_created = 0;
    int devices_processed = 0;

    for (const auto& prr : prr_records) {
        auto get_field = [&](const std::string& key) -> std::string {
            auto it = prr.fields.find(key);
            return (it != prr.fields.end()) ? it->second : "";
        };

        std::string device_dmc = get_field("PART_TXT");
        if (device_dmc.empty()) device_dmc = get_field("PART_ID");

        // Get device ID
        uint32_t device_id;
        if (device_ids.find(device_dmc) == device_ids.end()) {
            device_id = static_cast<uint32_t>(device_ids.size());
            device_ids[device_dmc] = device_id;
        } else {
            device_id = device_ids[device_dmc];
        }

        size_t device_measurements_before = measurements.size();

        // Process ONLY pixel tests for this device
        for (const auto& test : pixel_tests) {
            auto get_test_field = [&](const std::string& key) -> std::string {
                auto it = test.fields.find(key);
                return (it != test.fields.end()) ? it->second : "";
            };

            std::string param_name = get_test_field("ALARM_ID");
            std::string test_txt = get_test_field("TEST_TXT");
            std::string result_str = get_test_field("RESULT");
            std::string rtn_rslt = get_test_field("RTN_RSLT");
            std::string record_type = (test.type == STDFRecordType::MPR) ? "MPR" :
                                     (test.type == STDFRecordType::PTR) ? "PTR" :
                                     (test.type == STDFRecordType::FTR) ? "FTR" : "UNKNOWN";

            // Clean parameter name (remove pixel patterns like Python)
            std::string cleaned_param_name = clean_param_name(param_name);

            // Get parameter ID using cleaned name
            uint32_t param_id;
            if (param_ids.find(cleaned_param_name) == param_ids.end()) {
                param_id = static_cast<uint32_t>(param_ids.size());
                param_ids[cleaned_param_name] = param_id;
            } else {
                param_id = param_ids[cleaned_param_name];
            }

            // 🚀 CRITICAL: Parse comma-separated values like Python extract_all_measurements.py lines 223-239
            std::vector<double> measurement_values;

            if (record_type == "MPR" && !rtn_rslt.empty() && rtn_rslt != "[float_array]") {
                // MPR with RTN_RSLT array (like Python line 224-235)
                if (rtn_rslt.find(',') != std::string::npos) {
                    // Parse comma-separated RTN_RSLT values
                    measurement_values = parse_comma_separated_values(rtn_rslt);
                    std::cout << "DEBUG: MPR with " << measurement_values.size()
                              << " comma-separated values from RTN_RSLT" << std::endl;
                } else {
                    // Single RTN_RSLT value
                    measurement_values = {safe_string_to_double(rtn_rslt)};
                }
            } else {
                // For PTR/FTR or no array - use single result or TEST_TXT comma parsing
                if (test_txt.find(',') != std::string::npos) {
                    // Parse comma-separated values from TEST_TXT
                    measurement_values = parse_comma_separated_values(test_txt);
                    std::cout << "DEBUG: " << record_type << " with " << measurement_values.size()
                              << " comma-separated values from TEST_TXT" << std::endl;
                } else {
                    // Single value - use RESULT field or TEST_TXT
                    double single_value = safe_string_to_double(result_str);
                    if (single_value == 0.0 && !test_txt.empty()) {
                        single_value = safe_string_to_double(test_txt);
                    }
                    measurement_values = {single_value};
                }
            }

            // Extract pixel coordinates (like Python)
            auto [pixel_x, pixel_y] = extract_pixel_coordinates(param_name, test_txt, 0, 0);

            // 🚀 CREATE MULTIPLE MEASUREMENTS: One for each parsed value (like Python lines 284-302)
            for (size_t i = 0; i < measurement_values.size(); i++) {
                double measurement_value = measurement_values[i];

                // Create measurement tuple
                MeasurementTuple measurement;

                // 🚀 MACRO-DRIVEN: Initialize using same pattern as UltraFastProcessor
                #define MEASUREMENT_FIELD(name, cpp_type, python_conversion, clickhouse_type) \
                    measurement.name = cpp_type{};

                #include "cpp/field_defs/measurement_fields.def"
                #undef MEASUREMENT_FIELD

                // Set the actual values
                measurement.wld_id = device_id;
                measurement.wtp_id = param_id;
                measurement.wp_pos_x = pixel_x;
                measurement.wp_pos_y = pixel_y;
                measurement.wptm_value = measurement_value;
                measurement.test_flag = 1; // Pass flag
                measurement.segment = 0;

                // Set string fields (need to be set after macro initialization)
                // Note: These would need proper string handling in a real implementation

                measurements.push_back(measurement);
            }
        }

        size_t device_measurements = measurements.size() - device_measurements_before;
        devices_processed++;

        if (device_measurements > 0) {
            std::cout << "  Device " << devices_processed << "/" << prr_records.size()
                      << ": " << device_dmc << " → " << device_measurements << " measurements" << std::endl;
        }
    }

    std::cout << "✅ Measurement creation completed:" << std::endl;
    std::cout << "   📊 Processed " << devices_processed << " devices" << std::endl;
    std::cout << "   📊 Created " << measurements.size() << " measurements" << std::endl;
    std::cout << "   📊 Device mappings: " << device_ids.size() << std::endl;
    std::cout << "   📊 Parameter mappings: " << param_ids.size() << std::endl;

    return measurements;
}

void print_id_mappings(const std::vector<MeasurementTuple>& measurements, int sample_count = 5) {
    std::cout << "\n🔢 SAMPLE MEASUREMENTS:" << std::endl;
    std::cout << "─────────────────────────────────────────────────────────────" << std::endl;

    int count = 0;
    for (const auto& measurement : measurements) {
        if (count >= sample_count) break;

        std::cout << "Measurement " << (count + 1) << ":" << std::endl;

        // 🚀 MACRO-DRIVEN: Display all fields automatically
        #define MEASUREMENT_FIELD(name, cpp_type, python_conversion, clickhouse_type) \
            std::cout << "  " << #name << ": " << measurement.name << std::endl;

        #include "cpp/field_defs/measurement_fields.def"
        #undef MEASUREMENT_FIELD

        std::cout << std::endl;
        count++;
    }
}

int main(int argc, char* argv[]) {
    print_banner();

    // Parse command line arguments
    std::string stdf_filepath;
    if (argc > 1) {
        stdf_filepath = argv[1];
    } else {
        std::cout << "Usage: " << argv[0] << " <path_to_stdf_file>" << std::endl;
        std::cout << "Example: " << argv[0] << " STDF_Files/test.stdf" << std::endl;
        return 1;
    }

    std::cout << "📁 Input file: " << stdf_filepath << std::endl;
    std::cout << std::endl;

    try {
        // Overall timing
        auto overall_start = std::chrono::high_resolution_clock::now();

        std::cout << "🔧 Initializing UltraFastProcessor..." << std::endl;

        // Create the ultra-fast processor
        UltraFastProcessor processor;
        processor.set_enable_pixel_filtering(true);  // Enable pixel filtering like the Python version
        processor.set_file_hash("dummy_hash_123");   // 🔥 FIX: Set file hash to avoid expensive calculation!

        std::cout << "✅ Processor initialized" << std::endl;
        std::cout << std::endl;

        // 🚀 Use the SAME UltraFastProcessor that Python script calls!
        // Python line 300: stdf_parser_cpp.process_stdf_with_database_mappings()
        // This should call the EXACT same C++ code that the Python script uses

        std::cout << "🚀 Using SAME UltraFastProcessor that Python script calls..." << std::endl;
        std::cout << "   (This should match the 12.10s processing time from Python)" << std::endl;
        std::cout << std::endl;

        std::vector<MeasurementTuple> measurements;
        double parsing_time = 0.0, processing_time = 0.0;
        size_t total_records = 0;

        {
            PerformanceTimer timer("🚀 UltraFastProcessor (same as Python script)");

            // Setup empty database mappings (like Python script does)
            std::vector<std::pair<std::string, uint32_t>> empty_device_mappings;
            std::vector<std::pair<std::string, uint32_t>> empty_param_mappings;

            // Load empty mappings into processor (like Python bridge function does)
            auto& id_manager = const_cast<FastIDManager&>(processor.get_id_manager());
            id_manager.load_existing_mappings_from_python(empty_device_mappings, empty_param_mappings);

            std::cout << "🔧 Loading 0 device mappings, 0 parameter mappings (same as Python script)" << std::endl;

            // 🚀 Call the NEW ultra-fast function without file hash and segments!
            // This should be even FASTER than the Python version
            measurements = processor.process_stdf_file_measurements(stdf_filepath);

            // Get the same timing statistics that Python gets
            parsing_time = processor.get_parsing_time();
            processing_time = processor.get_processing_time();
            total_records = processor.get_total_records();

            std::cout << "✅ UltraFastProcessor completed: " << measurements.size() << " measurements" << std::endl;
            std::cout << "   📊 Records parsed: " << total_records << std::endl;
            std::cout << "   ⏱️ C++ parsing: " << parsing_time << "s" << std::endl;
            std::cout << "   ⏱️ C++ processing: " << processing_time << "s" << std::endl;
        }

        auto overall_end = std::chrono::high_resolution_clock::now();
        double total_time = std::chrono::duration<double>(overall_end - overall_start).count();

        std::cout << std::endl;

        // Display results
        if (measurements.empty()) {
            std::cout << "⚠️ No measurements extracted from the STDF file." << std::endl;
            std::cout << "   This could mean:" << std::endl;
            std::cout << "   - No pixel tests found (pixel filtering is enabled)" << std::endl;
            std::cout << "   - No PTR/MPR/FTR records in the file" << std::endl;
            std::cout << "   - File parsing issues" << std::endl;
            return 1;
        }

        // Print sample measurements
        print_measurement_sample(measurements, 3);

        // Print ID mappings from processor
        print_processor_statistics(processor, measurements, total_time);

        // Print comprehensive UltraFastProcessor statistics (same as Python gets)
        print_ultrafast_statistics(processor, measurements.size(), total_time);

        std::cout << "\n🎉 SUCCESS: Measurement extraction completed successfully!" << std::endl;
        std::cout << "📊 Total measurements extracted: " << measurements.size() << std::endl;

        return 0;

    } catch (const std::exception& e) {
        std::cout << "\n❌ ERROR: " << e.what() << std::endl;
        return 1;
    } catch (...) {
        std::cout << "\n❌ ERROR: Unknown exception occurred" << std::endl;
        return 1;
    }
}