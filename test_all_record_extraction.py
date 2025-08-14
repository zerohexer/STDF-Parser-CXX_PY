#!/usr/bin/env python3
"""
Test all record types - Check if dynamic field extraction is working for all record types
"""

import os

def main():
    try:
        import stdf_parser_cpp
        print("✅ C++ Extension loaded")
        
        # Find STDF file
        stdf_files = [f for f in os.listdir("STDF_Files") if f.endswith('.stdf')]
        test_file = os.path.join("STDF_Files", stdf_files[0])
        
        print(f"📁 Testing: {os.path.basename(test_file)}")
        
        # Parse and get all records
        result = stdf_parser_cpp.parse_stdf_file(test_file)
        records = result.get('records', [])
        
        # Group records by type
        record_groups = {}
        for record in records:
            record_type = record.get('record_type', 'UNKNOWN')
            if record_type not in record_groups:
                record_groups[record_type] = []
            record_groups[record_type].append(record)
        
        print(f"\n📊 Record Types Found: {list(record_groups.keys())}")
        
        # Test each record type that has X-Macros
        target_types = ['PTR', 'MPR', 'FTR', 'HBR', 'SBR', 'PRR']
        
        for record_type in target_types:
            if record_type in record_groups:
                records_of_type = record_groups[record_type]
                first_record = records_of_type[0]
                fields = first_record.get('fields', {})
                
                print(f"\n{'='*50}")
                print(f"🔍 {record_type} RECORD ANALYSIS")
                print(f"{'='*50}")
                print(f"  Total {record_type} records: {len(records_of_type)}")
                print(f"  Fields in first record: {len(fields)}")
                
                # Show key fields specific to each record type
                if record_type in ['PTR', 'MPR', 'FTR']:
                    # Test records have TEST_NUM and TEST_FLG
                    key_numeric = ['TEST_NUM', 'HEAD_NUM', 'SITE_NUM', 'TEST_FLG']
                elif record_type == 'HBR':
                    # Hardware Bin Record fields
                    key_numeric = ['HEAD_NUM', 'SITE_NUM', 'HBIN_NUM', 'HBIN_CNT']
                elif record_type == 'SBR':
                    # Software Bin Record fields  
                    key_numeric = ['HEAD_NUM', 'SITE_NUM', 'SBIN_NUM', 'SBIN_CNT']
                elif record_type == 'PRR':
                    # Part Result Record fields
                    key_numeric = ['HEAD_NUM', 'SITE_NUM', 'NUM_TEST', 'HARD_BIN']
                else:
                    key_numeric = ['HEAD_NUM', 'SITE_NUM']
                
                print(f"  📋 Key numeric fields:")
                for field in key_numeric:
                    value = fields.get(field, 'NOT_FOUND')
                    status = "✅" if value != 'NOT_FOUND' else "❌"
                    print(f"    {field:<12} = '{value}' {status}")
                
                # Look for string fields
                string_candidates = []
                for field_name, value in fields.items():
                    # Check if it's a string field with actual text content
                    if (isinstance(value, str) and len(value) > 1 and 
                        not value.isdigit() and value not in ['0', '0.000000', 'NOT_FOUND'] and
                        field_name.upper() in ['TEST_TXT', 'ALARM_ID', 'UNITS', 'VECT_NAM', 'TIME_SET', 
                                              'HBIN_NAM', 'SBIN_NAM', 'PART_ID', 'PART_TXT']):
                        string_candidates.append((field_name, value))
                
                if string_candidates:
                    print(f"  🎯 String fields found:")
                    for field_name, value in string_candidates[:5]:  # Show first 5
                        print(f"    {field_name:<12} = '{value}' ✅")
                else:
                    print(f"  ❌ No meaningful string fields found")
                
                # Show field count comparison
                expected_counts = {
                    'PTR': 20, 'MPR': 7, 'FTR': 7, 'HBR': 5, 'SBR': 5, 'PRR': 8
                }
                expected = expected_counts.get(record_type, 0)
                if expected > 0:
                    x_macro_fields = len([f for f in fields.keys() if f.upper() == f or '_' in f])
                    print(f"  📈 X-Macros extraction: {x_macro_fields} fields (expected ~{expected})")
                    if x_macro_fields >= expected * 0.8:  # At least 80% of expected
                        print(f"    ✅ Good extraction rate")
                    else:
                        print(f"    ⚠️ Might be missing some fields")
            else:
                print(f"\n❌ {record_type} records not found in STDF file")
        
        print(f"\n{'='*50}")
        print("🎯 SUMMARY")
        print(f"{'='*50}")
        total_records = sum(len(records) for records in record_groups.values())
        print(f"  Total records parsed: {total_records:,}")
        print(f"  Record types with X-Macros: {len([t for t in target_types if t in record_groups])}/6")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()