#include <iostream>
#include <cstring>
#include <algorithm>
#include "cpp/third_party/include/libstdf.h"

void debug_ptr_record(rec_unknown* rec) {
    if (!rec) {
        printf("ERROR: rec is NULL\n");
        return;
    }
    
    printf("\n=== PTR Record Debug ===\n");
    printf("REC_TYP: %d, REC_SUB: %d\n", rec->header.REC_TYP, rec->header.REC_SUB);
    printf("REC_LEN: %d bytes\n", rec->header.REC_LEN);
    printf("State: %d (0=RAW, 1=PARSED)\n", rec->header.state);
    printf("Data pointer: %p\n", rec->data);
    
    if (!rec->data) {
        printf("ERROR: Data pointer is NULL\n");
        return;
    }
    
    uint8_t* raw_data = static_cast<uint8_t*>(rec->data);
    
    // Test memory access
    printf("Testing memory access...\n");
    printf("First byte: 0x%02X\n", raw_data[0]);
    
    // Print first 16 bytes
    printf("Raw bytes (first 16): ");
    int bytes_to_show = std::min(16, (int)rec->header.REC_LEN);
    for (int i = 0; i < bytes_to_show; i++) {
        printf("%02X ", raw_data[i]);
        if (i == 7) printf("| ");
    }
    printf("\n");
    
    // Try to parse according to STDF PTR spec:
    // TEST_NUM (U4) - 4 bytes
    // HEAD_NUM (U1) - 1 byte  
    // SITE_NUM (U1) - 1 byte
    // TEST_FLG (B1) - 1 byte ← TARGET!
    // PARM_FLG (B1) - 1 byte
    // RESULT (R4) - 4 bytes
    
    if (rec->header.REC_LEN >= 8) {
        printf("\nParsing fields:\n");
        
        uint32_t test_num = *reinterpret_cast<uint32_t*>(raw_data + 0);
        uint8_t head_num = raw_data[4];
        uint8_t site_num = raw_data[5];
        uint8_t test_flg = raw_data[6];  // ← This is what we want!
        uint8_t parm_flg = raw_data[7];
        
        printf("  TEST_NUM: %u\n", test_num);
        printf("  HEAD_NUM: %d\n", head_num);
        printf("  SITE_NUM: %d\n", site_num);
        printf("  TEST_FLG: %d ← TARGET FIELD!\n", test_flg);
        printf("  PARM_FLG: %d\n", parm_flg);
        
        if (rec->header.REC_LEN >= 12) {
            float result = *reinterpret_cast<float*>(raw_data + 8);
            printf("  RESULT: %.6f\n", result);
        }
    } else {
        printf("Record too short for field parsing\n");
    }
}

int main() {
    printf("🔍 Direct C++ libstdf Binary Parsing Test\n");
    printf("=========================================\n");
    
    const char* filename = "STDF_Files/OSBE25_KEWGBBMD1U_BE_HRG39021_KEWGBBMD1U__Prod_TPP202_03_Agilent_93000MT9510_25C_5215_4_20241017193900.stdf";
    
    printf("Opening STDF file: %s\n", filename);
    
    stdf_file* file = stdf_open(const_cast<char*>(filename));
    if (!file) {
        printf("❌ Failed to open STDF file\n");
        return 1;
    }
    
    printf("✅ File opened successfully\n");
    
    rec_unknown* record;
    int total_records = 0;
    int ptr_records = 0;
    
    printf("\n🔄 Reading records...\n");
    
    while ((record = stdf_read_record(file)) != nullptr && ptr_records < 3) {
        total_records++;
        
        // Look for PTR records
        if (record->header.REC_TYP == 15 && record->header.REC_SUB == 10) {
            ptr_records++;
            printf("\n📍 Found PTR record #%d (total records: %d)\n", ptr_records, total_records);
            debug_ptr_record(record);
        }
        
        stdf_free_record(record);
        
        if (total_records % 1000 == 0) {
            printf("Processed %d records...\n", total_records);
        }
    }
    
    printf("\n✅ Test completed!\n");
    printf("Total records processed: %d\n", total_records);
    printf("PTR records found: %d\n", ptr_records);
    
    stdf_close(file);
    return 0;
}