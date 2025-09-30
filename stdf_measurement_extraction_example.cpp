#include <iostream>
#include <chrono>
#include <vector>
#include <string>
#include <fstream>
#include <future>
#include <windows.h>
#include "cpp/include/ultra_fast_processor.h"

// Process a single STDF file (for parallel execution)
std::pair<size_t, double> process_single_file(const std::string& filepath) {
    auto start = std::chrono::high_resolution_clock::now();
    UltraFastProcessor processor;
    auto measurements = processor.process_stdf_file_measurements(filepath);
    auto end = std::chrono::high_resolution_clock::now();

    double time = std::chrono::duration<double>(end - start).count();
    return {measurements.size(), time};
}

int main(int argc, char* argv[]) {
    if (argc < 2) {
        std::cout << "Usage: " << argv[0] << " <stdf_file_or_directory>" << std::endl;
        return 1;
    }

    std::vector<std::string> files;
    std::string input_path = argv[1];

    // Check if it's a directory first using Windows API
    DWORD fileAttrib = GetFileAttributes(input_path.c_str());
    if (fileAttrib != INVALID_FILE_ATTRIBUTES && (fileAttrib & FILE_ATTRIBUTE_DIRECTORY)) {
        // It's a directory - scan for STDF files
        std::cout << "Directory mode - scanning for .stdf files..." << std::endl;
        WIN32_FIND_DATA findFileData;
        std::string searchPath = input_path + "\\*.stdf";

        HANDLE hFind = FindFirstFile(searchPath.c_str(), &findFileData);
        if (hFind != INVALID_HANDLE_VALUE) {
            do {
                if (!(findFileData.dwFileAttributes & FILE_ATTRIBUTE_DIRECTORY)) {
                    files.push_back(input_path + "\\" + findFileData.cFileName);
                }
            } while (FindNextFile(hFind, &findFileData) != 0);
            FindClose(hFind);
        }
    }
    else {
        // It's a single file
        files.push_back(input_path);
        std::cout << "Single file mode" << std::endl;
    }

    if (files.empty()) {
        std::cout << "No STDF files found!" << std::endl;
        return 1;
    }

    std::cout << "Processing " << files.size() << " file(s)..." << std::endl;

    auto start = std::chrono::high_resolution_clock::now();
    size_t total_measurements = 0;

    if (files.size() == 1) {
        // Single file - process directly (no parallel overhead)
        UltraFastProcessor processor;
        auto measurements = processor.process_stdf_file_measurements(files[0]);
        total_measurements = measurements.size();
        std::cout << "File: " << measurements.size() << " measurements" << std::endl;
    } else {
        // Multiple files - process with limited parallelism to avoid memory issues
        const size_t MAX_PARALLEL = 5; // Process max 3 files at once to avoid memory exhaustion
        std::cout << "Processing " << files.size() << " files with " << MAX_PARALLEL << " parallel threads..." << std::endl;

        std::vector<std::pair<size_t, double>> results(files.size());
        double max_file_time = 0.0;

        // Process files in batches
        for (size_t batch_start = 0; batch_start < files.size(); batch_start += MAX_PARALLEL) {
            size_t batch_end = std::min(batch_start + MAX_PARALLEL, files.size());
            std::vector<std::future<std::pair<size_t, double>>> batch_futures;

            std::cout << "Batch " << (batch_start / MAX_PARALLEL + 1) << ": Processing files "
                      << (batch_start + 1) << "-" << batch_end << "..." << std::endl;

            // Start batch
            for (size_t i = batch_start; i < batch_end; ++i) {
                batch_futures.push_back(std::async(std::launch::async, process_single_file, files[i]));
            }

            // Collect batch results
            for (size_t i = 0; i < batch_futures.size(); ++i) {
                auto [measurements, file_time] = batch_futures[i].get();
                results[batch_start + i] = {measurements, file_time};
                total_measurements += measurements;
                max_file_time = std::max(max_file_time, file_time);

                // Extract filename for display
                size_t pos = files[batch_start + i].find_last_of("/\\");
                std::string filename = (pos == std::string::npos) ? files[batch_start + i] : files[batch_start + i].substr(pos + 1);

                std::cout << filename << ": " << measurements << " measurements (" << file_time << "s)" << std::endl;
            }
        }

        auto end_parallel = std::chrono::high_resolution_clock::now();
        double parallel_time = std::chrono::duration<double>(end_parallel - start).count();
        double speedup = (max_file_time * files.size()) / parallel_time;

        std::cout << "Speedup: " << speedup << "x" << std::endl;
    }

    auto end = std::chrono::high_resolution_clock::now();
    double total_time = std::chrono::duration<double>(end - start).count();

    std::cout << "Total: " << total_measurements << " measurements in " << total_time << "s" << std::endl;
    return 0;
}