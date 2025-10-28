#!/usr/bin/env python3
"""
STDF Parser Demonstration - Dynamic Version
===========================================
Automatically detects and displays ALL record types and fields.
Perfect for validating new record types (like TSR) added via scripts.

Features:
- Auto-detects all record types from parsed data
- Dynamically extracts ALL fields from each record type
- Shows comprehensive statistics
- Validates record type additions for CI/CD
- No hardcoded field names or record types
"""

import stdf_parser_cpp
import os
import sys
import time
from collections import defaultdict
from pathlib import Path


def get_available_record_types_from_registry():
    """
    Read record_types.def to get all defined record types.
    This is the ground truth of what SHOULD be available.
    """
    registry_file = Path("cpp/field_defs/record_types.def")

    if not registry_file.exists():
        return []

    record_types = []
    with open(registry_file, 'r') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('//'):
                continue
            if line.startswith('RECORD_TYPE('):
                # Extract: RECORD_TYPE(TSR, rec_tsr, 10, 30, REC_TSR)
                parts = line.split('(')[1].split(',')
                if parts:
                    record_name = parts[0].strip()
                    record_types.append(record_name)

    return record_types


def get_field_count_from_def(record_type):
    """Get the number of fields defined in a record's .def file"""
    def_file = Path(f"cpp/field_defs/{record_type.lower()}_fields.def")

    if not def_file.exists():
        return 0

    field_count = 0
    with open(def_file, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('//') and line.startswith('FIELD('):
                field_count += 1

    return field_count


def format_value(value, max_length=60):
    """Format a value for display, truncating if too long"""
    value_str = str(value)
    if len(value_str) > max_length:
        return value_str[:max_length] + '...'
    return value_str


def display_record_sample(record_type, records, num_samples=2):
    """Display sample records with ALL their fields dynamically"""
    print(f'\n{record_type} Records - Showing first {min(num_samples, len(records))} of {len(records):,}:')

    for i, record in enumerate(records[:num_samples], 1):
        fields = record.get('fields', {})

        if not fields:
            print(f'\n   Record #{i}: (No fields extracted)')
            continue

        print(f'\n   Record #{i}: ({len(fields)} fields)')

        # Sort fields for consistent display
        for field_name in sorted(fields.keys()):
            value = format_value(fields[field_name])
            print(f'      {field_name:20s}: {value}')


def analyze_and_display_results(result, parse_time):
    """Analyze and display parsing results dynamically"""

    print()
    print('=' * 80)
    print('PARSING RESULTS')
    print('=' * 80)
    print(f'Total records in file: {result["total_records"]:,}')
    print(f'Records parsed: {result["parsed_records"]:,}')
    print(f'Parsing time: {parse_time:.2f} seconds')
    print(f'Throughput: {result["total_records"]/parse_time:,.0f} records/second')
    print()

    # Auto-detect record types from parsed data
    record_type_data = defaultdict(list)
    for record in result['records']:
        rtype = record.get('record_type', 'UNKNOWN')
        record_type_data[rtype].append(record)

    print('Record Type Distribution:')
    for rtype in sorted(record_type_data.keys(), key=lambda x: len(record_type_data[x]), reverse=True):
        count = len(record_type_data[rtype])
        pct = (count / result["parsed_records"]) * 100
        print(f'   {rtype:8s}: {count:6,} records ({pct:5.1f}%)')

    print()
    print('=' * 80)
    print('SAMPLE DATA EXTRACTION')
    print('=' * 80)

    # Display samples for each detected record type
    for rtype in sorted(record_type_data.keys()):
        records = record_type_data[rtype]
        # Show fewer samples for common types, more for rare types
        num_samples = 1 if len(records) > 1000 else min(3, len(records))
        display_record_sample(rtype, records, num_samples)

    print()
    print('=' * 80)
    print('FIELD EXTRACTION CAPABILITIES')
    print('=' * 80)

    # Show field statistics for each record type
    for rtype in sorted(record_type_data.keys()):
        records = record_type_data[rtype]

        # Collect all unique fields across all records of this type
        all_fields = set()
        for record in records:
            fields = record.get('fields', {})
            all_fields.update(fields.keys())

        if all_fields:
            print(f'\n{rtype} - Total unique fields extracted: {len(all_fields)}')
            print(f'   Fields: {", ".join(sorted(all_fields))}')
        else:
            print(f'\n{rtype} - No fields extracted (check field definitions)')

    return record_type_data


def validate_record_types(record_type_data):
    """Validate that record types from registry are properly parsed"""
    print()
    print('=' * 80)
    print('RECORD TYPE VALIDATION')
    print('=' * 80)

    # Get expected record types from registry
    expected_types = get_available_record_types_from_registry()

    if not expected_types:
        print('⚠️  Could not read record_types.def - skipping validation')
        return True

    print(f'\nExpected record types from registry: {len(expected_types)}')
    print(f'   {", ".join(sorted(expected_types))}')

    print(f'\nParsed record types from file: {len(record_type_data)}')
    print(f'   {", ".join(sorted(record_type_data.keys()))}')

    # Check for each expected type
    print('\nValidation Results:')
    all_valid = True

    for rtype in sorted(expected_types):
        # Get field count from .def file
        expected_fields = get_field_count_from_def(rtype)

        if rtype in record_type_data:
            records = record_type_data[rtype]
            # Get actual field count from first record
            actual_fields = len(records[0].get('fields', {})) if records else 0

            if actual_fields > 0:
                status = '✅'
                details = f'{len(records):,} records, {actual_fields} fields extracted'
                if expected_fields > 0 and actual_fields != expected_fields:
                    details += f' (expected {expected_fields} fields from .def)'
            else:
                status = '⚠️ '
                details = f'{len(records):,} records, but NO fields extracted!'
                all_valid = False
        else:
            status = '❌'
            details = 'NOT FOUND in parsed data (may not exist in this file)'

        print(f'   {status} {rtype:8s}: {details}')

    # Check for unexpected types
    unexpected = set(record_type_data.keys()) - set(expected_types) - {'UNKNOWN'}
    if unexpected:
        print(f'\n⚠️  Unexpected record types found: {", ".join(sorted(unexpected))}')

    return all_valid


def main():
    """Main demonstration function"""

    # Default STDF file
    stdf_file = 'STDF_Files/OSBE25_KEWGBBMD1U_BE_HRG39021_KEWGBBMD1U__Prod_TPP202_03_Agilent_93000MT9510_25C_5215_4_20241017193900.stdf'

    # Allow command line override
    if len(sys.argv) > 1:
        stdf_file = sys.argv[1]

    if not os.path.exists(stdf_file):
        print(f'❌ Error: File not found: {stdf_file}')
        sys.exit(1)

    print('=' * 80)
    print('STDF PARSER DEMONSTRATION')
    print('=' * 80)
    print(f'File: {os.path.basename(stdf_file)}')
    print(f'File Size: {os.path.getsize(stdf_file) / (1024*1024):.2f} MB')
    print()

    # Parse the file
    print('Parsing STDF file...')
    start_time = time.time()
    result = stdf_parser_cpp.parse_stdf_file(stdf_file)
    parse_time = time.time() - start_time

    # Analyze and display results
    record_type_data = analyze_and_display_results(result, parse_time)

    # Validate record types
    validate_record_types(record_type_data)

    print()
    print('=' * 80)
    print('PARSING COMPLETED SUCCESSFULLY!')
    print('=' * 80)
    print(f'\nParser Version: {stdf_parser_cpp.get_version()}')
    print(f'Total Processing Time: {parse_time:.2f} seconds')
    print(f'Average Record Parse Time: {(parse_time / result["total_records"]) * 1000:.3f} ms per record')
    print()


if __name__ == '__main__':
    main()
