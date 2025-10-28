#!/usr/bin/env python3
"""
STDF Parser Demonstration - Dynamic Record Type & Field Detection
Automatically detects all record types and extracts all fields without hardcoding
"""

import stdf_parser_cpp
import os
import time
from collections import defaultdict

# Get the first STDF file
stdf_file = 'STDF_Files/OSBE25_KEWGBBMD1U_BE_HRG39021_KEWGBBMD1U__Prod_TPP202_03_Agilent_93000MT9510_25C_5215_4_20241017193900.stdf'

print('=' * 80)
print('STDF PARSER DEMONSTRATION - DYNAMIC MODE')
print('=' * 80)
print(f'File: {os.path.basename(stdf_file)}')
print(f'File Size: {os.path.getsize(stdf_file) / (1024*1024):.2f} MB')
print()

# Parse the file
print('Parsing STDF file...')
start_time = time.time()
result = stdf_parser_cpp.parse_stdf_file(stdf_file)
parse_time = time.time() - start_time

print()
print('=' * 80)
print('PARSING RESULTS')
print('=' * 80)
print(f'Total records in file: {result["total_records"]:,}')
print(f'Records parsed: {result["parsed_records"]:,}')
print(f'Parsing time: {parse_time:.2f} seconds')
print(f'Throughput: {result["total_records"]/parse_time:,.0f} records/second')
print()

# ============================================================================
# DYNAMIC RECORD TYPE ANALYSIS
# ============================================================================
# Automatically organize records by type and collect field metadata
record_types = defaultdict(list)
record_type_fields = defaultdict(set)

for record in result['records']:
    rtype = record.get('record_type', 'UNKNOWN')
    record_types[rtype].append(record)

    # Collect all unique fields for this record type
    fields = record.get('fields', {})
    record_type_fields[rtype].update(fields.keys())

# Sort record types by count (descending)
sorted_types = sorted(record_types.items(), key=lambda x: len(x[1]), reverse=True)

print('=' * 80)
print('DYNAMIC RECORD TYPE DETECTION')
print('=' * 80)
print(f'Detected {len(record_types)} unique record type(s):\n')

for rtype, records in sorted_types:
    count = len(records)
    pct = (count / result["parsed_records"]) * 100
    field_count = len(record_type_fields[rtype])
    print(f'   {rtype:12s}: {count:6,} records ({pct:5.1f}%) | {field_count:2d} fields extracted')

# ============================================================================
# SAMPLE DATA EXTRACTION - DYNAMIC (First 2-3 records per type)
# ============================================================================
print()
print('=' * 80)
print('SAMPLE DATA EXTRACTION (All Record Types)')
print('=' * 80)

# Define record type descriptions
RECORD_DESCRIPTIONS = {
    'PTR': 'Parametric Test Record',
    'MPR': 'Multiple-Result Parametric Record',
    'FTR': 'Functional Test Record',
    'PRR': 'Part Result Record',
    'MIR': 'Master Information Record',
    'HBR': 'Hardware Bin Record',
    'SBR': 'Software Bin Record',
    'TSR': 'Test Synopsis Record',
    'WIR': 'Wafer Information Record',
    'WRR': 'Wafer Results Record',
    'UNKNOWN': 'Unknown/Unsupported Record Type'
}

# Key fields to highlight for each record type (if available)
KEY_FIELDS = {
    'PTR': ['TEST_NUM', 'HEAD_NUM', 'SITE_NUM', 'RESULT', 'UNITS', 'LO_LIMIT', 'HI_LIMIT', 'TEST_FLG', 'TEST_TXT'],
    'MPR': ['TEST_NUM', 'HEAD_NUM', 'SITE_NUM', 'RSLT_CNT', 'UNITS', 'TEST_TXT'],
    'FTR': ['TEST_NUM', 'HEAD_NUM', 'SITE_NUM', 'TEST_FLG', 'TEST_TXT'],
    'PRR': ['HEAD_NUM', 'SITE_NUM', 'PART_ID', 'HARD_BIN', 'SOFT_BIN', 'X_COORD', 'Y_COORD', 'NUM_TEST'],
    'MIR': ['SETUP_T', 'START_T', 'LOT_ID', 'PART_TYP', 'NODE_NAM', 'TSTR_TYP', 'JOB_NAM', 'EXEC_TYP'],
    'HBR': ['HEAD_NUM', 'SITE_NUM', 'HBIN_NUM', 'HBIN_CNT', 'HBIN_NAM'],
    'SBR': ['HEAD_NUM', 'SITE_NUM', 'SBIN_NUM', 'SBIN_CNT', 'SBIN_NAM'],
    'TSR': ['HEAD_NUM', 'SITE_NUM', 'TEST_TYP', 'TEST_NUM', 'EXEC_CNT', 'FAIL_CNT', 'ALRM_CNT', 'TEST_NAM', 'TEST_MIN', 'TEST_MAX'],
}

