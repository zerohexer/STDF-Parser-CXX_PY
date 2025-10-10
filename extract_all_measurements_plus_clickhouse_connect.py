#!/usr/bin/env python3
"""
Extract ALL Measurements + ClickHouse Integration - CLEANED VERSION
===================================================================
Simplified version with all legacy/unused code removed.

Uses database-aware C++ processing for perfect ID alignment.
"""

import os
import platform
import time
import argparse
import sys
import hashlib
from datetime import datetime

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
    exit(1)

try:
    from clickhouse_driver import Client
    from clickhouse_utils import setup_clickhouse_schema
    print("✅ ClickHouse integration loaded")
except ImportError as e:
    print(f"❌ ClickHouse integration not available: {e}")
    exit(1)


class STDFProcessor:
    """Simplified STDF processor with C++ parsing + ClickHouse integration"""

    def __init__(self, enable_clickhouse=True):
        self.enable_clickhouse = enable_clickhouse
        self.measurement_tuples = []
        self.new_device_mappings = []
        self.new_param_mappings = []
        self.processing_stats = {}
        self.current_file_hash = None

        print(f"🚀 STDFProcessor initialized (cleaned version)")
        print(f"   ClickHouse: {'✅ Enabled' if enable_clickhouse else '❌ Disabled'}")

    def _generate_file_hash(self, file_path):
        """Generate MD5 hash for deduplication"""
        hash_md5 = hashlib.md5()
        try:
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_md5.update(chunk)
            return hash_md5.hexdigest()
        except Exception as e:
            print(f"⚠️  Error generating file hash: {e}")
            return None

    def _is_file_already_processed(self, file_hash, client):
        """Check if file already processed"""
        if not file_hash or not client:
            return False

        try:
            query = f"SELECT COUNT(*) FROM measurements WHERE file_hash = '{file_hash}' LIMIT 1"
            rows = client.execute(query)
            return rows and rows[0][0] > 0
        except Exception as e:
            print(f"⚠️  Error checking file hash: {e}")
            return False

    def _load_existing_mappings(self, host, port, database, user, password):
        """Load existing device/parameter mappings from ClickHouse"""
        try:
            client = Client(host=host, port=port, database=database, user=user, password=password)

            # Load devices
            device_mappings = []
            try:
                device_results = client.execute("SELECT wld_device_dmc, wld_id FROM device_mapping")
                device_mappings = [(dmc, did) for dmc, did in device_results]
                print(f"📊 Loaded {len(device_mappings)} existing device mappings")
            except Exception as e:
                print(f"⚠️  No existing device mappings: {e}")

            # Load parameters
            param_mappings = []
            try:
                param_results = client.execute("SELECT wtp_param_name, wtp_id FROM parameter_info")
                param_mappings = [(pname, pid) for pname, pid in param_results]
                print(f"📊 Loaded {len(param_mappings)} existing parameter mappings")
            except Exception as e:
                print(f"⚠️  No existing parameter mappings: {e}")

            return device_mappings, param_mappings

        except Exception as e:
            print(f"⚠️  Error loading mappings: {e}")
            return [], []

    def extract_measurements(self, stdf_file_path, ch_host='localhost', ch_port=9000,
                           ch_database='default', ch_user='default', ch_password=''):
        """Extract measurements using database-aware C++ processing"""
        print(f"\n📄 Processing: {os.path.basename(stdf_file_path)}")
        start_time = time.time()

        # Generate file hash for deduplication
        print(f"🔍 Checking file deduplication...")
        file_hash = self._generate_file_hash(stdf_file_path)
        if file_hash:
            print(f"   📄 File hash: {file_hash}")
            self.current_file_hash = file_hash

            # Check if already processed
            try:
                temp_client = Client(host=ch_host, port=ch_port, database=ch_database,
                                    user=ch_user, password=ch_password)

                if self._is_file_already_processed(file_hash, temp_client):
                    print(f"⚠️  File already processed, skipping")
                    self.measurement_tuples = []
                    self.new_device_mappings = []
                    self.new_param_mappings = []
                    self.processing_stats = {
                        'skipped_duplicate': True,
                        'file_hash': file_hash,
                        'total_measurements': 0
                    }
                    return []
                else:
                    print(f"✅ File not previously processed")
            except Exception as e:
                print(f"⚠️  Could not check for duplicates: {e}")

        # Load existing mappings from database
        print(f"🔧 Loading existing mappings from ClickHouse...")
        device_mappings, param_mappings = self._load_existing_mappings(
            ch_host, ch_port, ch_database, ch_user, ch_password
        )

        # Process with database-aware C++
        result = stdf_parser_cpp.process_stdf_with_database_mappings(
            stdf_file_path,
            device_mappings,
            param_mappings,
            self.current_file_hash or ""
        )

        # Extract results
        self.measurement_tuples = result.get('measurement_tuples', [])
        self.new_device_mappings = result.get('new_device_mappings', [])
        self.new_param_mappings = result.get('new_param_mappings', [])

        total_time = time.time() - start_time

        print(f"🚀 C++ processing completed:")
        print(f"   📊 Records: {result.get('total_records', 0):,}")
        print(f"   📊 Measurements: {len(self.measurement_tuples):,}")
        print(f"   ⏱️  Parsing: {result.get('parsing_time', 0):.2f}s")
        print(f"   ⏱️  Processing: {result.get('processing_time', 0):.2f}s")
        print(f"   ⏱️  Total: {total_time:.2f}s")
        print(f"   📊 New devices: {len(self.new_device_mappings)}")
        print(f"   📊 New params: {len(self.new_param_mappings)}")

        if total_time > 0:
            throughput = len(self.measurement_tuples) / total_time
            print(f"   🚀 Throughput: {throughput:,.0f} measurements/second")

        # Store stats
        self.processing_stats = {
            'cpp_parsing_time': result.get('parsing_time', 0),
            'cpp_processing_time': result.get('processing_time', 0),
            'total_processing_time': total_time,
            'total_measurements': len(self.measurement_tuples),
            'total_records': result.get('total_records', 0)
        }

        return self.measurement_tuples

    def push_to_clickhouse(self, host='localhost', port=9000, database='default',
                          user='default', password=''):
        """Push measurements to ClickHouse"""
        if not self.enable_clickhouse:
            print("⚠️  ClickHouse integration disabled")
            return False

        if not self.measurement_tuples:
            print("⚠️  No measurements to push")
            return False

        print(f"\n🚀 Pushing to ClickHouse...")
        start_time = time.time()

        try:
            # Setup connection and schema
            client = Client(host=host, port=port, database=database, user=user, password=password,
                          settings={'max_insert_block_size': 1000000, 'max_threads': 16})
            setup_clickhouse_schema(client)

            # Insert new mappings
            if self.new_device_mappings:
                device_data = [(did, dmc) for dmc, did in self.new_device_mappings]
                client.execute("INSERT INTO device_mapping (wld_id, wld_device_dmc) VALUES", device_data)
                print(f"✅ Pushed {len(device_data)} new device mappings")

            if self.new_param_mappings:
                param_data = [(pid, pname) for pname, pid in self.new_param_mappings]
                client.execute("INSERT INTO parameter_info (wtp_id, wtp_param_name) VALUES", param_data)
                print(f"✅ Pushed {len(param_data)} new parameter mappings")

            # Convert tuples to ClickHouse format
            current_time = datetime.now()
            clickhouse_tuples = [
                (wld_id, wtp_id, wp_pos_x, wp_pos_y, wptm_value, current_time,
                 test_flag, segment, file_hash)
                for (wld_id, wtp_id, wp_pos_x, wp_pos_y, wptm_value, test_flag,
                     segment, file_hash, *_) in self.measurement_tuples
            ]

            # Push measurements
            print(f"🚀 Inserting {len(clickhouse_tuples):,} measurements...")
            client.execute(
                "INSERT INTO measurements (wld_id, wtp_id, wp_pos_x, wp_pos_y, wptm_value, "
                "wptm_created_date, test_flag, segment, file_hash) VALUES",
                clickhouse_tuples
            )

            elapsed = time.time() - start_time
            throughput = len(clickhouse_tuples) / elapsed if elapsed > 0 else 0

            print(f"✅ ClickHouse push completed!")
            print(f"   📊 Measurements: {len(clickhouse_tuples):,}")
            print(f"   ⏱️  Time: {elapsed:.2f}s")
            print(f"   🚀 Throughput: {throughput:,.0f} measurements/second")

            self.processing_stats['clickhouse_push_time'] = elapsed
            return True

        except Exception as e:
            print(f"❌ ClickHouse push failed: {e}")
            import traceback
            traceback.print_exc()
            return False

    def print_statistics(self):
        """Print processing statistics"""
        print(f"\n📈 STATISTICS:")
        print("=" * 60)

        if self.processing_stats.get('skipped_duplicate'):
            print(f"⏭️  FILE SKIPPED (already processed)")
            print(f"  Hash: {self.processing_stats.get('file_hash', 'N/A')}")
            return

        print(f"Processing:")
        print(f"  Records: {self.processing_stats.get('total_records', 0):,}")
        print(f"  Measurements: {self.processing_stats.get('total_measurements', 0):,}")
        print(f"  Parsing time: {self.processing_stats.get('cpp_parsing_time', 0):.2f}s")
        print(f"  Processing time: {self.processing_stats.get('cpp_processing_time', 0):.2f}s")
        print(f"  Total time: {self.processing_stats.get('total_processing_time', 0):.2f}s")

        if 'clickhouse_push_time' in self.processing_stats:
            print(f"\nClickHouse:")
            print(f"  Push time: {self.processing_stats.get('clickhouse_push_time', 0):.2f}s")

        print("=" * 60)


