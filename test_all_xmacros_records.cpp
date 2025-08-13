#include "cpp/include/stdf_parser.h"
#include <iostream>
#include <set>
#include <algorithm>
#include <cctype>
#include <map>

void test_all_record_types_xmacros() {
    std::cout << "=== X-Macros ALL Record Types Extraction Test ===" << std::endl;
    
    // Parse STDF file
    std::string test_file = "STDF_Files/OSBE25_KEWGBBMD1U_BE_HRG39021_KEWGBBMD1U__Prod_TPP202_03_Agilent_93000MT9510_25C_5215_4_20241017193900.stdf";
    STDFParser parser;
    auto records = parser.parse_file(test_file);
    
    std::cout << "Total records parsed: " << records.size() << std::endl;
    
    // Count records by type
    std::map<STDFRecordType, int> record_counts;
    for (const auto& record : records) {
        record_counts[record.type]++;
    }
    
    std::cout << "\nRecord Type Summary:" << std::endl;
    std::cout << "  PTR: " << record_counts[STDFRecordType::PTR] << std::endl;
    std::cout << "  MPR: " << record_counts[STDFRecordType::MPR] << std::endl;
    std::cout << "  FTR: " << record_counts[STDFRecordType::FTR] << std::endl;
    std::cout << "  HBR: " << record_counts[STDFRecordType::HBR] << std::endl;
    std::cout << "  SBR: " << record_counts[STDFRecordType::SBR] << std::endl;
    std::cout << "  PRR: " << record_counts[STDFRecordType::PRR] << std::endl;
    std::cout << "  MIR: " << record_counts[STDFRecordType::MIR] << std::endl;
    
    // Test each record type
    std::cout << "\nTesting X-Macros for Each Record Type:" << std::endl;
    
    // Test PTR
    std::cout << "\n=== PTR Records ===" << std::endl;
    std::set<std::string> ptr_xmacros_fields;
    #define FIELD(name, member) ptr_xmacros_fields.insert(name);
    #include "cpp/field_defs/ptr_fields.def"
    #undef FIELD
    
    std::cout << "X-Macros fields defined: " << ptr_xmacros_fields.size() << std::endl;
    for (const auto& field : ptr_xmacros_fields) {
        std::cout << "  " << field << std::endl;
    }
    
    int ptr_tested = 0;
    for (const auto& record : records) {
        if (record.type == STDFRecordType::PTR && ptr_tested < 1) {
            std::cout << "Sample PTR fields extracted:" << std::endl;
            for (const auto& field : record.fields) {
                std::cout << "  " << field.first << " = " << field.second << std::endl;
            }
            ptr_tested++;
        }
    }
    
    // Test MPR
    std::cout << "\n=== MPR Records ===" << std::endl;
    std::cout << "MPR .def file status: ";
    
    // Check if MPR fields are defined
    try {
        std::set<std::string> mpr_xmacros_fields;
        #define FIELD(name, member) mpr_xmacros_fields.insert(name);
        #include "cpp/field_defs/mpr_fields.def"
        #undef FIELD
        
        std::cout << "OK " << mpr_xmacros_fields.size() << " fields defined" << std::endl;
        for (const auto& field : mpr_xmacros_fields) {
            std::cout << "  - " << field << std::endl;
        }
    } catch (...) {
        std::cout << "ERROR MPR .def file has issues" << std::endl;
    }
    
    int mpr_tested = 0;
    for (const auto& record : records) {
        if (record.type == STDFRecordType::MPR && mpr_tested < 1) {
            std::cout << "Sample MPR fields extracted:" << std::endl;
            for (const auto& field : record.fields) {
                std::cout << "  " << field.first << " = " << field.second << std::endl;
            }
            mpr_tested++;
        }
    }
    
    // Test FTR
    std::cout << "\n=== FTR Records ===" << std::endl;
    std::cout << "FTR .def file status: ";
    
    try {
        std::set<std::string> ftr_xmacros_fields;
        #define FIELD(name, member) ftr_xmacros_fields.insert(name);
        #include "cpp/field_defs/ftr_fields.def"
        #undef FIELD
        
        std::cout << "OK " << ftr_xmacros_fields.size() << " fields defined" << std::endl;
        for (const auto& field : ftr_xmacros_fields) {
            std::cout << "  - " << field << std::endl;
        }
    } catch (...) {
        std::cout << "ERROR FTR .def file has issues" << std::endl;
    }
    
    int ftr_tested = 0;
    for (const auto& record : records) {
        if (record.type == STDFRecordType::FTR && ftr_tested < 1) {
            std::cout << "Sample FTR fields extracted:" << std::endl;
            for (const auto& field : record.fields) {
                std::cout << "  " << field.first << " = " << field.second << std::endl;
            }
            ftr_tested++;
        }
    }
    
    // Test HBR
    std::cout << "\n=== HBR Records ===" << std::endl;
    std::cout << "HBR .def file status: ";
    
    try {
        std::set<std::string> hbr_xmacros_fields;
        #define FIELD(name, member) hbr_xmacros_fields.insert(name);
        #include "cpp/field_defs/hbr_fields.def"
        #undef FIELD
        
        std::cout << "OK " << hbr_xmacros_fields.size() << " fields defined" << std::endl;
        for (const auto& field : hbr_xmacros_fields) {
            std::cout << "  - " << field << std::endl;
        }
    } catch (...) {
        std::cout << "ERROR HBR .def file has issues" << std::endl;
    }
    
    int hbr_tested = 0;
    for (const auto& record : records) {
        if (record.type == STDFRecordType::HBR && hbr_tested < 1) {
            std::cout << "Sample HBR fields extracted:" << std::endl;
            for (const auto& field : record.fields) {
                std::cout << "  " << field.first << " = " << field.second << std::endl;
            }
            hbr_tested++;
        }
    }
    
    // Test SBR
    std::cout << "\n=== SBR Records ===" << std::endl;
    std::cout << "SBR .def file status: ";
    
    try {
        std::set<std::string> sbr_xmacros_fields;
        #define FIELD(name, member) sbr_xmacros_fields.insert(name);
        #include "cpp/field_defs/sbr_fields.def"
        #undef FIELD
        
        std::cout << "OK " << sbr_xmacros_fields.size() << " fields defined" << std::endl;
        for (const auto& field : sbr_xmacros_fields) {
            std::cout << "  - " << field << std::endl;
        }
    } catch (...) {
        std::cout << "ERROR SBR .def file has issues" << std::endl;
    }
    
    int sbr_tested = 0;
    for (const auto& record : records) {
        if (record.type == STDFRecordType::SBR && sbr_tested < 1) {
            std::cout << "Sample SBR fields extracted:" << std::endl;
            for (const auto& field : record.fields) {
                std::cout << "  " << field.first << " = " << field.second << std::endl;
            }
            sbr_tested++;
        }
    }
    
    // Test PRR
    std::cout << "\n=== PRR Records ===" << std::endl;
    std::cout << "PRR .def file status: ";
    
    try {
        std::set<std::string> prr_xmacros_fields;
        #define FIELD(name, member) prr_xmacros_fields.insert(name);
        #include "cpp/field_defs/prr_fields.def"
        #undef FIELD
        
        std::cout << "OK " << prr_xmacros_fields.size() << " fields defined" << std::endl;
        for (const auto& field : prr_xmacros_fields) {
            std::cout << "  - " << field << std::endl;
        }
    } catch (...) {
        std::cout << "ERROR PRR .def file has issues" << std::endl;
    }
    
    int prr_tested = 0;
    for (const auto& record : records) {
        if (record.type == STDFRecordType::PRR && prr_tested < 1) {
            std::cout << "Sample PRR fields extracted:" << std::endl;
            for (const auto& field : record.fields) {
                std::cout << "  " << field.first << " = " << field.second << std::endl;
            }
            prr_tested++;
        }
    }
    
    // Count actual fields from other record types
    std::set<std::string> mpr_count, ftr_count, hbr_count, sbr_count, prr_count;
    
    #define FIELD(name, member) mpr_count.insert(name);
    #include "cpp/field_defs/mpr_fields.def"
    #undef FIELD
    
    #define FIELD(name, member) ftr_count.insert(name);
    #include "cpp/field_defs/ftr_fields.def"
    #undef FIELD
    
    #define FIELD(name, member) hbr_count.insert(name);
    #include "cpp/field_defs/hbr_fields.def"
    #undef FIELD
    
    #define FIELD(name, member) sbr_count.insert(name);
    #include "cpp/field_defs/sbr_fields.def"
    #undef FIELD
    
    #define FIELD(name, member) prr_count.insert(name);
    #include "cpp/field_defs/prr_fields.def"
    #undef FIELD
    
    // Summary
    std::cout << "\nX-Macros Field Count:" << std::endl;
    std::cout << "  PTR: " << ptr_xmacros_fields.size() << " fields" << std::endl;
    std::cout << "  MPR: " << mpr_count.size() << " fields" << std::endl;
    std::cout << "  FTR: " << ftr_count.size() << " fields" << std::endl;
    std::cout << "  HBR: " << hbr_count.size() << " fields" << std::endl;
    std::cout << "  SBR: " << sbr_count.size() << " fields" << std::endl;
    std::cout << "  PRR: " << prr_count.size() << " fields" << std::endl;
}

int main() {
    test_all_record_types_xmacros();
    return 0;
}