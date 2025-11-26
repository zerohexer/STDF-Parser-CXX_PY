#!/usr/bin/env python3
"""
MES Emulator - Simulate FactoryLook SetStdfFile API calls

Use this to test the API without actual MES integration.
Simulates CMOS Move Out (MVOU) trigger.

Usage:
    # Single lot
    python emulate_mes_call.py \\
        --lot HRG3201Y.09 \\
        --operation 5264 \\
        --equipment 3CMT0101 \\
        --product-type KEWGBCLD1U \\
        --product-class "PCBcast Pixlog 2217"

    # With custom API endpoint
    python emulate_mes_call.py \\
        --api-url http://192.168.1.100:8000/SetStdfFile \\
        --lot HRG3201Y.09 \\
        ...
"""

import sys
import argparse
import requests
import json
from typing import Dict


def call_set_stdf_file_api(api_url: str, params: Dict) -> Dict:
    """
    Call SetStdfFile API endpoint

    Args:
        api_url: Full API URL (e.g., http://localhost:8000/SetStdfFile)
        params: Request parameters

    Returns:
        API response dict
    """
    print("=" * 70)
    print("MES Emulator - Calling SetStdfFile API")
    print("=" * 70)
    print(f"API URL: {api_url}")
    print(f"Request:")
    print(json.dumps(params, indent=2))
    print("-" * 70)

    try:
        response = requests.post(api_url, json=params, timeout=300)
        response.raise_for_status()

        result = response.json()
        print(f"Response Status: {response.status_code}")
        print(f"Response:")
        print(json.dumps(result, indent=2))
        print("=" * 70)

        # Print summary
        print(f"\n✅ Status: {result['status'].upper()}")
        print(f"   Lot: {result['lot']}")
        print(f"   Files Total: {result['files_total']}")
        print(f"   Files Processed: {result['files_processed']}")
        print(f"   Files Skipped: {result['files_skipped']} (already processed)")
        print(f"   Files Failed: {result['files_failed']}")
        print(f"   Total Measurements: {result['total_measurements']}")
        print(f"   Processing Time: {result['processing_time_seconds']}s")
        print(f"\n   Message: {result['message']}")

        return result

    except requests.exceptions.ConnectionError:
        print(f"\n❌ ERROR: Could not connect to API server at {api_url}")
        print("   Make sure the API server is running:")
        print("   python stdf_api_service.py --network-path <path>")
        sys.exit(1)
    except requests.exceptions.Timeout:
        print(f"\n❌ ERROR: Request timeout (>300s)")
        print("   Processing is taking too long. Check server logs.")
        sys.exit(1)
    except requests.exceptions.HTTPError as e:
        print(f"\n❌ ERROR: HTTP {e.response.status_code}")
        print(f"   {e.response.text}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        sys.exit(1)


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='MES Emulator - Test SetStdfFile API',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic usage
  python emulate_mes_call.py \\
      --lot HRG3201Y.09 \\
      --operation 5264 \\
      --operation-name "CMOS Pre-Test (Room)" \\
      --equipment 3CMT0101 \\
      --product-type KEWGBCLD1U \\
      --product-class "PCBcast Pixlog 2217"

  # Custom API URL
  python emulate_mes_call.py \\
      --api-url http://192.168.1.100:8000/SetStdfFile \\
      --lot HRG3201Y.09 \\
      --operation 5264 \\
      --equipment 3CMT0101 \\
      --product-type KEWGBCLD1U \\
      --product-class "PCBcast Pixlog 2217"

  # From SOAP message values
  python emulate_mes_call.py \\
      --lot HRG3201Y.09 \\
      --operation 5264 \\
      --operation-name "CMOS Pre-Test (Room)" \\
      --equipment 3CMT0101 \\
      --product-type KEWGBCLD1U \\
      --product-class "PCBcast Pixlog 2217"
        """
    )

    parser.add_argument('--api-url', default='http://localhost:8000/SetStdfFile',
                       help='API endpoint URL (default: http://localhost:8000/SetStdfFile)')
    parser.add_argument('--lot', '--lot-number', required=True,
                       help='Lot number (e.g., HRG3201Y.09)')
    parser.add_argument('--operation', '--operation-number', required=True,
                       help='Operation number (e.g., 5264)')
    parser.add_argument('--operation-name', default='CMOS Pre-Test',
                       help='Operation name (default: CMOS Pre-Test)')
    parser.add_argument('--equipment', '--equipment-number', required=True,
                       help='Equipment number (e.g., 3CMT0101)')
    parser.add_argument('--product-type', required=True,
                       help='Product type (e.g., KEWGBCLD1U)')
    parser.add_argument('--product-class', required=True,
                       help='Product class (e.g., "PCBcast Pixlog 2217")')

    args = parser.parse_args()

    # Build request parameters
    params = {
        "LotNumber": args.lot,
        "OperationNumber": args.operation,
        "OperationName": args.operation_name,
        "EquipmentNumber": args.equipment,
        "ProductType": args.product_type,
        "ProductClass": args.product_class
    }

    # Call API
    result = call_set_stdf_file_api(args.api_url, params)

    # Exit with appropriate code
    if result['status'] == 'success':
        sys.exit(0)
    elif result['status'] == 'partial':
        sys.exit(2)  # Some files processed
    else:
        sys.exit(1)  # All failed


if __name__ == '__main__':
    main()