def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="STDF to ClickHouse (Cleaned Version)")
    parser.add_argument("--stdf-file", required=True, help="Path to STDF file")
    parser.add_argument("--push-clickhouse", action="store_true", help="Push to ClickHouse")
    parser.add_argument("--ch-host", default="localhost", help="ClickHouse host")
    parser.add_argument("--ch-port", type=int, default=9000, help="ClickHouse port")
    parser.add_argument("--ch-database", default="default", help="ClickHouse database")
    parser.add_argument("--ch-user", default="default", help="ClickHouse user")
    parser.add_argument("--ch-password", default="", help="ClickHouse password")

    args = parser.parse_args()

    print("🚀 STDF to ClickHouse - Cleaned Version")
    print("=" * 60)

    if not os.path.exists(args.stdf_file):
        print(f"❌ File not found: {args.stdf_file}")
        return 1

    # Create processor
    processor = STDFProcessor(enable_clickhouse=args.push_clickhouse)

    # Extract measurements
    measurements = processor.extract_measurements(
        args.stdf_file,
        ch_host=args.ch_host,
        ch_port=args.ch_port,
        ch_database=args.ch_database,
        ch_user=args.ch_user,
        ch_password=args.ch_password
    )

    # Push to ClickHouse if requested
    if args.push_clickhouse and measurements:
        success = processor.push_to_clickhouse(
            host=args.ch_host,
            port=args.ch_port,
            database=args.ch_database,
            user=args.ch_user,
            password=args.ch_password
        )
        if not success:
            return 1

    # Print stats
    processor.print_statistics()

    return 0


if __name__ == "__main__":
    sys.exit(main())