# Display sample records for each detected type
for rtype, records in sorted_types:
    if not records:
        continue

    desc = RECORD_DESCRIPTIONS.get(rtype, f'{rtype} Record Type')
    sample_count = min(3, len(records))

    print(f'\n{rtype} ({desc})')
    print(f'   Total: {len(records):,} records | Showing first {sample_count}:')

    for i, record in enumerate(records[:sample_count], 1):
        fields = record.get('fields', {})
        print(f'\n   Record #{i}:')

        # Show key fields if defined for this type
        key_fields = KEY_FIELDS.get(rtype, sorted(fields.keys())[:8])

        for field_name in key_fields:
            if field_name in fields:
                value = fields[field_name]
                # Truncate long values
                if isinstance(value, str) and len(value) > 60:
                    value = value[:60] + '...'
                print(f'      {field_name:15s}: {value}')

# ============================================================================
# FIELD EXTRACTION VALIDATION - Shows ALL fields for each record type
# ============================================================================
print()
print('=' * 80)
print('FIELD EXTRACTION VALIDATION')
print('=' * 80)
print('All fields extracted per record type:\n')

for rtype in sorted(record_types.keys()):
    fields = sorted(record_type_fields[rtype])
    print(f'{rtype} ({len(fields)} fields):')

    # Get first record of this type to show sample values
    sample_record = record_types[rtype][0]
    sample_fields = sample_record.get('fields', {})

    for i, field_name in enumerate(fields, 1):
        value = sample_fields.get(field_name, 'N/A')
        # Truncate long values
        if isinstance(value, str) and len(value) > 40:
            value = value[:40] + '...'
        print(f'   {i:2d}. {field_name:20s} = {value}')
    print()

# ============================================================================
# TSR RECORD VALIDATION (CI/CD Check)
# ============================================================================
print('=' * 80)
print('TSR RECORD TYPE VALIDATION')
print('=' * 80)

if 'TSR' in record_types:
    tsr_records = record_types['TSR']
    tsr_fields = record_type_fields['TSR']

    print(f'✅ TSR Record Type DETECTED')
    print(f'   Records found: {len(tsr_records):,}')
    print(f'   Fields extracted: {len(tsr_fields)}')
    print(f'   Field list: {", ".join(sorted(tsr_fields))}')

    # Expected TSR fields (from STDF specification)
    expected_fields = {
        'HEAD_NUM', 'SITE_NUM', 'TEST_TYP', 'TEST_NUM',
        'EXEC_CNT', 'FAIL_CNT', 'ALRM_CNT', 'TEST_NAM',
        'SEQ_NAME', 'TEST_LBL', 'OPT_FLAG', 'TEST_TIM',
        'TEST_MIN', 'TEST_MAX', 'TST_SUMS', 'TST_SQRS'
    }

    found_fields = tsr_fields & expected_fields
    missing_fields = expected_fields - tsr_fields

    if found_fields:
        print(f'\n   ✅ Found {len(found_fields)} expected TSR fields:')
        print(f'      {", ".join(sorted(found_fields))}')

    if missing_fields:
        print(f'\n   ⚠️  Missing {len(missing_fields)} expected TSR fields:')
        print(f'      {", ".join(sorted(missing_fields))}')

    # Show sample TSR record
    if tsr_records:
        print(f'\n   Sample TSR Record:')
        sample = tsr_records[0].get('fields', {})
        for field in sorted(tsr_fields):
            print(f'      {field:15s}: {sample.get(field, "N/A")}')
else:
    print('ℹ️  TSR Record Type NOT FOUND in this STDF file')
    print('   This is normal if the test file does not contain TSR records.')
    print('   TSR support is configured and will work when TSR records are present.')

# ============================================================================
# SUMMARY
# ============================================================================
print()
print('=' * 80)
print('PARSING COMPLETED SUCCESSFULLY!')
print('=' * 80)
print(f'\nParser Version: {stdf_parser_cpp.get_version()}')
print(f'Total Processing Time: {parse_time:.2f} seconds')
print(f'Average Record Parse Time: {(parse_time / result["total_records"]) * 1000:.3f} ms per record')
print(f'\nRecord Types Detected: {len(record_types)}')
print(f'Total Fields Extracted: {sum(len(fields) for fields in record_type_fields.values())}')
print(f'Unique Record Types: {", ".join(sorted(record_types.keys()))}')
