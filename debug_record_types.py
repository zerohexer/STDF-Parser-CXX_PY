#!/usr/bin/env python3
"""
Debug: Check what record types our C++ parser is actually finding
"""
import os
import sys
import time

def test_cpp_record_types():
    """Test which record types the C++ parser is finding"""
    print("🔍 C++ Parser Record Type Debug")
    print("=" * 50)
    
    try:
        import stdf_parser_cpp
        
        test_file = "STDF_Files/OSBE25_KEWGBBMD1U_BE_HRG39021_KEWGBBMD1U__Prod_TPP202_03_Agilent_93000MT9510_25C_5215_4_20241017193900.stdf"
        
        if not os.path.exists(test_file):
            print(f"❌ Test file not found: {test_file}")
            return
            
        print(f"📁 Testing file: {os.path.basename(test_file)}")
        
        # Parse with C++
        start_time = time.time()
        result = stdf_parser_cpp.parse_stdf_file(test_file)
        end_time = time.time()
        
        parse_time = end_time - start_time
        
        if isinstance(result, dict) and 'records' in result:
            records = result['records']
            
            # Count record types
            record_counts = {}
            for record in records:
                rec_type = record.get('record_type', 'UNKNOWN')
                record_counts[rec_type] = record_counts.get(rec_type, 0) + 1
            
            print(f"\n📊 C++ Parser Record Types Found:")
            print(f"  Total records parsed: {len(records):,}")
            print(f"  Parse time: {parse_time:.2f} seconds")
            
            # Show counts in descending order
            for rec_type in sorted(record_counts.keys(), key=lambda x: record_counts[x], reverse=True):
                count = record_counts[rec_type]
                print(f"  {rec_type}: {count:,} records")
            
            # Compare with expected Python counts
            expected_counts = {
                'MPR': 92772,
                'PTR': 1096,  # Python found 1096
                'FTR': 1060,  # Python found 1060, C++ found 0
                'HBR': 5,
                'SBR': 5,
                'PRR': 4,
                'MIR': 1
            }
            
            print(f"\n🔍 Comparison with Python Results:")
            print(f"{'Type':<6} {'C++':<8} {'Python':<8} {'Diff':<8} {'Status'}")
            print("-" * 40)
            
            for rec_type in sorted(expected_counts.keys()):
                cpp_count = record_counts.get(rec_type, 0)
                python_count = expected_counts[rec_type]
                diff = cpp_count - python_count
                
                if diff == 0:
                    status = "✅"
                elif abs(diff) < 100:
                    status = "⚠️"
                else:
                    status = "❌"
                
                print(f"{rec_type:<6} {cpp_count:<8,} {python_count:<8,} {diff:<+8,} {status}")
            
            # Find any unexpected record types
            unexpected = set(record_counts.keys()) - set(expected_counts.keys())
            if unexpected:
                print(f"\n🤔 Unexpected Record Types Found:")
                for rec_type in sorted(unexpected):
                    count = record_counts[rec_type]
                    print(f"  {rec_type}: {count:,} records")
            
        else:
            print("❌ Invalid result format from C++ parser")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_cpp_record_types()