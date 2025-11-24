#!/usr/bin/env python3
"""
Setup script for STDF ingestion directory structure

Creates the recommended directory hierarchy for watchdog-based automated ingestion.
"""

import os
import sys
from pathlib import Path
from typing import List


def create_directory_structure(base_path: str = "/data/stdf-ingestion",
                                 example_facilities: List[str] = None,
                                 example_lots: List[str] = None,
                                 example_products: List[str] = None,
                                 example_programs: List[str] = None):
    """
    Create the full ingestion directory structure with optional example hierarchies

    Args:
        base_path: Root directory for ingestion system
        example_facilities: List of facility names to create example structure for
        example_lots: List of lot names
        example_products: List of product names
        example_programs: List of test program names
    """
    base = Path(base_path)

    # Top-level directories
    top_level = ['incoming', 'processing', 'processed', 'failed', 'archive']

    print(f"Creating STDF ingestion directory structure at: {base}")
    print("=" * 70)

    for dir_name in top_level:
        dir_path = base / dir_name
        dir_path.mkdir(parents=True, exist_ok=True)
        print(f"✓ Created: {dir_path}")

    # Create example hierarchies if provided
    if example_facilities:
        print("\nCreating example directory hierarchies:")
        print("-" * 70)

        for facility in example_facilities:
            for lot in (example_lots or ['LOT_EXAMPLE']):
                for product in (example_products or ['PRODUCT_EXAMPLE']):
                    for program in (example_programs or ['TEST_PROGRAM_EXAMPLE']):
                        # Create in incoming directory only
                        example_path = base / 'incoming' / facility / lot / product / program
                        example_path.mkdir(parents=True, exist_ok=True)
                        print(f"✓ {example_path}")

    # Create README in base directory
    readme_path = base / "README.txt"
    with open(readme_path, 'w') as f:
        f.write("""STDF Ingestion Directory Structure
=====================================

Directory Layout:
-----------------

incoming/       ← Place STDF files here (watchdog monitors this)
    {FACILITY}/
        {LOT}/
            {PRODUCT}/
                {TEST_PROGRAM}/
                    *.stdf

processing/     ← Files currently being processed
    {same structure as incoming}

processed/      ← Successfully ingested files
    {FACILITY}/
        {LOT}/
            {PRODUCT}/
                {TEST_PROGRAM}/
                    {YYYY}/
                        {MM}/
                            {DD}/
                                *.stdf

failed/         ← Files that failed processing
    {same structure + *.error.log files}

archive/        ← Long-term storage (manual archiving)
    {same structure}


Usage:
------

1. Start the watchdog service:
   python watchdog_ingestion.py --base-path /data/stdf-ingestion

2. Copy STDF files to incoming directory following the hierarchy:
   cp myfile.stdf /data/stdf-ingestion/incoming/OSBE25/LOT123/PRODUCT_A/TEST_V1/

3. Watchdog automatically:
   - Detects new .stdf files
   - Moves to processing/
   - Parses and pushes to ClickHouse
   - Moves to processed/{YYYY}/{MM}/{DD}/ on success
   - Moves to failed/ with error log on failure


Example File Path:
------------------

/data/stdf-ingestion/incoming/OSBE25/KEWGBCLD1U/BE_HRG3301Y.06/Prod_TPP202_03/test_data.stdf

Breakdown:
  FACILITY:     OSBE25
  LOT:          KEWGBCLD1U
  PRODUCT:      BE_HRG3301Y.06
  TEST_PROGRAM: Prod_TPP202_03
  FILE:         test_data.stdf

After successful processing, moved to:
/data/stdf-ingestion/processed/OSBE25/KEWGBCLD1U/BE_HRG3301Y.06/Prod_TPP202_03/2025/11/24/test_data.stdf


Notes:
------

- Directory structure is FLEXIBLE - only create levels you need
- Watchdog works with any depth (automatically creates missing parent dirs)
- File naming convention is up to you (only .stdf extension matters)
- Metadata extracted from STDF headers takes precedence over directory names
""")

    print(f"\n✓ Created README: {readme_path}")
    print("\n" + "=" * 70)
    print("Directory structure setup complete!")
    print(f"\nNext steps:")
    print(f"1. Copy STDF files to: {base / 'incoming' / '<FACILITY>' / '<LOT>' / '<PRODUCT>' / '<PROGRAM>'}")
    print(f"2. Start watchdog: python watchdog_ingestion.py --base-path {base}")


def main():
    """CLI interface for directory setup"""
    import argparse

    parser = argparse.ArgumentParser(
        description='Setup STDF ingestion directory structure',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic setup (creates empty structure)
  python setup_ingestion_dirs.py

  # Setup with example facility structure
  python setup_ingestion_dirs.py --facilities OSBE25 OSBE26

  # Full example with all levels
  python setup_ingestion_dirs.py \\
      --facilities OSBE25 OSBE26 \\
      --lots LOT001 LOT002 \\
      --products PRODUCT_A PRODUCT_B \\
      --programs TEST_V1 TEST_V2

  # Custom base path
  python setup_ingestion_dirs.py --base-path /mnt/data/stdf
        """
    )

    parser.add_argument('--base-path', default='/data/stdf-ingestion',
                        help='Base directory for ingestion (default: /data/stdf-ingestion)')
    parser.add_argument('--facilities', nargs='+',
                        help='Facility names to create example structure (e.g., OSBE25 OSBE26)')
    parser.add_argument('--lots', nargs='+',
                        help='Lot names for example structure (e.g., LOT001 LOT002)')
    parser.add_argument('--products', nargs='+',
                        help='Product names for example structure (e.g., PRODUCT_A PRODUCT_B)')
    parser.add_argument('--programs', nargs='+',
                        help='Test program names for example structure (e.g., TEST_V1 TEST_V2)')

    args = parser.parse_args()

    try:
        create_directory_structure(
            base_path=args.base_path,
            example_facilities=args.facilities,
            example_lots=args.lots,
            example_products=args.products,
            example_programs=args.programs
        )
        return 0
    except Exception as e:
        print(f"\nERROR: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
