#!/usr/bin/env python3
"""
TSR Record Extraction Validator
================================
Validates that TSR records are properly extracted with expected fields.

Usage:
    python scripts/validate_tsr_extraction.py [--required-fields FIELD1,FIELD2,...]

Exit Codes:
    0 - All validations passed
    1 - Validation failed (TSR records missing or required fields not found)

Options:
    --required-fields    Comma-separated list of field names that MUST be present
    --min-records       Minimum number of TSR records expected (default: 1)
    --verbose           Show detailed output
"""

import sys
import os
import argparse
from pathlib import Path
from collections import defaultdict

# Add parent directory to path to import stdf_parser_cpp
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    import stdf_parser_cpp
except ImportError as e:
    print(f"ERROR: Could not import stdf_parser_cpp")
    print(f"   {e}")
    print(f"   Make sure the C++ extension is built first:")
    print(f"   python setup_windows_mingw.py build_ext --inplace")
    sys.exit(1)


class Colors:
    """ANSI color codes for terminal output"""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    CYAN = '\033[96m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

    @staticmethod
    def disable():
        """Disable colors (for Windows or piped output)"""
        Colors.GREEN = ''
        Colors.RED = ''
        Colors.YELLOW = ''
        Colors.CYAN = ''
        Colors.RESET = ''
        Colors.BOLD = ''


def parse_stdf_file(stdf_file):
    """Parse STDF file and return results"""
    if not os.path.exists(stdf_file):
        print(f"{Colors.RED} ERROR: STDF file not found: {stdf_file}{Colors.RESET}")
        return None

    print(f"{Colors.CYAN}Parsing STDF file...{Colors.RESET}")
    print(f"  File: {os.path.basename(stdf_file)}")
    print(f"  Size: {os.path.getsize(stdf_file) / (1024*1024):.2f} MB")
    print()

    try:
        result = stdf_parser_cpp.parse_stdf_file(stdf_file)
        return result
    except Exception as e:
        print(f"{Colors.RED} ERROR: Failed to parse STDF file{Colors.RESET}")
        print(f"   {e}")
        return None


def extract_record_type_data(result):
    """Extract records organized by type"""
    record_type_data = defaultdict(list)

    for record in result.get('records', []):
        rtype = record.get('record_type', 'UNKNOWN')
        record_type_data[rtype].append(record)

    return record_type_data


def validate_tsr_exists(record_type_data, min_records=1):
    """
    Validate that TSR records exist in the parsed data.

    Returns:
        tuple: (passed: bool, tsr_records: list, message: str)
    """
    if 'TSR' not in record_type_data:
        return False, [], "TSR record type not found in parsed data"

    tsr_records = record_type_data['TSR']

    if len(tsr_records) < min_records:
        return False, tsr_records, f"Only {len(tsr_records)} TSR records found (expected at least {min_records})"

    return True, tsr_records, f"Found {len(tsr_records):,} TSR records"


def validate_tsr_fields(tsr_records, required_fields):
    """
    Validate that TSR records contain all required fields.

    Returns:
        tuple: (passed: bool, found_fields: set, missing_fields: set, message: str)
    """
    if not tsr_records:
        return False, set(), set(required_fields), "No TSR records to validate"

    # Get fields from first TSR record (all records should have same fields)
    first_record = tsr_records[0]
    fields = first_record.get('fields', {})
    found_fields = set(fields.keys())

    # Check for required fields
    required_set = set(required_fields) if required_fields else set()
    missing_fields = required_set - found_fields

    if required_fields and missing_fields:
        return False, found_fields, missing_fields, f"Missing {len(missing_fields)} required fields"

    return True, found_fields, missing_fields, f"All {len(found_fields)} fields extracted successfully"


