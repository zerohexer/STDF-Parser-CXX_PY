#!/usr/bin/env python3
"""
Debug: Check what raw record types (REC_TYP, REC_SUB) are in the STDF file
Let's create a simple debug version that shows ALL record types found by libstdf
"""

# Let's add some debug prints to the C++ code temporarily
debug_code = '''
// Add this debug code to the main parsing loop in stdf_parser.cpp around line 68

// Debug: Count all record types found by libstdf
static std::map<std::pair<uint8_t, uint8_t>, int> raw_record_counts;
std::pair<uint8_t, uint8_t> rec_pair = std::make_pair(rec_typ, rec_sub);
raw_record_counts[rec_pair]++;

// Every 10000 records, print current counts
if (total_records_ % 10000 == 0) {
    std::cout << "Progress: " << total_records_ << " records processed..." << std::endl;
    std::cout << "Raw record types found so far:" << std::endl;
    for (const auto& entry : raw_record_counts) {
        uint8_t typ = entry.first.first;
        uint8_t sub = entry.first.second;
        int count = entry.second;
        std::cout << "  (" << (int)typ << "," << (int)sub << "): " << count << " records" << std::endl;
    }
}

// At the end, print final counts
if (record == nullptr) {  // End of file
    std::cout << "Final raw record type counts:" << std::endl;
    for (const auto& entry : raw_record_counts) {
        uint8_t typ = entry.first.first;
        uint8_t sub = entry.first.second; 
        int count = entry.second;
        
        // Map to known types
        std::string type_name = "UNKNOWN";
        if (typ == 15 && sub == 20) type_name = "PTR";
        else if (typ == 15 && sub == 15) type_name = "MPR";
        else if (typ == 15 && sub == 25) type_name = "FTR";  // This is what we're looking for!
        else if (typ == 1 && sub == 40) type_name = "HBR";
        else if (typ == 1 && sub == 50) type_name = "SBR";
        else if (typ == 5 && sub == 20) type_name = "PRR";
        else if (typ == 1 && sub == 10) type_name = "MIR";
        
        std::cout << "  (" << (int)typ << "," << (int)sub << ") " << type_name << ": " << count << " records" << std::endl;
    }
}
'''

print("🔍 Debug Plan: Check Raw Record Types")
print("=" * 50)
print("We need to debug what raw (REC_TYP, REC_SUB) pairs libstdf is finding.")
print()
print("The issue might be:")
print("1. ❌ FTR records don't exist in the file (REC_TYP=15, REC_SUB=25)")
print("2. ❌ FTR records have different (REC_TYP, REC_SUB) than we expect")
print("3. ❌ libstdf is not reading FTR records correctly")
print("4. ❌ Our get_record_type() mapping is wrong")
print()
print("Let's check the Python parser's raw data to see what record types it found:")

def analyze_python_results():
    """Check what the Python parser found in the same file"""
    print("\n🐍 Checking Python Parser Raw Data:")
    print("From the previous test_fair_comparison.py results:")
    print("  FTR: 1,060 records <- Python found these!")
    print("  PTR: 1,096 records <- Python found 36 more than C++")
    print()
    print("This confirms FTR records DO exist in the file.")
    print("The problem is our C++ parser isn't finding them.")
    print()
    
    print("🔍 Let's check if the issue is in get_record_type() mapping:")
    print("Current C++ FTR mapping: rec_typ == 15 && rec_sub == 25")
    print()
    
    print("To debug this, we need to:")
    print("1. ✅ Add debug logging to see all (REC_TYP, REC_SUB) pairs found")
    print("2. ✅ Compare with Python's raw data")
    print("3. ✅ Fix the mapping if needed")

if __name__ == "__main__":
    analyze_python_results()
    
    print("\n" + "="*60)
    print("🛠️  SOLUTION: Let's add debug logging to the C++ parser")
    print("="*60)
    print("We need to temporarily modify the C++ code to log raw record types.")
    print("This will show us exactly what libstdf is finding vs what we expect.")