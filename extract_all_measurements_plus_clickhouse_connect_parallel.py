#!/usr/bin/env python3
"""
TRUE Parallel STDF Processing with Perfect ID Alignment
========================================================
Uses ProcessPoolExecutor for REAL parallelism (not limited by GIL)
Maintains perfect device/parameter ID alignment using database-aware C++ processing

Key Strategy:
1. Load existing device/param mappings from database ONCE (main process)
2. Pass mappings to each worker process
3. Each worker calls C++ process_stdf_with_database_mappings() with:
   - Existing mappings (for consistent IDs)
   - Returns NEW mappings found in that file
4. Main process collects ALL new mappings and inserts to database
5. Mega-push all measurements in single operation

Benefits:
- TRUE parallel processing (separate processes, no GIL)
- Perfect ID alignment (C++ handles it with database-aware mode)
- No race conditions (database handles ID conflicts)
- Minimal overhead (only new mappings returned per file)
"""

import os
import platform
import time
import argparse
import sys
import hashlib
from datetime import datetime
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

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


def generate_file_hash(file_path):
    """Generate MD5 hash for file"""
    hash_md5 = hashlib.md5()
    try:
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    except Exception as e:
        print(f"⚠️ Error generating hash for {file_path}: {e}")
        return ""


def process_single_file_with_mappings(args):
    """
    Worker function: Process ONE file with existing database mappings

    This runs in a SEPARATE PROCESS (true parallelism!)

    Args:
        args: tuple of (file_path, device_mappings, param_mappings, ch_config)

    Returns:
        dict with measurements, new mappings, and stats
    """
    file_path, device_mappings, param_mappings, ch_config = args

    try:
        print(f"\n🔄 Worker processing: {os.path.basename(file_path)}")
        start_time = time.time()

        # Generate file hash for deduplication
        file_hash = generate_file_hash(file_path)

        # Check if file already processed (deduplication)
        if file_hash and ch_config:
            try:
                client = Client(
                    host=ch_config['host'],
                    port=ch_config['port'],
                    database=ch_config['database'],
                    user=ch_config['user'],
                    password=ch_config['password']
                )
                query = f"SELECT COUNT(*) FROM measurements WHERE file_hash = '{file_hash}' LIMIT 1"
                rows = client.execute(query)
                if rows and rows[0][0] > 0:
                    print(f"⏭️ {os.path.basename(file_path)} already processed (hash: {file_hash[:8]}...)")
                    return {
                        'file': file_path,
                        'skipped': True,
                        'measurements': 0,
                        'new_devices': 0,
                        'new_params': 0,
                        'time': time.time() - start_time
                    }
            except Exception as e:
                print(f"⚠️ Could not check for duplicates: {e}")

        # 🚀 DATABASE-AWARE C++ PROCESSING
        # C++ will use existing mappings and return ONLY new mappings found
        result = stdf_parser_cpp.process_stdf_with_database_mappings(
            file_path,
            device_mappings,  # Existing mappings passed in
            param_mappings,   # Existing mappings passed in
            file_hash         # Pass file hash for consistency
        )

        measurements = result['measurement_tuples']
        new_device_mappings = result['new_device_mappings']  # Only NEW devices
        new_param_mappings = result['new_param_mappings']    # Only NEW params

        elapsed = time.time() - start_time

        print(f"✅ {os.path.basename(file_path)}: {len(measurements):,} measurements in {elapsed:.2f}s")
        print(f"   📊 New devices: {len(new_device_mappings)}, New params: {len(new_param_mappings)}")

        return {
            'file': file_path,
            'skipped': False,
            'measurements': measurements,
            'new_device_mappings': new_device_mappings,
            'new_param_mappings': new_param_mappings,
            'total_measurements': len(measurements),
            'new_devices': len(new_device_mappings),
            'new_params': len(new_param_mappings),
            'time': elapsed
        }

    except Exception as e:
        print(f"❌ Error processing {os.path.basename(file_path)}: {e}")
        import traceback
        traceback.print_exc()
        return {
            'file': file_path,
            'skipped': False,
            'measurements': [],
            'new_device_mappings': [],
            'new_param_mappings': [],
            'total_measurements': 0,
            'new_devices': 0,
            'new_params': 0,
            'time': 0,
            'error': str(e)
        }


def load_existing_mappings(client):
    """Load existing device and parameter mappings from database"""
    device_mappings = []
    param_mappings = []

    try:
        # Load devices
        device_results = client.execute("SELECT wld_device_dmc, wld_id FROM device_mapping")
        device_mappings = [(device_dmc, device_id) for device_dmc, device_id in device_results]
        print(f"📥 Loaded {len(device_mappings)} existing device mappings")
    except Exception as e:
        print(f"⚠️ No existing device mappings: {e}")

    try:
        # Load parameters
        param_results = client.execute("SELECT wtp_param_name, wtp_id FROM parameter_info")
        param_mappings = [(param_name, param_id) for param_name, param_id in param_results]
        print(f"📥 Loaded {len(param_mappings)} existing parameter mappings")
    except Exception as e:
        print(f"⚠️ No existing parameter mappings: {e}")

    return device_mappings, param_mappings


