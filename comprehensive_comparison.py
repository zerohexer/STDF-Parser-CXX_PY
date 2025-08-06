#!/usr/bin/env python3
"""
Comprehensive STDF Parser Comparison: Python vs C++
Side-by-side performance and accuracy testing
"""
import os
import sys
import time
from io import StringIO
import pystdf.V4 as v4
from pystdf.IO import Parser
from pystdf.Writers import TextWriter

def test_python_parser(file_path):
    """Test Python pystdf parser with same record types as C++ parser"""
    print("🐍 Testing Python Parser (pystdf)")
    print("=" * 50)
    
    if not os.path.exists(file_path):
        print(f"❌ File not found: {file_path}")
        return None
        
    filename = os.path.basename(file_path)
    print(f"📁 File: {filename}")
    
    # C++ parser record types (same as our fixed C++ parser)
    cpp_record_types = ['MIR', 'PTR', 'MPR', 'FTR', 'HBR', 'SBR', 'PRR']
    print(f"🎯 Target record types: {cpp_record_types}")
    
    try:
        # Step 1: Parse STDF binary to text
        print(f"🔄 Step 1: Parsing STDF binary to text...")
        step1_start = time.time()
        
        with open(file_path, 'rb') as f_in:
            p = Parser(inp=f_in)
            captured_std_out = StringIO()
            p.addSink(TextWriter(captured_std_out))
            p.parse()
            atdf = captured_std_out.getvalue()
        
        step1_end = time.time()
        step1_time = step1_end - step1_start
        print(f"✅ Binary parsing: {step1_time:.2f}s")
        
        # Step 2: Convert text to records (ONLY C++ types)
        print(f"🔄 Step 2: Converting to records...")
        step2_start = time.time()
        
        atdf_lines = atdf.split('\n')
        print(f"📝 Raw lines: {len(atdf_lines):,}")
        
        # Debug: Check first few lines
        print(f"🔍 Debug - First 5 lines of ATDF:")
        for i, line in enumerate(atdf_lines[:5]):
            print(f"  Line {i}: {line[:100]}..." if len(line) > 100 else f"  Line {i}: {line}")
        
        # Add line numbers and filename
        for n, line in enumerate(atdf_lines):
            if len(line) >= 4:
                atdf_lines[n] = line[:4] + str(n) + '|' + filename + '|' + line[4:]
        
        # Parse ONLY C++ supported record types
        raw_records = {}
        total_parsed_records = 0
        
        # First, try to find records using pystdf.V4.records
        for record_type in v4.records:
            record_name = record_type.name.split('.')[-1].upper()
            if record_name in cpp_record_types:
                curr = [line for line in atdf_lines if line.startswith(record_name)]
                if curr:
                    raw_records[record_name] = []
                    header_names = list(list(zip(*record_type.fieldMap))[0])
                    for line in curr:
                        fields = line.split('|')
                        if len(fields) > 2:
                            record_data = dict(zip(header_names, fields[2:]))
                            raw_records[record_name].append(record_data)
                            total_parsed_records += 1
        
        # Additionally, search for any missing record types directly in the text
        # This handles cases where pystdf might not have all record types defined
        for record_name in cpp_record_types:
            if record_name not in raw_records:
                curr = [line for line in atdf_lines if line.startswith(record_name)]
                if curr:
                    raw_records[record_name] = []
                    for line in curr:
                        fields = line.split('|')
                        if len(fields) > 2:
                            # Create a basic record with available fields
                            record_data = {'raw_line': line}
                            raw_records[record_name].append(record_data)
                            total_parsed_records += 1
                    print(f"🔍 Found {len(curr)} {record_name} records not in pystdf.V4.records")
        
        step2_end = time.time()
        step2_time = step2_end - step2_start
        print(f"✅ Text to records: {step2_time:.2f}s")
        
        total_time = step1_time + step2_time
        
        print(f"\\n📊 Python Results:")
        for record_type in sorted(raw_records.keys(), key=lambda x: len(raw_records[x]), reverse=True):
            count = len(raw_records[record_type])
            if count > 0:
                print(f"  {record_type}: {count:,} records")
        
        print(f"\\n📈 Python Performance:")
        print(f"  Total records: {total_parsed_records:,}")
        print(f"  Parse time: {total_time:.2f}s")
        print(f"  Records/sec: {total_parsed_records/total_time:,.0f}")
        
        return {
            'parser': 'Python (pystdf)',
            'total_records': total_parsed_records,
            'parse_time': total_time,
            'records_per_second': total_parsed_records/total_time,
            'record_types': {k: len(v) for k, v in raw_records.items()},
            'step1_time': step1_time,
            'step2_time': step2_time
        }
        
    except Exception as e:
        print(f"❌ Python parser failed: {e}")
        import traceback
        traceback.print_exc()
        return None

