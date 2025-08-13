#!/usr/bin/env python3
"""
Test script for the STDF C++ parser with cross-platform library loading
"""

# Setup library paths before importing the extension
import sys
import os

# For Linux/WSL - set LD_LIBRARY_PATH
lib_dir = os.path.join(os.path.dirname(__file__), "cpp", "third_party", "lib")
current_path = os.environ.get("LD_LIBRARY_PATH", "")
if lib_dir not in current_path:
    os.environ["LD_LIBRARY_PATH"] = f"{lib_dir}:{current_path}" if current_path else lib_dir

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'python'))

# Now import the C++ extension
try:
    import stdf_parser_cpp
    print(" Extension loaded successfully")
    print(f"Version: {stdf_parser_cpp.get_version()}")
except ImportError as e:
    print(f" Failed to load extension: {e}")
    sys.exit(1)

def test_with_file(filepath):
    """Test parsing a single STDF file"""
    if not os.path.exists(filepath):
        print(f" File not found: {filepath}")
        return False
        
    try:
        print(f"\n Testing with: {os.path.basename(filepath)}")
        result = stdf_parser_cpp.parse_stdf_file(filepath)
        
        if isinstance(result, dict):
            records = result.get('records', [])
            total = result.get('total_records', 0)
            parsed = result.get('parsed_records', 0)
            
            print(f" Successfully parsed {len(records)} records")
            print(f"  Total records in file: {total}")
            print(f"  Records parsed: {parsed}")
            
            # Show first few records
            if records:
                print("\n Sample records:")
                for i, record in enumerate(records[:3]):
                    record_type = record.get('record_type', 'UNKNOWN')
                    test_num = record.get('test_num', 'N/A')
                    print(f"  {i+1}. {record_type} - Test #{test_num}")
                    
                    # Show some fields
                    fields = record.get('fields', {})
                    if fields:
                        sample_fields = list(fields.items())[:3]
                        for key, value in sample_fields:
                            print(f"     {key}: {value}")
            
            return True
        else:
            print(f" Unexpected result type: {type(result)}")
            return False
            
    except Exception as e:
        print(f" Error parsing file: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    # Test with STDF files
    stdf_dir = "STDF_Files"
    if os.path.exists(stdf_dir):
        stdf_files = [f for f in os.listdir(stdf_dir) if f.endswith('.stdf')]
        if stdf_files:
            # Test with first file
            test_file = os.path.join(stdf_dir, stdf_files[0])
            success = test_with_file(test_file)
            
            if success:
                print(f"\n Parser test completed successfully!")
            else:
                print(f"\n Parser test failed!")
                sys.exit(1)
        else:
            print("No .stdf files found in STDF_Files directory")
    else:
        print("STDF_Files directory not found")