def insert_new_mappings(client, all_new_devices, all_new_params):
    """Insert all NEW mappings collected from workers"""
    # Deduplicate across all files
    unique_devices = {}
    for device_dmc, device_id in all_new_devices:
        if device_dmc not in unique_devices:
            unique_devices[device_dmc] = device_id

    unique_params = {}
    for param_name, param_id in all_new_params:
        if param_name not in unique_params:
            unique_params[param_name] = param_id

    # Insert devices
    if unique_devices:
        device_data = [(device_id, device_dmc) for device_dmc, device_id in unique_devices.items()]
        try:
            client.execute(
                "INSERT INTO device_mapping (wld_id, wld_device_dmc) VALUES",
                device_data
            )
            print(f"✅ Inserted {len(device_data)} new device mappings")
        except Exception as e:
            print(f"⚠️ Error inserting devices (may already exist): {e}")

    # Insert parameters
    if unique_params:
        param_data = [(param_id, param_name) for param_name, param_id in unique_params.items()]
        try:
            client.execute(
                "INSERT INTO parameter_info (wtp_id, wtp_param_name) VALUES",
                param_data
            )
            print(f"✅ Inserted {len(param_data)} new parameter mappings")
        except Exception as e:
            print(f"⚠️ Error inserting params (may already exist): {e}")


def mega_push_measurements(client, all_measurements):
    """Push all measurements in single mega operation"""
    if not all_measurements:
        return

    print(f"\n🚀 MEGA-PUSH: {len(all_measurements):,} measurements...")
    start_time = time.time()

    # Convert tuples to ClickHouse format
    current_time = datetime.now()
    clickhouse_tuples = []

    for tuple_data in all_measurements:
        # Unpack 14-field tuple (13 base + 1 extra_fields dict)
        (wld_id, wtp_id, wp_pos_x, wp_pos_y, wptm_value, test_flag, segment, file_hash,
         wld_device_dmc, wtp_param_name, units, test_num, test_flg, extra_fields) = tuple_data

        clickhouse_tuples.append((
            wld_id,
            wtp_id,
            wp_pos_x,
            wp_pos_y,
            wptm_value,
            current_time,
            test_flag,
            segment,
            file_hash
        ))

    # Single insert for ALL measurements
    client.execute(
        "INSERT INTO measurements (wld_id, wtp_id, wp_pos_x, wp_pos_y, wptm_value, wptm_created_date, test_flag, segment, file_hash) VALUES",
        clickhouse_tuples
    )

    elapsed = time.time() - start_time
    throughput = len(all_measurements) / elapsed if elapsed > 0 else 0

    print(f"✅ MEGA-PUSH COMPLETE: {len(all_measurements):,} measurements in {elapsed:.2f}s")
    print(f"🚀 Throughput: {throughput:,.0f} measurements/second")


