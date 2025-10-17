#!/usr/bin/env python3
"""
TRUE Parallel STDF Processing with ID Reassignment & device_info
================================================================
Uses ProcessPoolExecutor for REAL parallelism (not limited by GIL)
Maintains globally unique device/parameter IDs via Python-side reassignment

Key Strategy:
1. Load existing device/param mappings from database ONCE (main process)
2. Pass mappings to each worker process
3. Each worker calls C++ process_stdf_with_database_mappings() with:
   - Existing mappings (for consistent IDs within file)
   - Returns NEW mappings found in that file (may have ID conflicts across workers)
4. Main process REASSIGNS globally unique IDs to new mappings
5. Remap measurement IDs to use reassigned IDs
6. Push device_info (from MIR records) then measurements

Benefits:
- TRUE parallel processing (separate processes, no GIL)
- Globally unique IDs (Python reassignment ensures no conflicts)
- Complete device_info support (facility, lot, bin codes, etc.)
- IDs start from 1 (not 0)

Fixed Issues:
- Duplicate IDs from parallel workers (now reassigned)
- IDs starting from 0 (now default=0 → first ID = 1)
- Missing device_info records (now captures all batches)
- Corrupted device_info data (now uses tuples, not dicts)
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


def extract_mir_from_stdf_fast(file_path):
    """
    Extract MIR (Master Information Record) for device_info metadata

    Returns:
        dict with facility, operation, lot_name, equipment, prog_name, prog_version
    """
    try:
        result = stdf_parser_cpp.parse_stdf_file(file_path)
        records = result.get('records', [])

        for record in records:
            if record.get('record_type') == 'MIR':
                fields = record.get('fields', {})
                return {
                    'facility': fields.get('FACIL_ID', ''),
                    'operation': fields.get('OPER_NAM', ''),
                    'lot_name': fields.get('LOT_ID', ''),
                    'equipment': fields.get('NODE_NAM', ''),
                    'prog_name': fields.get('JOB_REV', ''),
                    'prog_version': fields.get('SBLOT_ID', '')
                }

        return {}  # Empty if no MIR found

    except Exception as e:
        print(f"⚠️ MIR extraction error for {os.path.basename(file_path)}: {e}")
        return {}


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

        # Extract MIR info for device_info table
        mir_info = extract_mir_from_stdf_fast(file_path)

        print(f"✅ {os.path.basename(file_path)}: {len(measurements):,} measurements in {elapsed:.2f}s")
        print(f"   📊 New devices: {len(new_device_mappings)}, New params: {len(new_param_mappings)}")

        return {
            'file': file_path,
            'skipped': False,
            'measurements': measurements,
            'new_device_mappings': new_device_mappings,
            'new_param_mappings': new_param_mappings,
            'mir_info': mir_info,        # MIR data for device_info
            'file_hash': file_hash,      # File hash for linking MIR to devices
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


def insert_new_mappings(client, all_new_devices, all_new_params, existing_device_mappings, existing_param_mappings):
    """
    Insert all NEW mappings with globally unique ID reassignment

    CRITICAL: Workers may generate conflicting IDs within a batch.
    We MUST reassign IDs here to ensure global uniqueness.
    """
    # Get existing device/param names from database
    existing_device_dmcs = set(dmc for dmc, _ in existing_device_mappings)
    existing_param_names = set(name for name, _ in existing_param_mappings)

    # Collect only TRULY NEW devices/params (not in database)
    new_device_dmcs = set()
    for device_dmc, _ in all_new_devices:  # Ignore worker IDs
        if device_dmc not in existing_device_dmcs:
            new_device_dmcs.add(device_dmc)

    new_param_names = set()
    for param_name, _ in all_new_params:  # Ignore worker IDs
        if param_name not in existing_param_names:
            new_param_names.add(param_name)

    # Calculate max IDs from existing mappings (FIXED: default=0 instead of -1)
    max_device_id = max([did for _, did in existing_device_mappings], default=0)
    max_param_id = max([pid for _, pid in existing_param_mappings], default=0)

    # REASSIGN globally unique IDs (sorted for determinism)
    unique_devices = {}
    for device_dmc in sorted(new_device_dmcs):
        max_device_id += 1  # Now starts from 1 (not 0)
        unique_devices[device_dmc] = max_device_id

    unique_params = {}
    for param_name in sorted(new_param_names):
        max_param_id += 1  # Now starts from 1 (not 0)
        unique_params[param_name] = max_param_id

    # Insert devices with reassigned IDs
    if unique_devices:
        device_data = [(device_id, device_dmc) for device_dmc, device_id in unique_devices.items()]
        try:
            client.execute(
                "INSERT INTO device_mapping (wld_id, wld_device_dmc) VALUES",
                device_data
            )
            print(f"✅ Inserted {len(device_data)} new device mappings (IDs {min(d[0] for d in device_data)}-{max(d[0] for d in device_data)})")
        except Exception as e:
            print(f"⚠️ Error inserting devices: {e}")

    # Insert parameters with reassigned IDs
    if unique_params:
        param_data = [(param_id, param_name) for param_name, param_id in unique_params.items()]
        try:
            client.execute(
                "INSERT INTO parameter_info (wtp_id, wtp_param_name) VALUES",
                param_data
            )
            print(f"✅ Inserted {len(param_data)} new parameter mappings (IDs {min(p[0] for p in param_data)}-{max(p[0] for p in param_data)})")
        except Exception as e:
            print(f"⚠️ Error inserting params: {e}")

    return unique_devices, unique_params


def remap_measurement_ids(all_measurements, device_id_map, param_id_map):
    """
    Remap measurement IDs after reassignment

    CRITICAL: Workers generate measurements with their own IDs.
    After ID reassignment, we MUST update measurements to use the new IDs.

    Args:
        all_measurements: List of measurement tuples
        device_id_map: Dict mapping device_dmc -> new_id
        param_id_map: Dict mapping param_name -> new_id

    Returns:
        List of remapped measurement tuples
    """
    remapped = []
    for tuple_data in all_measurements:
        # Unpack 14-field tuple
        (old_wld_id, old_wtp_id, wp_pos_x, wp_pos_y, wptm_value, test_flag, segment, file_hash,
         wld_device_dmc, wtp_param_name, units, test_num, test_flg, extra_fields) = tuple_data

        # Look up NEW IDs (use old ID if not found - means it was already in database)
        new_wld_id = device_id_map.get(wld_device_dmc, old_wld_id)
        new_wtp_id = param_id_map.get(wtp_param_name, old_wtp_id)

        # Create remapped tuple
        remapped.append((
            new_wld_id, new_wtp_id, wp_pos_x, wp_pos_y, wptm_value, test_flag, segment, file_hash,
            wld_device_dmc, wtp_param_name, units, test_num, test_flg, extra_fields
        ))

    return remapped


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


def collect_device_info(all_measurements, mir_info_map):
    """
    Build device_info records from measurements + MIR data

    Args:
        all_measurements: List of measurement tuples
        mir_info_map: Dict mapping file_hash -> MIR info

    Returns:
        dict mapping wld_id -> device_info record
    """
    device_info_map = {}

    for tuple_data in all_measurements:
        # Unpack 14-field tuple
        (wld_id, wtp_id, wp_pos_x, wp_pos_y, wptm_value, test_flag, segment, file_hash,
         wld_device_dmc, wtp_param_name, units, test_num, test_flg, extra_fields) = tuple_data

        # Only create device_info once per wld_id
        if wld_id not in device_info_map:
            mir_info = mir_info_map.get(file_hash, {})

            # Determine bin code/desc from test_flag
            bin_code = '1' if test_flag == 1 else '0'
            bin_desc = 'PASS' if test_flag == 1 else 'FAIL'

            device_info_map[wld_id] = {
                'wld_id': wld_id,
                'wld_device_dmc': wld_device_dmc,
                'wld_phoenix_id': '',
                'wld_latest': 'Y',
                'wld_bin_code': bin_code,
                'wld_bin_desc': bin_desc,
                'wfi_facility': mir_info.get('facility', ''),
                'wfi_operation': mir_info.get('operation', ''),
                'wl_lot_name': mir_info.get('lot_name', ''),
                'wmp_prog_name': mir_info.get('prog_name', ''),
                'wmp_prog_version': mir_info.get('prog_version', ''),
                'wfi_equipment': mir_info.get('equipment', ''),
                'sft_name': 'STDF_CPP',
                'sft_group': 'STDF_CPP',
                'wld_created_date': datetime.now()
            }

    return device_info_map


def push_device_info(client, device_info_map, batch_size=10000):
    """
    Push device_info records to ClickHouse

    Args:
        client: ClickHouse client
        device_info_map: Dict mapping wld_id -> device_info record
        batch_size: Number of records per batch (for very large datasets)
    """
    if not device_info_map:
        return

    print(f"🔧 Pushing {len(device_info_map)} device_info records...")
    start_time = time.time()

    # Convert dicts to tuples in correct column order
    device_info_tuples = []
    for device_record in device_info_map.values():
        device_info_tuples.append((
            device_record['wld_id'],
            device_record['wld_device_dmc'],
            device_record['wld_phoenix_id'],
            device_record['wld_latest'],
            device_record['wld_bin_code'],
            device_record['wld_bin_desc'],
            device_record['wfi_facility'],
            device_record['wfi_operation'],
            device_record['wl_lot_name'],
            device_record['wmp_prog_name'],
            device_record['wmp_prog_version'],
            device_record['wfi_equipment'],
            device_record['sft_name'],
            device_record['sft_group'],
            device_record['wld_created_date']
        ))

    # Push in batches (usually just one batch)
    for i in range(0, len(device_info_tuples), batch_size):
        batch = device_info_tuples[i:i + batch_size]
        if batch:
            client.execute(
                """INSERT INTO device_info (
                    wld_id, wld_device_dmc, wld_phoenix_id, wld_latest,
                    wld_bin_code, wld_bin_desc, wfi_facility, wfi_operation,
                    wl_lot_name, wmp_prog_name, wmp_prog_version, wfi_equipment,
                    sft_name, sft_group, wld_created_date
                ) VALUES""",
                batch
            )

    elapsed = time.time() - start_time
    print(f"✅ device_info push complete: {len(device_info_map)} records in {elapsed:.2f}s")


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
    mir_info_map = {}  # Map file_hash -> MIR info (for device_info)
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

                    # Collect MIR info for device_info
                    if 'mir_info' in result and 'file_hash' in result:
                        mir_info_map[result['file_hash']] = result['mir_info']

                    processed_files += 1

                except Exception as e:
                    print(f"❌ Worker error for {os.path.basename(file_path)}: {e}")

        # Batch complete - now push to ClickHouse BEFORE processing next batch
        if all_measurements or all_new_devices or all_new_params:
            batch_number += 1
            print(f"\n📦 BATCH {batch_number} COMPLETE: Processed {len(current_batch_files)} files")
            print(f"🔒 WAITING: Pushing {len(all_measurements):,} measurements to ClickHouse...")

            # Insert new mappings with ID reassignment
            reassigned_devices = {}
            reassigned_params = {}
            if args.push_clickhouse and client and (all_new_devices or all_new_params):
                # Reassign IDs and insert to database
                reassigned_devices, reassigned_params = insert_new_mappings(
                    client,
                    all_new_devices,
                    all_new_params,
                    device_mappings,  # Existing mappings for reference
                    param_mappings
                )

                # Extend existing mappings with REASSIGNED IDs
                for device_dmc, device_id in reassigned_devices.items():
                    device_mappings.append((device_dmc, device_id))

                for param_name, param_id in reassigned_params.items():
                    param_mappings.append((param_name, param_id))

                print(f"✅ Extended mappings: +{len(reassigned_devices)} devices, +{len(reassigned_params)} params")
                print(f"📊 Total mappings now: {len(device_mappings)} devices, {len(param_mappings)} params")

                all_new_devices = []
                all_new_params = []

            # Push device_info and measurements batch
            if args.push_clickhouse and client and all_measurements:
                # CRITICAL: Remap measurement IDs if we reassigned any
                if reassigned_devices or reassigned_params:
                    print(f"🔄 Remapping measurement IDs...")
                    all_measurements = remap_measurement_ids(all_measurements, reassigned_devices, reassigned_params)

                # 1. Push device_info FIRST (before measurements)
                device_info_map = collect_device_info(all_measurements, mir_info_map)
                push_device_info(client, device_info_map)

                # 2. Then push measurements
                mega_push_measurements(client, all_measurements)
                total_pushed_measurements += len(all_measurements)

                # 3. Clear batch (now safe after pushing)
                all_measurements = []
                mir_info_map = {}  # Clear MIR info for next batch

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