def print_validation_results(args, result, record_type_data, tsr_records, found_fields, missing_fields):
    """Print comprehensive validation results"""

    print()
    print("=" * 80)
    print(f"{Colors.BOLD}TSR EXTRACTION VALIDATION RESULTS{Colors.RESET}")
    print("=" * 80)
    print()

    # Overall parsing statistics
    print(f"{Colors.CYAN}Parsing Summary:{Colors.RESET}")
    print(f"  Total records parsed: {result['parsed_records']:,}")
    print(f"  Record types found: {len(record_type_data)}")
    print(f"  Record types: {', '.join(sorted(record_type_data.keys()))}")
    print()

    # TSR existence check
    print(f"{Colors.CYAN}TSR Record Check:{Colors.RESET}")
    if tsr_records:
        print(f"  {Colors.GREEN} PASSED{Colors.RESET} - TSR records found")
        print(f"    TSR record count: {len(tsr_records):,}")

        # Calculate percentage of total records
        pct = (len(tsr_records) / result['parsed_records']) * 100
        print(f"    Percentage of total: {pct:.1f}%")
    else:
        print(f"  {Colors.RED} FAILED{Colors.RESET} - TSR records NOT FOUND")
    print()

    # TSR field extraction check
    print(f"{Colors.CYAN}TSR Field Extraction:{Colors.RESET}")
    if found_fields:
        print(f"  Total fields extracted: {len(found_fields)}")
        print(f"  Fields: {', '.join(sorted(found_fields))}")
    else:
        print(f"  {Colors.RED}No fields extracted{Colors.RESET}")
    print()

    # Required fields check
    if args.required_fields:
        print(f"{Colors.CYAN}Required Field Validation:{Colors.RESET}")
        required_list = args.required_fields.split(',')
        print(f"  Required fields: {len(required_list)}")
        print(f"  Fields: {', '.join(required_list)}")
        print()

        if missing_fields:
            print(f"  {Colors.RED} FAILED{Colors.RESET} - Missing {len(missing_fields)} required fields")
            print(f"    Missing: {', '.join(sorted(missing_fields))}")
        else:
            print(f"  {Colors.GREEN} PASSED{Colors.RESET} - All required fields present")
    print()

    # Sample TSR record (if verbose)
    if args.verbose and tsr_records:
        print(f"{Colors.CYAN}Sample TSR Record:{Colors.RESET}")
        sample = tsr_records[0].get('fields', {})
        for field_name in sorted(sample.keys()):
            value = str(sample[field_name])
            if len(value) > 60:
                value = value[:60] + '...'
            print(f"  {field_name:20s}: {value}")
        print()


def main():
    """Main validation function"""

    parser = argparse.ArgumentParser(
        description='Validate TSR record extraction from STDF files',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument(
        'stdf_file',
        nargs='?',
        default='STDF_Files/OSBE25_KEWGBBMD1U_BE_HRG39021_KEWGBBMD1U__Prod_TPP202_03_Agilent_93000MT9510_25C_5215_4_20241017193900.stdf',
        help='Path to STDF file (default: test file in STDF_Files/)'
    )

    parser.add_argument(
        '--required-fields',
        type=str,
        help='Comma-separated list of required field names (e.g., "TEST_NUM,TEST_TYP,EXEC_CNT")'
    )

    parser.add_argument(
        '--min-records',
        type=int,
        default=1,
        help='Minimum number of TSR records expected (default: 1)'
    )

    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Show detailed output including sample records'
    )

    parser.add_argument(
        '--no-color',
        action='store_true',
        help='Disable colored output'
    )

    args = parser.parse_args()

    # Disable colors if requested or on Windows (PowerShell doesn't handle ANSI well)
    if args.no_color or sys.platform == 'win32':
        Colors.disable()

    # Print header
    print()
    print("=" * 80)
    print(f"{Colors.BOLD}TSR RECORD EXTRACTION VALIDATOR{Colors.RESET}")
    print("=" * 80)
    print()

    # Parse STDF file
    result = parse_stdf_file(args.stdf_file)
    if result is None:
        sys.exit(1)

    # Extract record type data
    record_type_data = extract_record_type_data(result)

    # Validate TSR exists
    tsr_exists, tsr_records, tsr_message = validate_tsr_exists(record_type_data, args.min_records)

    # Validate TSR fields
    required_fields = args.required_fields.split(',') if args.required_fields else []
    fields_valid, found_fields, missing_fields, fields_message = validate_tsr_fields(tsr_records, required_fields)

    # Print results
    print_validation_results(args, result, record_type_data, tsr_records, found_fields, missing_fields)

    # Determine overall pass/fail
    print("=" * 80)
    print(f"{Colors.BOLD}VALIDATION SUMMARY{Colors.RESET}")
    print("=" * 80)
    print()

    all_passed = True

    # Check 1: TSR records exist
    if tsr_exists:
        print(f"  {Colors.GREEN} TSR records found:{Colors.RESET} {tsr_message}")
    else:
        print(f"  {Colors.RED} TSR records check:{Colors.RESET} {tsr_message}")
        all_passed = False

    # Check 2: Required fields present (if specified)
    if args.required_fields:
        if fields_valid:
            print(f"  {Colors.GREEN} Required fields:{Colors.RESET} {fields_message}")
        else:
            print(f"  {Colors.RED} Required fields:{Colors.RESET} {fields_message}")
            all_passed = False
    else:
        print(f"  {Colors.YELLOW} Required fields:{Colors.RESET} Not specified (use --required-fields)")

    print()

    # Final result
    if all_passed:
        print(f"{Colors.GREEN}{Colors.BOLD} ALL VALIDATIONS PASSED!{Colors.RESET}")
        print()
        return 0
    else:
        print(f"{Colors.RED}{Colors.BOLD} VALIDATION FAILED!{Colors.RESET}")
        print()
        return 1


if __name__ == '__main__':
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}Validation interrupted by user{Colors.RESET}")
        sys.exit(1)
    except Exception as e:
        print(f"\n{Colors.RED} UNEXPECTED ERROR:{Colors.RESET}")
        print(f"   {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
