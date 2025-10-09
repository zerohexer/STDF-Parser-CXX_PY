#!/usr/bin/env python3
"""
Test Runtime Flexible API - Approach 3
=======================================
Demonstrates the new flexible API where Python specifies which fields
to add at runtime, and C++ does ALL the work (3M lookups in C++).

NO C++ REBUILD NEEDED to change fields!

Usage:
    python test_runtime_flexible_api.py --stdf-file path/to/file.stdf
"""

import os
import sys
import argparse
import platform
import time

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
    print("Make sure to build: python setup.py build_ext --inplace")
    sys.exit(1)


def test_use_case_1_ftr_fields(stdf_file: str):
    """Use Case 1: Add 3 FTR fields"""
    print("\n" + "=" * 70)
    print("🔬 USE CASE 1: Add FTR fields (VECT_NAM, TIME_SET, OP_CODE)")
    print("=" * 70)

    start_time = time.time()

    result = stdf_parser_cpp.process_stdf_file_measurements(
        stdf_file,
        extra_fields=[
            ('FTR', ['VECT_NAM', 'TIME_SET', 'OP_CODE'])
        ]
    )

    elapsed = time.time() - start_time
    measurements = result['measurement_tuples']

    print(f"\n✅ Processed {len(measurements):,} measurements in {elapsed:.2f}s")
    print(f"⚡ Throughput: {len(measurements) / elapsed:,.0f} measurements/second")

    # Show sample measurements
    print(f"\n📋 Sample Measurements (first 3):")
    for i, m in enumerate(measurements[:3], 1):
        # Tuple has 14 elements: 13 base fields + 1 extra_fields dict
        *base_fields, extra_fields = m
        print(f"\n--- Measurement #{i} ---")
        print(f"Test #: {base_fields[11]}")  # test_num
        print(f"Value: {base_fields[4]}")     # wptm_value
        print(f"Extra fields: {extra_fields}")


def test_use_case_2_ptr_fields(stdf_file: str):
    """Use Case 2: Add PTR fields (different fields!)"""
    print("\n" + "=" * 70)
    print("🔬 USE CASE 2: Add PTR fields (HI_LIMIT, LO_LIMIT, UNITS)")
    print("=" * 70)

    start_time = time.time()

    result = stdf_parser_cpp.process_stdf_file_measurements(
        stdf_file,
        extra_fields=[
            ('PTR', ['HI_LIMIT', 'LO_LIMIT', 'UNITS'])
        ]
    )

    elapsed = time.time() - start_time
    measurements = result['measurement_tuples']

    print(f"\n✅ Processed {len(measurements):,} measurements in {elapsed:.2f}s")
    print(f"⚡ Throughput: {len(measurements) / elapsed:,.0f} measurements/second")

    # Show sample
    print(f"\n📋 Sample Measurements (first 3):")
    for i, m in enumerate(measurements[:3], 1):
        *base_fields, extra_fields = m
        print(f"\n--- Measurement #{i} ---")
        print(f"Test #: {base_fields[11]}")
        print(f"Extra fields: {extra_fields}")


def test_use_case_3_multiple_record_types(stdf_file: str):
    """Use Case 3: Add fields from MULTIPLE record types"""
    print("\n" + "=" * 70)
    print("🔬 USE CASE 3: Add fields from FTR + PTR (combined!)")
    print("=" * 70)

    start_time = time.time()

    result = stdf_parser_cpp.process_stdf_file_measurements(
        stdf_file,
        extra_fields=[
            ('FTR', ['VECT_NAM', 'TIME_SET', 'OP_CODE']),
            ('PTR', ['HI_LIMIT', 'LO_LIMIT'])
        ]
    )

    elapsed = time.time() - start_time
    measurements = result['measurement_tuples']

    print(f"\n✅ Processed {len(measurements):,} measurements in {elapsed:.2f}s")
    print(f"⚡ Throughput: {len(measurements) / elapsed:,.0f} measurements/second")

    # Show sample
    print(f"\n📋 Sample Measurements (first 3):")
    for i, m in enumerate(measurements[:3], 1):
        *base_fields, extra_fields = m
        print(f"\n--- Measurement #{i} ---")
        print(f"Test #: {base_fields[11]}")
        print(f"Extra fields (FTR + PTR): {extra_fields}")


def test_use_case_4_no_extra_fields(stdf_file: str):
    """Use Case 4: No extra fields (base 13 fields only)"""
    print("\n" + "=" * 70)
    print("🔬 USE CASE 4: No extra fields (base 13 fields)")
    print("=" * 70)

    start_time = time.time()

    result = stdf_parser_cpp.process_stdf_file_measurements(stdf_file)

    elapsed = time.time() - start_time
    measurements = result['measurement_tuples']

    print(f"\n✅ Processed {len(measurements):,} measurements in {elapsed:.2f}s")
    print(f"⚡ Throughput: {len(measurements) / elapsed:,.0f} measurements/second")

    # Show sample
    print(f"\n📋 Sample Measurements (first 3):")
    for i, m in enumerate(measurements[:3], 1):
        *base_fields, extra_fields = m
        print(f"\n--- Measurement #{i} ---")
        print(f"Test #: {base_fields[11]}")
        print(f"Extra fields (empty dict): {extra_fields}")


def main():
    """Main function"""
    parser = argparse.ArgumentParser(
        description="Test Runtime Flexible API - Approach 3",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument("--stdf-file", required=True, help="Path to STDF file")

    args = parser.parse_args()

    # Validate input file
    if not os.path.exists(args.stdf_file):
        print(f"❌ File not found: {args.stdf_file}")
        return 1

    print("\n🚀 Runtime Flexible API - Test Suite")
    print("=" * 70)
    print(f"Platform: {platform.system()} ({platform.machine()})")
    print(f"Input: {args.stdf_file}")

    # Test all use cases
    test_use_case_1_ftr_fields(args.stdf_file)
    test_use_case_2_ptr_fields(args.stdf_file)
    test_use_case_3_multiple_record_types(args.stdf_file)
    test_use_case_4_no_extra_fields(args.stdf_file)

    print("\n" + "=" * 70)
    print("✅ All Tests Complete!")
    print("\n💡 Key Benefits:")
    print("   ✅ Python specifies fields at runtime (NO C++ rebuild!)")
    print("   ✅ C++ does all 3M lookups (FAST - no Python loops!)")
    print("   ✅ Flexible - different fields per use case")
    print("   ✅ Single parse - file read ONCE")

    return 0


if __name__ == "__main__":
    sys.exit(main())
