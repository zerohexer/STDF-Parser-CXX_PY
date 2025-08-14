#!/usr/bin/env python3
"""
Direct comparison: STDFReader_CPP (C++) vs pystdf (Python)
Compares field extraction between C++ libstdf and Python pystdf implementations
"""

import sys
import os
import platform
import time
from collections import defaultdict

def setup_platform_libraries():
    """Setup libraries for the current platform"""
    system = platform.system().lower()
    if system == "linux":
        lib_dir = os.path.join(os.path.dirname(__file__), "cpp", "third_party", "lib")
        current_path = os.environ.get("LD_LIBRARY_PATH", "")
        if lib_dir not in current_path:
            os.environ["LD_LIBRARY_PATH"] = f"{lib_dir}:{current_path}" if current_path else lib_dir
    elif system == "windows":
        lib_dir = os.path.join(os.path.dirname(__file__), "cpp", "third_party", "lib")
        if os.path.exists(lib_dir) and hasattr(os, 'add_dll_directory'):
            try:
                os.add_dll_directory(lib_dir)
            except:
                pass

def run_cpp_extraction(stdf_file):
    """Run C++ version and extract sample records"""
    setup_platform_libraries()
    
    try:
        import stdf_parser_cpp
        print("✅ C++ Extension loaded successfully")
        
        start_time = time.time()
        result = stdf_parser_cpp.parse_stdf_file(stdf_file)
        end_time = time.time()
        
        records = result.get('records', [])
        print(f"C++ parsed {len(records):,} records in {end_time - start_time:.2f}s")
        
        # Group records by type and get samples
        cpp_samples = {}
        for record in records:
            record_type = record.get('record_type', 'UNKNOWN')
            if record_type not in cpp_samples:
                cpp_samples[record_type] = record
        
        return cpp_samples, end_time - start_time
        
    except Exception as e:
        print(f"❌ C++ extraction failed: {e}")
        return None, 0

def run_pystdf_extraction(stdf_file):
    """Run pystdf version and extract sample records using STDF_Parser_CH approach"""
    try:
        import pystdf.V4 as v4
        from pystdf.IO import Parser
        from pystdf.Writers import TextWriter
        from io import StringIO
        print("✅ pystdf loaded successfully")
        
        start_time = time.time()
        
        # Use same approach as STDF_Parser_CH
        with open(stdf_file, 'rb') as f_in:
            p = Parser(inp=f_in)
            captured_std_out = StringIO()
            p.addSink(TextWriter(captured_std_out))
            p.parse()
            atdf = captured_std_out.getvalue()
        
        # Split into lines like STDF_Parser_CH
        record_lines = atdf.split('\n')
        print(f"pystdf generated {len(record_lines)} text lines")
        
        # Debug: Show sample lines to understand format
        print("DEBUG: Sample pystdf output lines:")
        for i, line in enumerate(record_lines[:10]):
            if line.strip():
                print(f"  {i}: {line}")
        
        # Debug: Show PTR lines specifically
        ptr_lines = [line for line in record_lines if line.startswith('PTR')][:2]
        print("DEBUG: Sample PTR lines:")
        for i, line in enumerate(ptr_lines):
            print(f"  PTR{i}: {line}")
            fields = line.split('|')
            print(f"    Split into {len(fields)} fields: {fields[:10]}...")  # Show first 10 fields
        
        # Parse records like STDF_Parser_CH does
        required_records = ['MIR', 'PIR', 'PRR', 'PTR', 'MPR', 'FTR', 'HBR', 'SBR']
        raw_records = {}
        
        # Parse records with proper field alignment
        for record_type in v4.records:
            record_name = record_type.name.split('.')[-1].upper()
            if record_name in required_records:
                curr = [line for line in record_lines if line.startswith(record_name)]
                if curr:
                    raw_records[record_name] = []
                    # Get field names from pystdf record definition
                    header_names = list(list(zip(*record_type.fieldMap))[0])
                    
                    for line in curr:
                        fields = line.split('|')
                        # Skip the first few fields (record type, etc.) and properly align
                        if len(fields) >= len(header_names):
                            # The pystdf TextWriter format is: RECORD|field1|field2|...
                            # We need to skip the record name and align properly
                            data_fields = fields[1:]  # Skip record name
                            
                            # Ensure we have enough fields
                            while len(data_fields) < len(header_names):
                                data_fields.append('')
                            
                            # Create record with proper field alignment
                            record_data = {}
                            for i, field_name in enumerate(header_names):
                                if i < len(data_fields):
                                    record_data[field_name] = data_fields[i]
                                else:
                                    record_data[field_name] = ''
                                    
                            raw_records[record_name].append(record_data)
        
        # Get first sample of each record type
        pystdf_samples = {}
        record_counts = {}
        
        for record_name, records in raw_records.items():
            if records:
                record_counts[record_name] = len(records)
                pystdf_samples[record_name] = records[0]  # First sample
        
        end_time = time.time()
        
        print(f"pystdf parsed records in {end_time - start_time:.2f}s")
        print(f"Record counts: {record_counts}")
        
        return pystdf_samples, end_time - start_time
        
    except Exception as e:
        print(f"❌ pystdf extraction failed: {e}")
        import traceback
        traceback.print_exc()
        return None, 0

