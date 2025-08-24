#!/usr/bin/env python3
"""
Test Field Extraction - Verify STDF Record Fields
=================================================
This script tests field extraction from different STDF record types
to verify that field definitions in cpp/field_defs/*.def are working correctly.

Usage:
    python test_field_extraction.py --stdf-file path/to/file.stdf [--records-per-type 5]
"""

import os
import sys
import argparse
import platform
from pprint import pprint

# Platform setup for C++ library
system = platform.system().lower()
if system == "linux":
    lib_dir = os.path.join(os.path.dirname(__file__), "cpp", "third_party", "lib")
    current_path = os.environ.get("LD_LIBRARY_PATH", "")
    if lib_dir not in current_path:
        os.environ["LD_LIBRARY_PATH"] = f"{lib_dir}:{current_path}" if current_path else lib_dir

try:
    import stdf_parser_cpp
    print("✅ C++ STDF parser loaded")
except ImportError as e:
    print(f"❌ C++ parser not available: {e}")
    print("Make sure to build the C++ module first: python setup.py build_ext --inplace")
    sys.exit(1)

def test_field_extraction(stdf_file_path, records_per_type=5):
    """
    Test field extraction from STDF file and print sample records
    
    Args:
        stdf_file_path: Path to STDF file
        records_per_type: Number of records to print per record type
    """
    print(f"\n📄 Testing field extraction: {os.path.basename(stdf_file_path)}")
    print("=" * 60)
    
    if not os.path.exists(stdf_file_path):
        print(f"❌ File not found: {stdf_file_path}")
        return False
    
    try:
        # Parse STDF file using C++ parser (like test_all_xmacros_records.cpp)
        print("🔧 Parsing STDF file with C++ parser...")
        result = stdf_parser_cpp.parse_stdf_file(stdf_file_path)
        
        if not result or not isinstance(result, dict):
            print("❌ No data returned from C++ parser")
            return False
        
        # Debug: Print what we actually got back
        print("🔍 Debug - C++ parser result keys:", list(result.keys()))
        
        # The C++ parser returns different structures, let's check all possibilities
        record_types = None
        if 'record_types' in result:
            record_types = result['record_types']
            print("🔍 Debug - record_types keys:", list(record_types.keys()) if record_types else "None")
        elif 'records' in result:
            # Convert from records list to record_types dict (like the C++ test does)
            records = result['records']
            record_types = {}
            for record in records:
                if isinstance(record, dict) and 'type' in record:
                    record_type = record['type']
                    if record_type not in record_types:
                        record_types[record_type] = []
                    record_types[record_type].append(record)
            print("🔍 Debug - converted from records list, found types:", list(record_types.keys()))
        else:
            # Maybe the result IS the records directly
            print("🔍 Debug - Full result structure:")
            pprint(result, depth=2, width=100)
        
        if not record_types:
            print("❌ No record types found in parsed data")
            return False
        
        print(f"✅ Successfully parsed {len(record_types)} record types")
        print()
        
        # Define the record types we're interested in (from cpp/field_defs/)
        target_record_types = ['FTR', 'HBR', 'MPR', 'PRR', 'PTR', 'SBR', 'MIR']
        
        # Show field definition status (like test_all_xmacros_records.cpp does)
        print("🔧 FIELD DEFINITION STATUS:")
        print("-" * 50)
        field_def_files = {
            'PTR': 'cpp/field_defs/ptr_fields.def',
            'MPR': 'cpp/field_defs/mpr_fields.def',
            'FTR': 'cpp/field_defs/ftr_fields.def',
            'HBR': 'cpp/field_defs/hbr_fields.def',
            'SBR': 'cpp/field_defs/sbr_fields.def',
            'PRR': 'cpp/field_defs/prr_fields.def'
        }
        
        for record_type, def_file in field_def_files.items():
            if os.path.exists(def_file):
                try:
                    with open(def_file, 'r') as f:
                        lines = f.readlines()
                    field_count = len([line for line in lines if line.strip() and not line.strip().startswith('//')])
                    print(f"  {record_type:8s}: ✅ {field_count} fields defined in {def_file}")
                except Exception as e:
                    print(f"  {record_type:8s}: ❌ Error reading {def_file}: {e}")
            else:
                print(f"  {record_type:8s}: ⚠️  No .def file found: {def_file}")
        print()
        
        # Create mapping from integer record types to string names
        # Based on cpp/include/stdf_parser.h enum values:
        record_type_names = {
            0: "PTR",   # Parametric Test Record
            1: "MPR",   # Multiple-Result Parametric Record
            2: "FTR",   # Functional Test Record
            3: "HBR",   # Hardware Bin Record
            4: "SBR",   # Software Bin Record
            5: "PRR",   # Part Results Record
            6: "MIR",   # Master Information Record
            7: "UNKNOWN"
        }
        
        # Add additional mappings for record types that might appear
        # (These seem to be from a different enum or processed differently)
        additional_mappings = {
            1: "SDR",   # If this appears, it might be Site Description Record
            2: "WIR",   # If this appears, it might be Wafer Information Record
            3: "WRR",   # If this appears, it might be Wafer Results Record
            4: "PIR"    # If this appears, it might be Part Information Record
        }
        
        # Merge mappings, with original taking precedence
        for k, v in additional_mappings.items():
            if k not in record_type_names:
                record_type_names[k] = v
        
        # Print summary of all record types found
        print("📊 RECORD TYPE SUMMARY:")
        print("-" * 40)
        for record_type, records in record_types.items():
            count = len(records) if isinstance(records, list) else 0
            type_name = record_type_names.get(record_type, f"TYPE_{record_type}")
            print(f"  {type_name:8s} ({record_type:2d}): {count:,} records")
        print()
        
        # Convert integer types to string names for easier processing
        named_record_types = {}
        for record_type, records in record_types.items():
            type_name = record_type_names.get(record_type, f"TYPE_{record_type}")
            named_record_types[type_name] = records
        record_types = named_record_types
        
        # Print detailed field information for each target record type
        for record_type in target_record_types:
            print(f"🔍 TESTING {record_type} RECORD FIELDS:")
            print("=" * 50)
            
            if record_type not in record_types:
                print(f"   ⚠️  No {record_type} records found in file")
                print()
                continue
            
            records = record_types[record_type]
            if not records or not isinstance(records, list):
                print(f"   ⚠️  No valid {record_type} records found")
                print()
                continue
            
            print(f"   📊 Total {record_type} records: {len(records):,}")
            print(f"   🔍 Showing first {min(records_per_type, len(records))} records:")
            print()
            
            # Print sample records
            for i, record in enumerate(records[:records_per_type]):
                print(f"   --- {record_type} Record #{i+1} ---")
                
                # Print record structure
                if isinstance(record, dict):
                    print(f"   📋 Record keys: {list(record.keys())}")
                    
                    # Print fields if they exist
                    fields = record.get('fields', {})
                    if fields:
                        print(f"   📝 Field count: {len(fields)}")
                        print("   🔧 Fields:")
                        for field_name, field_value in fields.items():
                            # Truncate long values for readability
                            if isinstance(field_value, str) and len(field_value) > 50:
                                display_value = field_value[:47] + "..."
                            else:
                                display_value = field_value
                            print(f"      {field_name:20s}: {display_value}")
                    else:
                        print("   ⚠️  No fields found in record")
                        
                    # Print non-field data
                    other_data = {k: v for k, v in record.items() if k != 'fields'}
                    if other_data:
                        print("   📄 Other data:")
                        for key, value in other_data.items():
                            if isinstance(value, str) and len(value) > 50:
                                display_value = value[:47] + "..."
                            else:
                                display_value = value
                            print(f"      {key:20s}: {display_value}")
                else:
                    print(f"   ⚠️  Record is not a dictionary: {type(record)}")
                    print(f"   📄 Raw record: {record}")
                
                print()
            
            # Show field statistics for this record type
            if records:
                all_field_names = set()
                for record in records:
                    if isinstance(record, dict) and 'fields' in record:
                        all_field_names.update(record['fields'].keys())
                
                if all_field_names:
                    print(f"   📈 All unique field names in {record_type} records:")
                    print(f"   {', '.join(sorted(all_field_names))}")
                else:
                    print(f"   ⚠️  No fields found in any {record_type} records")
            
            print()
            print()
        
        # Print overall statistics
        total_records = sum(len(records) if isinstance(records, list) else 0 
                          for records in record_types.values())
        print("📈 OVERALL STATISTICS:")
        print("-" * 40)
        print(f"  Total record types: {len(record_types)}")
        print(f"  Total records: {total_records:,}")
        print(f"  Target record types found: {len([rt for rt in target_record_types if rt in record_types])}/{len(target_record_types)}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error during field extraction test: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main function with command-line interface"""
    parser = argparse.ArgumentParser(description="Test STDF field extraction")
    parser.add_argument("--stdf-file", required=True, help="Path to STDF file")
    parser.add_argument("--records-per-type", type=int, default=5, 
                       help="Number of records to show per type (default: 5)")
    
    args = parser.parse_args()
    
    print("🔧 STDF Field Extraction Test")
    print("=" * 40)
    print(f"Platform: {platform.system()} ({platform.machine()})")
    print()
    
    success = test_field_extraction(args.stdf_file, args.records_per_type)
    
    if success:
        print("✅ Field extraction test completed successfully!")
        print()
        print("💡 Tips:")
        print("  - If fields are missing, check cpp/field_defs/*.def files")
        print("  - After modifying .def files, rebuild: python setup.py build_ext --inplace --force")
        print("  - Use --records-per-type to show more/fewer sample records")
        return 0
    else:
        print("❌ Field extraction test failed!")
        return 1

if __name__ == "__main__":
    sys.exit(main())