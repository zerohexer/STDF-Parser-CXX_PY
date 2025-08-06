#!/usr/bin/env python3
"""
Simple debug test for C++ parser
"""
import os
import sys
import time

def test_cpp_parser_debug():
    print("🔍 Debug Test: C++ Parser")
    print("=" * 40)
    
    try:
        # Test basic import
        print("Step 1: Testing import...")
        import stdf_parser_cpp
        print("✅ Import successful")
        
        # Test version
        print("Step 2: Testing version...")
        version = stdf_parser_cpp.get_version()
        print(f"✅ Version: {version}")
        
        # Test with small file first (if exists)
        test_files = [
            "STDF_Files/OSBE25_KEWGBBMD1U_BE_HRG39021_KEWGBBMD1U__Prod_TPP202_03_Agilent_93000MT9510_25C_5215_4_20241017193900.stdf"
        ]
        
        for test_file in test_files:
            if os.path.exists(test_file):
                print(f"Step 3: Testing with file: {os.path.basename(test_file)}")
                print("⏳ Starting parsing...")
                
                start_time = time.time()
                try:
                    result = stdf_parser_cpp.parse_stdf_file(test_file)
                    elapsed = time.time() - start_time
                    print(f"✅ Parsing completed in {elapsed:.2f} seconds")
                    
                    if isinstance(result, dict):
                        print(f"📊 Results:")
                        print(f"  Total records: {result.get('total_records', 'unknown')}")
                        print(f"  Parsed records: {result.get('parsed_records', 'unknown')}")
                        records = result.get('records', [])
                        print(f"  Records returned: {len(records)}")
                        
                        # Show first few records
                        if records:
                            print(f"  First record type: {records[0].get('record_type', 'unknown')}")
                    else:
                        print(f"📊 Result type: {type(result)}")
                        if hasattr(result, '__len__'):
                            print(f"  Length: {len(result)}")
                    
                except Exception as e:
                    elapsed = time.time() - start_time
                    print(f"❌ Parsing failed after {elapsed:.2f} seconds")
                    print(f"Error: {e}")
                    import traceback
                    traceback.print_exc()
                
                break
        else:
            print("❌ No test files found")
            
    except ImportError as e:
        print(f"❌ Import failed: {e}")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_cpp_parser_debug()