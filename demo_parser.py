#!/usr/bin/env python3
"""
STDF Parser Demonstration
Runs the C++ STDF parser and displays detailed results
"""

import stdf_parser_cpp
import os
import time

# Get the first STDF file
stdf_file = 'STDF_Files/OSBE25_KEWGBBMD1U_BE_HRG39021_KEWGBBMD1U__Prod_TPP202_03_Agilent_93000MT9510_25C_5215_4_20241017193900.stdf'

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

print()
print('=' * 80)
print('PARSING RESULTS')
print('=' * 80)
print(f'Total records in file: {result["total_records"]:,}')
print(f'Records parsed: {result["parsed_records"]:,}')
print(f'Parsing time: {parse_time:.2f} seconds')
print(f'Throughput: {result["total_records"]/parse_time:,.0f} records/second')
print()

# Analyze record types
record_types = {}
for record in result['records']:
    rtype = record.get('record_type', 'UNKNOWN')
    record_types[rtype] = record_types.get(rtype, 0) + 1

print('Record Type Distribution:')
for rtype, count in sorted(record_types.items(), key=lambda x: x[1], reverse=True):
    pct = (count / result["parsed_records"]) * 100
    print(f'   {rtype:8s}: {count:6,} records ({pct:5.1f}%)')

print()
print('=' * 80)
print('SAMPLE DATA EXTRACTION')
print('=' * 80)

# Show PTR records
ptr_records = [r for r in result['records'] if r.get('record_type') == 'PTR']
print(f'\nPTR (Parametric Test) Records - Showing first 3 of {len(ptr_records):,}:')
for i, record in enumerate(ptr_records[:3], 1):
    fields = record.get('fields', {})
    print(f'\n   Record #{i}:')
    print(f'      TEST_NUM:  {fields.get("TEST_NUM", "N/A")}')
    alarm_id = fields.get("ALARM_ID", "N/A")
    if len(alarm_id) > 60:
        print(f'      ALARM_ID:  {alarm_id[:60]}...')
    else:
        print(f'      ALARM_ID:  {alarm_id}')
    print(f'      RESULT:    {fields.get("RESULT", "N/A")}')
    print(f'      UNITS:     {fields.get("UNITS", "N/A")}')
    print(f'      LO_LIMIT:  {fields.get("LO_LIMIT", "N/A")}')
    print(f'      HI_LIMIT:  {fields.get("HI_LIMIT", "N/A")}')
    print(f'      TEST_FLG:  {fields.get("TEST_FLG", "N/A")}')

# Show MPR records
mpr_records = [r for r in result['records'] if r.get('record_type') == 'MPR']
if mpr_records:
    print(f'\nMPR (Multiple-Result Parametric) Records - Showing first 2 of {len(mpr_records):,}:')
    for i, record in enumerate(mpr_records[:2], 1):
        fields = record.get('fields', {})
        print(f'\n   Record #{i}:')
        print(f'      TEST_NUM:  {fields.get("TEST_NUM", "N/A")}')
        alarm_id = fields.get("ALARM_ID", "N/A")
        if len(alarm_id) > 60:
            print(f'      ALARM_ID:  {alarm_id[:60]}...')
        else:
            print(f'      ALARM_ID:  {alarm_id}')
        print(f'      RSLT_CNT:  {fields.get("RSLT_CNT", "N/A")} (number of measurements)')
        print(f'      UNITS:     {fields.get("UNITS", "N/A")}')

# Show PRR records
prr_records = [r for r in result['records'] if r.get('record_type') == 'PRR']
print(f'\nPRR (Part Result) Records - Showing first 3 of {len(prr_records):,}:')
for i, record in enumerate(prr_records[:3], 1):
    fields = record.get('fields', {})
    print(f'\n   Record #{i}:')
    print(f'      PART_ID:   {fields.get("PART_ID", "N/A")}')
    print(f'      X_COORD:   {fields.get("X_COORD", "N/A")}')
    print(f'      Y_COORD:   {fields.get("Y_COORD", "N/A")}')
    print(f'      HARD_BIN:  {fields.get("HARD_BIN", "N/A")}')
    print(f'      SOFT_BIN:  {fields.get("SOFT_BIN", "N/A")}')
    print(f'      NUM_TEST:  {fields.get("NUM_TEST", "N/A")} tests executed')

# Show MIR record
mir_records = [r for r in result['records'] if r.get('record_type') == 'MIR']
if mir_records:
    print(f'\nMIR (Master Information) Record - File metadata:')
    fields = mir_records[0].get('fields', {})
    print(f'      LOT_ID:      {fields.get("LOT_ID", "N/A")}')
    print(f'      PART_TYP:    {fields.get("PART_TYP", "N/A")}')
    print(f'      NODE_NAM:    {fields.get("NODE_NAM", "N/A")}')
    print(f'      TSTR_TYP:    {fields.get("TSTR_TYP", "N/A")}')
    print(f'      JOB_NAM:     {fields.get("JOB_NAM", "N/A")}')
    print(f'      EXEC_TYP:    {fields.get("EXEC_TYP", "N/A")}')
    print(f'      STAT_NUM:    {fields.get("STAT_NUM", "N/A")}')

print()
print('=' * 80)
print('FIELD EXTRACTION CAPABILITIES')
print('=' * 80)

# Show all available fields for PTR record
if ptr_records:
    print('\nAll fields extracted from PTR record:')
    fields = ptr_records[0].get('fields', {})
    field_names = sorted(fields.keys())
    for i, field_name in enumerate(field_names, 1):
        value = fields[field_name]
        if len(str(value)) > 50:
            value = str(value)[:50] + '...'
        print(f'   {i:2d}. {field_name:15s} = {value}')

print()
print('=' * 80)
print('PARSING COMPLETED SUCCESSFULLY!')
print('=' * 80)
print(f'\nParser Version: {stdf_parser_cpp.get_version()}')
print(f'Total Processing Time: {parse_time:.2f} seconds')
print(f'Average Record Parse Time: {(parse_time / result["total_records"]) * 1000:.3f} ms per record')