def normalize_field_name(field_name):
    """Normalize field names for comparison"""
    # Convert to lowercase and remove common prefixes/suffixes
    normalized = field_name.lower()
    
    # Remove common prefixes
    for prefix in ['rec_', 'stdf_']:
        if normalized.startswith(prefix):
            normalized = normalized[len(prefix):]
    
    return normalized

def compare_record_fields(cpp_record, pystdf_record, record_type):
    """Compare fields between C++ and pystdf records"""
    print(f"\n{'='*60}")
    print(f"COMPARING {record_type} RECORD FIELDS")
    print(f"{'='*60}")
    
    # Get C++ fields
    cpp_fields = cpp_record.get('fields', {})
    cpp_direct_fields = {k: v for k, v in cpp_record.items() if k not in ['fields', 'type', 'record_type']}
    
    # Combine all C++ fields
    all_cpp_fields = {**cpp_direct_fields, **cpp_fields}
    
    print(f"\n--- C++ {record_type} Fields ({len(all_cpp_fields)}) ---")
    for key, value in sorted(all_cpp_fields.items()):
        print(f"  {key:<20} = {value}")
    
    print(f"\n--- pystdf {record_type} Fields ({len(pystdf_record)}) ---")
    for key, value in sorted(pystdf_record.items()):
        print(f"  {key:<20} = {value}")
    
    # Field comparison analysis
    print(f"\n--- FIELD COMPARISON ANALYSIS ---")
    
    cpp_field_set = set(all_cpp_fields.keys())
    pystdf_field_set = set(pystdf_record.keys())
    
    # Normalize field names for better matching
    cpp_normalized = {normalize_field_name(f): f for f in cpp_field_set}
    pystdf_normalized = {normalize_field_name(f): f for f in pystdf_field_set}
    
    normalized_common = set(cpp_normalized.keys()) & set(pystdf_normalized.keys())
    cpp_only_normalized = set(cpp_normalized.keys()) - set(pystdf_normalized.keys())
    pystdf_only_normalized = set(pystdf_normalized.keys()) - set(cpp_normalized.keys())
    
    print(f"Common fields (normalized, {len(normalized_common)}): {sorted(normalized_common)}")
    print(f"C++ only (normalized, {len(cpp_only_normalized)}): {sorted(cpp_only_normalized)}")
    print(f"pystdf only (normalized, {len(pystdf_only_normalized)}): {sorted(pystdf_only_normalized)}")
    
    # Check if values match for common fields
    matching_fields = []
    different_fields = []
    
    for norm_field in normalized_common:
        cpp_field = cpp_normalized[norm_field]
        pystdf_field = pystdf_normalized[norm_field]
        
        cpp_value = str(all_cpp_fields.get(cpp_field, '')).strip()
        pystdf_value = str(pystdf_record.get(pystdf_field, '')).strip()
        
        if cpp_value == pystdf_value:
            matching_fields.append((norm_field, cpp_value))
        else:
            different_fields.append((norm_field, cpp_field, pystdf_field, cpp_value, pystdf_value))
    
    print(f"\n✅ MATCHING VALUES ({len(matching_fields)}):")
    for field, value in sorted(matching_fields):
        print(f"  {field:<20} = '{value}'")
    
    if different_fields:
        print(f"\n❌ DIFFERENT VALUES ({len(different_fields)}):")
        for norm_field, cpp_field, pystdf_field, cpp_val, pystdf_val in different_fields:
            print(f"  {norm_field:<20}:")
            print(f"    C++ ({cpp_field:<15}) = '{cpp_val}'")
            print(f"    pystdf ({pystdf_field:<12}) = '{pystdf_val}'")
    
    # Key field checks
    key_fields = ['test_flg', 'test_num', 'head_num', 'site_num', 'result']
    print(f"\n🎯 KEY FIELD CHECK:")
    for key_field in key_fields:
        cpp_val = all_cpp_fields.get(key_field, 'NOT_FOUND')
        
        # Try different case variations in pystdf
        pystdf_val = 'NOT_FOUND'
        for variant in [key_field, key_field.upper(), key_field.lower()]:
            if variant in pystdf_record:
                pystdf_val = pystdf_record[variant]
                break
        
        status = "✅ MATCH" if str(cpp_val) == str(pystdf_val) else "❌ DIFF"
        print(f"  {key_field:<15}: C++='{cpp_val}' vs pystdf='{pystdf_val}' {status}")
    
    return {
        'cpp_field_count': len(all_cpp_fields),
        'pystdf_field_count': len(pystdf_record),
        'common_fields': len(normalized_common),
        'matching_values': len(matching_fields),
        'different_values': len(different_fields)
    }

