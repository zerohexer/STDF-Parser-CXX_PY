#include <iostream>
#include <fstream>
#include <string>
#include <cstring>

// libstdf headers
#include "cpp/third_party/include/libstdf.h"

int main() {
    std::cout << "🔍 Standalone C++ libstdf Debug Test" << std::endl;
    std::cout << "====================================" << std::endl;
    
    const char* filepath = "STDF_Files/OSBE25_KEWGBBMD1U_BE_HRG39021_KEWGBBMD1U__Prod_TPP202_03_Agilent_93000MT9510_25C_5215_4_20241017193900.stdf";
    
    std::cout << "Opening STDF file: " << filepath << std::endl;
    
    // Open STDF file with libstdf
    stdf_file* file = stdf_open(const_cast<char*>(filepath));
    if (!file) {
        std::cerr << "❌ Failed to open STDF file with libstdf" << std::endl;
        return 1;
    }
    
    std::cout << "✅ File opened successfully" << std::endl;
    
    int total_records = 0;
    int ptr_records = 0;
    int mpr_records = 0;
    int mir_records = 0;
    int max_records = 100; // Limit for debugging
    
    // Read records using libstdf
    rec_unknown* record;
    while ((record = stdf_read_record(file)) != nullptr && total_records < max_records) {
        total_records++;
        
        if (total_records % 10 == 0) {
            std::cout << "Processing record " << total_records << "..." << std::endl;
        }
        
        try {
            uint8_t rec_typ = record->header.REC_TYP;
            uint8_t rec_sub = record->header.REC_SUB;
            
            std::cout << "Record " << total_records << ": Type=" << (int)rec_typ << ", Sub=" << (int)rec_sub;
            
            // Check specific record types
            if (rec_typ == 15 && rec_sub == 20) { // PTR
                std::cout << " [PTR]";
                ptr_records++;
                
                // Try casting to PTR - THIS MIGHT BE WHERE IT HANGS
                std::cout << " - Attempting cast...";
                rec_ptr* ptr = static_cast<rec_ptr*>(record);
                std::cout << " Cast OK";
                
                // Try accessing basic fields
                std::cout << " - TEST_NUM: " << ptr->TEST_NUM;
                std::cout << " - RESULT: " << ptr->RESULT;
                
                // Try accessing string fields carefully
                if (ptr->TEST_TXT) {
                    std::cout << " - TEST_TXT: [exists]";
                    // Don't print the actual string yet
                }
                if (ptr->ALARM_ID) {
                    std::cout << " - ALARM_ID: [exists]";
                }
                if (ptr->UNITS) {
                    std::cout << " - UNITS: [exists]";
                }
                
            } else if (rec_typ == 15 && rec_sub == 15) { // MPR
                std::cout << " [MPR]";
                mpr_records++;
            } else if (rec_typ == 1 && rec_sub == 10) { // MIR
                std::cout << " [MIR]";
                mir_records++;
            } else {
                std::cout << " [OTHER]";
            }
            
            std::cout << std::endl;
            
        } catch (const std::exception& e) {
            std::cerr << "❌ Exception processing record " << total_records << ": " << e.what() << std::endl;
            break;
        }
        
        stdf_free_record(record);
        
        // Stop at first PTR record to debug
        if (ptr_records >= 1) {
            std::cout << "⏹️  Stopping after first PTR record for debugging" << std::endl;
            break;
        }
    }
    
    stdf_close(file);
    
    std::cout << "\n📊 Summary:" << std::endl;
    std::cout << "Total records processed: " << total_records << std::endl;
    std::cout << "PTR records: " << ptr_records << std::endl;
    std::cout << "MPR records: " << mpr_records << std::endl;
    std::cout << "MIR records: " << mir_records << std::endl;
    
    std::cout << "✅ Debug test completed successfully!" << std::endl;
    return 0;
}