def test_cpp_parser(file_path):
    """Test C++ libstdf parser"""
    print("\\n🚀 Testing C++ Parser (libstdf)")
    print("=" * 50)
    
    try:
        import stdf_parser_cpp
        
        filename = os.path.basename(file_path)
        print(f"📁 File: {filename}")
        
        print(f"🔄 Parsing with C++ parser...")
        start_time = time.time()
        result = stdf_parser_cpp.parse_stdf_file(file_path)
        end_time = time.time()
        
        cpp_time = end_time - start_time
        
        if isinstance(result, dict):
            total_records = result.get('total_records', 0)
            parsed_records = result.get('parsed_records', 0)
            records = result.get('records', [])
            
            # Count record types
            record_types = {}
            for record in records:
                rec_type = record.get('record_type', 'UNKNOWN')
                record_types[rec_type] = record_types.get(rec_type, 0) + 1
            
            print(f"\\n📊 C++ Results:")
            for rec_type in sorted(record_types.keys(), key=lambda x: record_types[x], reverse=True):
                count = record_types[rec_type]
                if count > 0:
                    print(f"  {rec_type}: {count:,} records")
            
            print(f"\\n📈 C++ Performance:")
            print(f"  Total records: {parsed_records:,}")
            print(f"  Parse time: {cpp_time:.2f}s")
            print(f"  Records/sec: {parsed_records/cpp_time:,.0f}")
            
            return {
                'parser': 'C++ (libstdf)',
                'total_records': parsed_records,
                'parse_time': cpp_time,
                'records_per_second': parsed_records/cpp_time,
                'record_types': record_types,
                'raw_total': total_records
            }
            
    except ImportError:
        print("❌ C++ parser not available (stdf_parser_cpp not found)")
        return None
    except Exception as e:
        print(f"❌ C++ parser failed: {e}")
        import traceback
        traceback.print_exc()
        return None

def compare_results(python_result, cpp_result):
    """Compare Python vs C++ results"""
    print("\\n🏁 Comprehensive Comparison")
    print("=" * 70)
    
    if not python_result or not cpp_result:
        print("❌ Cannot compare - one or both parsers failed")
        return
    
    # Performance comparison
    print("⚡ Performance Comparison:")
    print(f"  Python: {python_result['total_records']:,} records in {python_result['parse_time']:.2f}s ({python_result['records_per_second']:,.0f} rps)")
    print(f"  C++   : {cpp_result['total_records']:,} records in {cpp_result['parse_time']:.2f}s ({cpp_result['records_per_second']:,.0f} rps)")
    
    if cpp_result['records_per_second'] > 0 and python_result['records_per_second'] > 0:
        speed_ratio = cpp_result['records_per_second'] / python_result['records_per_second']
        time_ratio = python_result['parse_time'] / cpp_result['parse_time']
        print(f"  🚀 C++ is {speed_ratio:.1f}x faster than Python")
        print(f"  ⏱️  C++ takes {1/time_ratio:.2f}x less time")
    
    # Accuracy comparison
    print(f"\\n🔍 Record-by-Record Comparison:")
    print(f"{'Type':<8} {'Python':<10} {'C++':<10} {'Diff':<8} {'Status'}")
    print("-" * 45)
    
    all_types = set(python_result['record_types'].keys()) | set(cpp_result['record_types'].keys())
    record_diff_total = 0
    
    for rec_type in sorted(all_types):
        py_count = python_result['record_types'].get(rec_type, 0)
        cpp_count = cpp_result['record_types'].get(rec_type, 0)
        diff = cpp_count - py_count
        record_diff_total += abs(diff)
        
        if diff == 0:
            status = "✅"
        elif abs(diff) < 100:
            status = "⚠️"
        else:
            status = "❌"
        
        print(f"{rec_type:<8} {py_count:<10,} {cpp_count:<10,} {diff:<+8,} {status}")
    
    # Overall accuracy
    print(f"\\n📈 Overall Accuracy:")
    total_diff = abs(cpp_result['total_records'] - python_result['total_records'])
    accuracy_pct = (1 - total_diff / max(cpp_result['total_records'], python_result['total_records'])) * 100
    
    print(f"  Record count difference: {total_diff:,}")
    print(f"  Accuracy: {accuracy_pct:.2f}%")
    
    if total_diff == 0:
        print("  ✅ Perfect accuracy match!")
    elif total_diff < 100:
        print("  ✅ Excellent accuracy!")
    elif total_diff < 1000:
        print("  ⚠️  Good accuracy")
    else:
        print("  ❌ Significant difference detected")
    
    # Efficiency breakdown (Python only)
    if 'step1_time' in python_result and 'step2_time' in python_result:
        print(f"\\n🔧 Python Parser Breakdown:")
        step1_pct = (python_result['step1_time'] / python_result['parse_time']) * 100
        step2_pct = (python_result['step2_time'] / python_result['parse_time']) * 100
        print(f"  Binary→Text: {python_result['step1_time']:.2f}s ({step1_pct:.1f}%)")
        print(f"  Text→Records: {python_result['step2_time']:.2f}s ({step2_pct:.1f}%)")

def main():
    """Main comparison test"""
    print("🏁 Comprehensive STDF Parser Comparison")
    print("=" * 70)
    
    # Test file
    test_file = "STDF_Files/OSBE25_KEWGBBMD1U_BE_HRG39021_KEWGBBMD1U__Prod_TPP202_03_Agilent_93000MT9510_25C_5215_4_20241017193900.stdf"
    
    if not os.path.exists(test_file):
        print(f"❌ Test file not found: {test_file}")
        print("Make sure the STDF file exists in the STDF_Files directory")
        return
    
    print(f"📁 Testing with: {os.path.basename(test_file)}")
    print(f"📏 File size: {os.path.getsize(test_file) / (1024*1024):.1f} MB")
    
    # Run both parsers
    python_result = test_python_parser(test_file)
    cpp_result = test_cpp_parser(test_file)
    
    # Compare results
    compare_results(python_result, cpp_result)
    
    print("\\n" + "=" * 70)
    print("🎉 Comparison completed!")

if __name__ == "__main__":
    main()