def main():
    """Main comparison function"""
    print("FIELD EXTRACTION COMPARISON: C++ libstdf vs Python pystdf")
    print("=" * 80)
    
    # Test with first available STDF file
    stdf_dir = "STDF_Files"
    if not os.path.exists(stdf_dir):
        print(f"❌ STDF_Files directory not found")
        return False
    
    stdf_files = [f for f in os.listdir(stdf_dir) if f.endswith('.stdf')]
    if not stdf_files:
        print("❌ No .stdf files found")
        return False
    
    test_file = os.path.join(stdf_dir, stdf_files[0])
    print(f"📁 Testing with: {os.path.basename(test_file)}")
    
    # Run both extractors
    print(f"\n🔄 Running C++ extraction...")
    cpp_samples, cpp_time = run_cpp_extraction(test_file)
    
    print(f"\n🔄 Running pystdf extraction...")
    pystdf_samples, pystdf_time = run_pystdf_extraction(test_file)
    
    if not cpp_samples or not pystdf_samples:
        print("❌ One or both extractors failed")
        return False
    
    # Performance comparison
    print(f"\n📊 PERFORMANCE COMPARISON:")
    print(f"  C++ time: {cpp_time:.2f}s")
    print(f"  pystdf time: {pystdf_time:.2f}s")
    if cpp_time > 0:
        print(f"  Speedup: {pystdf_time/cpp_time:.1f}x")
    
    # Record type comparison
    print(f"\n📋 RECORD TYPES FOUND:")
    print(f"  C++: {sorted(cpp_samples.keys())}")
    print(f"  pystdf: {sorted(pystdf_samples.keys())}")
    
    # Compare record types (both should use same naming now)
    common_types = []
    for cpp_type in cpp_samples.keys():
        if cpp_type in pystdf_samples:
            common_types.append((cpp_type, cpp_type))
    
    print(f"\n🔍 COMPARING {len(common_types)} RECORD TYPES...")
    
    comparison_results = {}
    
    for cpp_type, pystdf_type in common_types:
        cpp_sample = cpp_samples[cpp_type]
        pystdf_sample = pystdf_samples[pystdf_type]
        
        results = compare_record_fields(cpp_sample, pystdf_sample, cpp_type)
        comparison_results[cpp_type] = results
    
    # Summary table
    print(f"\n📝 COMPARISON SUMMARY:")
    print(f"{'Record':<10} {'C++ Fields':<12} {'pystdf Fields':<15} {'Common':<8} {'Match':<7} {'Diff':<6}")
    print("-" * 70)
    
    for record_type, results in comparison_results.items():
        print(f"{record_type:<10} {results['cpp_field_count']:<12} {results['pystdf_field_count']:<15} "
              f"{results['common_fields']:<8} {results['matching_values']:<7} {results['different_values']:<6}")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)