def main():
    parser = argparse.ArgumentParser(description="TRUE Parallel STDF Processing")
    parser.add_argument("--directory", required=True, help="Directory with STDF files")
    parser.add_argument("--workers", type=int, default=3, help="Number of parallel workers (default: 3)")
    parser.add_argument("--push-batch-size", type=int, default=8, help="Push to ClickHouse after N files processed (default: 8)")
    parser.add_argument("--push-clickhouse", action="store_true", help="Push to ClickHouse")
    parser.add_argument("--ch-host", default="localhost", help="ClickHouse host")
    parser.add_argument("--ch-port", type=int, default=9000, help="ClickHouse port")
    parser.add_argument("--ch-database", default="default", help="ClickHouse database")
    parser.add_argument("--ch-user", default="default", help="ClickHouse user")
    parser.add_argument("--ch-password", default="", help="ClickHouse password")

    args = parser.parse_args()

    print(f"\n🚀 TRUE PARALLEL STDF PROCESSOR")
    print("=" * 70)
    print(f"Directory: {args.directory}")
    print(f"Workers: {args.workers}")
    print(f"Push Batch Size: {args.push_batch_size} files")
    print(f"ClickHouse: {'✅ Enabled' if args.push_clickhouse else '❌ Disabled'}")
    if args.push_clickhouse:
        print(f"ClickHouse: {args.ch_host}:{args.ch_port}/{args.ch_database}")

    # Find STDF files
    stdf_files = list(Path(args.directory).glob("*.stdf"))
    if not stdf_files:
        print(f"❌ No STDF files found in {args.directory}")
        return 1

    print(f"\n📁 Found {len(stdf_files)} STDF files")

    total_start = time.time()

    # Setup ClickHouse and load existing mappings
    client = None
    device_mappings = []
    param_mappings = []
    ch_config = None

    if args.push_clickhouse:
        print(f"\n🔧 Setting up ClickHouse connection...")
        try:
            client = Client(
                host=args.ch_host,
                port=args.ch_port,
                database=args.ch_database,
                user=args.ch_user,
                password=args.ch_password
            )
            setup_clickhouse_schema(client)

            # Load existing mappings
            device_mappings, param_mappings = load_existing_mappings(client)

            ch_config = {
                'host': args.ch_host,
                'port': args.ch_port,
                'database': args.ch_database,
                'user': args.ch_user,
                'password': args.ch_password
            }

        except Exception as e:
            print(f"❌ ClickHouse setup failed: {e}")
            return 1

    # TRUE PARALLEL PROCESSING WITH BATCHED PUSHING
    print(f"\n🚀 Starting TRUE PARALLEL processing with {args.workers} workers...")
    print(f"📦 Will push to ClickHouse every {args.push_batch_size} files processed")
    print(f"⚠️  IMPORTANT: Workers will WAIT after each batch until push completes")
    parallel_start = time.time()

    all_measurements = []
    all_new_devices = []
    all_new_params = []
    processed_files = 0
    skipped_files = 0
    total_pushed_measurements = 0
    batch_number = 0

    # Process files in batches
    total_files = len(stdf_files)
    file_index = 0

    while file_index < total_files:
        # Determine batch size (process up to push_batch_size files)
        batch_end = min(file_index + args.push_batch_size, total_files)
        current_batch_files = stdf_files[file_index:batch_end]

        print(f"\n🔄 Processing batch of {len(current_batch_files)} files ({file_index + 1} to {batch_end} of {total_files})...")

        # Prepare worker arguments for this batch
        worker_args = [
            (str(file), device_mappings, param_mappings, ch_config)
            for file in current_batch_files
        ]

        # ProcessPoolExecutor for TRUE parallelism - ONLY for current batch
        with ProcessPoolExecutor(max_workers=args.workers) as executor:
            # Submit current batch files
            future_to_file = {
                executor.submit(process_single_file_with_mappings, arg): arg[0]
                for arg in worker_args
            }

            # Collect results as they complete
            for future in as_completed(future_to_file):
                file_path = future_to_file[future]
                try:
                    result = future.result()

                    if result.get('skipped'):
                        skipped_files += 1
                        continue

                    # Collect measurements
                    if result['measurements']:
                        all_measurements.extend(result['measurements'])

                    # Collect new mappings
                    all_new_devices.extend(result['new_device_mappings'])
                    all_new_params.extend(result['new_param_mappings'])

                    processed_files += 1

                except Exception as e:
                    print(f"❌ Worker error for {os.path.basename(file_path)}: {e}")

        # Batch complete - now push to ClickHouse BEFORE processing next batch
        if all_measurements or all_new_devices or all_new_params:
            batch_number += 1
            print(f"\n📦 BATCH {batch_number} COMPLETE: Processed {len(current_batch_files)} files")
            print(f"🔒 WAITING: Pushing {len(all_measurements):,} measurements to ClickHouse...")

            # Insert new mappings first
            if args.push_clickhouse and client and (all_new_devices or all_new_params):
                insert_new_mappings(client, all_new_devices, all_new_params)

                # Extend with unique entries only (deduplicate before extending)
                unique_new_devices = {}
                for device_dmc, device_id in all_new_devices:
                    if device_dmc not in unique_new_devices:
                        unique_new_devices[device_dmc] = device_id

                unique_new_params = {}
                for param_name, param_id in all_new_params:
                    if param_name not in unique_new_params:
                        unique_new_params[param_name] = param_id

                # Extend existing mappings with unique new entries
                for device_dmc, device_id in unique_new_devices.items():
                    device_mappings.append((device_dmc, device_id))

                for param_name, param_id in unique_new_params.items():
                    param_mappings.append((param_name, param_id))

                print(f"✅ Extended mappings: +{len(unique_new_devices)} devices, +{len(unique_new_params)} params")
                print(f"📊 Total mappings now: {len(device_mappings)} devices, {len(param_mappings)} params")

                all_new_devices = []
                all_new_params = []

            # Push measurements batch
            if args.push_clickhouse and client and all_measurements:
                mega_push_measurements(client, all_measurements)
                total_pushed_measurements += len(all_measurements)
                all_measurements = []  # Clear batch

            print(f"✅ Batch {batch_number} pushed successfully ({total_pushed_measurements:,} total)")
            print(f"➡️  Ready to process next batch...\n")

        # Move to next batch
        file_index = batch_end

    parallel_time = time.time() - parallel_start

    print(f"\n✅ ALL BATCHES COMPLETE:")
    print(f"   Files processed: {processed_files}")
    print(f"   Files skipped: {skipped_files}")
    print(f"   Total batches: {batch_number}")
    print(f"   Total measurements pushed: {total_pushed_measurements:,}")
    print(f"   Parallel time: {parallel_time:.2f}s")

    total_time = time.time() - total_start

    print(f"\n📈 SUMMARY:")
    print("=" * 70)
    print(f"Total files: {len(stdf_files)}")
    print(f"Processed: {processed_files}")
    print(f"Skipped: {skipped_files}")
    print(f"Total measurements pushed: {total_pushed_measurements:,}")
    print(f"Total time: {total_time:.2f}s")
    if total_pushed_measurements > 0:
        print(f"Overall throughput: {total_pushed_measurements / total_time:,.0f} measurements/second")
    print(f"Platform: {platform.system()} ({platform.machine()})")

    return 0


if __name__ == "__main__":
    sys.exit(main())
