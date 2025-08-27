#!/usr/bin/env python3
"""
Debug: Check what record types our C++ parser is actually finding
Uses pystdf to get expected record counts dynamically instead of hardcoded values
"""
import os
import sys
import time
from io import StringIO
import pystdf.V4 as v4
from pystdf.IO import Parser
from pystdf.Writers import TextWriter

def get_pystdf_record_counts(file_path):
    """
    Get expected record counts using pystdf (Python reference implementation)
    """
    if not os.path.exists(file_path):
        print(f"❌ File not found: {file_path}")
        return {}
    
    print(f"🐍 Getting reference counts using pystdf...")
    
    try:
        # Parse STDF file using pystdf
        with open(file_path, 'rb') as f_in:
            p = Parser(inp=f_in)
            captured_std_out = StringIO()
            p.addSink(TextWriter(captured_std_out))
            p.parse()
            atdf_output = captured_std_out.getvalue()
        
        # Split into lines and count record types
        atdf_lines = atdf_output.split('\n')
        print(f"  Total ATDF lines: {len(atdf_lines)}")
        
        # Count records by type
        record_counts = {}
        
        # Get all available record types from pystdf
        for record_type in v4.records:
            record_name = record_type.name.split('.')[-1].upper()
            
            # Count lines that start with this record type
            count = sum(1 for line in atdf_lines if line.startswith(record_name + '|'))
            
            if count > 0:
                record_counts[record_name] = count
        
        print(f"  Found {len(record_counts)} record types")
        return record_counts
        
    except Exception as e:
        print(f"❌ Error parsing with pystdf: {e}")
        import traceback
        traceback.print_exc()
        return {}

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
        
        # Get Python reference counts first
        expected_counts = get_pystdf_record_counts(test_file)
        
        if not expected_counts:
            print("❌ Failed to get Python reference counts")
            return
        
        # Parse with C++
        print(f"🚀 Parsing with C++ implementation...")
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
            
            print(f"\n🔍 Comparison with Python pystdf Results:")
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
                print(f"\n🤔 Unexpected Record Types Found in C++:")
                for rec_type in sorted(unexpected):
                    count = record_counts[rec_type]
                    print(f"  {rec_type}: {count:,} records")
            
            # Find any missing record types
            missing = set(expected_counts.keys()) - set(record_counts.keys())
            if missing:
                print(f"\n❌ Record Types Missing in C++:")
                for rec_type in sorted(missing):
                    count = expected_counts[rec_type]
                    print(f"  {rec_type}: {count:,} records (found in Python)")
            
            # Summary
            total_cpp = sum(record_counts.values())
            total_python = sum(expected_counts.values())
            print(f"\n📊 Summary:")
            print(f"  C++ total records: {total_cpp:,}")
            print(f"  Python total records: {total_python:,}")
            print(f"  Difference: {total_cpp - total_python:+,}")
            
            # Success rate
            matches = 0
            for rec_type in expected_counts:
                if record_counts.get(rec_type, 0) == expected_counts[rec_type]:
                    matches += 1
            
            success_rate = (matches / len(expected_counts)) * 100 if expected_counts else 0
            print(f"  Exact match rate: {success_rate:.1f}% ({matches}/{len(expected_counts)})")
            
        else:
            print("❌ Invalid result format from C++ parser")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_cpp_record_types()