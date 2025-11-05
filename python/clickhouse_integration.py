"""
ClickHouse utility functions for STDF data processing
Optimized for high-throughput data ingestion with thread-safe connection pooling
"""

from clickhouse_driver import Client
import threading
from concurrent.futures import ThreadPoolExecutor
import time
from datetime import datetime
import sys
import os

# Import the connection pool
from clickhouse_pool import ClickHouseConnectionPool, ConnectionManager


def optimize_clickhouse_connection(host='localhost', port=9000, database='default', user='default', password=''):
    """
    Create an optimized ClickHouse client connection with enhanced settings for STDF data processing

    Parameters:
    - host: ClickHouse server hostname
    - port: ClickHouse server port (default is 9000)
    - database: Database name
    - user: Username for authentication
    - password: Password for authentication

    Returns:
    - client: Configured ClickHouse client
    """
    try:
        # Configure ClickHouse client with performance-optimized settings
        client = Client(
            host=host,
            port=port,
            database=database,
            user=user,
            password=password,
            settings={
                # Insert optimization settings
                'max_insert_block_size': 1000000,        # Larger block size for better insert performance
                'min_insert_block_size_rows': 100000,    # Increased from 10000 for better batching
                'min_insert_block_size_bytes': 52428800, # 50MB (increased from 10MB)
                
                # Parallelism settings
                'max_threads': 32,                       # Doubled thread count for better parallelism
                'max_insert_threads': 32,                # Doubled insert threads
                
                # Network settings
                'receive_timeout': 600,                  # Doubled timeout (10 min) for large operations
                'send_timeout': 600,                     # Doubled timeout for large data sending
                'max_execution_time': 600,               # Doubled execution timeout
                'socket_timeout': 600,                   # Socket timeout
                
                # Memory settings
                'max_memory_usage': 20000000000,         # 20GB memory limit (doubled)
                'max_bytes_before_external_sort': 10000000000,  # 10GB before using external sort
                
                # Performance settings
                'max_bytes_in_join': 10000000000,        # 10GB for join operations
                'join_algorithm': 'hash',                # Use hash join algorithm
                'max_read_buffer_size': 10485760,        # 10MB read buffer
                'optimize_skip_unused_shards': 1,        # Skip unused shards
                'optimize_read_in_order': 1,             # Read in order when possible
                'enable_optimize_predicate_expression': 1, # Optimize predicates
            }
        )
        
        # Verify connection
        result = client.execute("SELECT 1")
        if result and result[0][0] == 1:
            print(f"Connected to ClickHouse server at {host}:{port}, database: {database}")
            return client
        else:
            raise ConnectionError("Connection test failed")
            
    except Exception as e:
        print(f"Error connecting to ClickHouse: {e}")
        raise


def setup_clickhouse_schema(client):
    """
    Set up the ClickHouse schema for STDF data with Solution 5 enhancements
    
    Parameters:
    - client: ClickHouse client
    """
    try:
        # Create device mapping table
        client.execute("""
            CREATE TABLE IF NOT EXISTS device_mapping (
                wld_id UInt32,
                wld_device_dmc String
            ) ENGINE = MergeTree()
            ORDER BY (wld_id)
        """)
        
        # Create parameter info table
        client.execute("""
            CREATE TABLE IF NOT EXISTS parameter_info (
                wtp_id UInt32,
                wtp_param_name String
            ) ENGINE = MergeTree()
            ORDER BY (wtp_id)
        """)
        
        # Create measurements table with ClickHouse-specific optimizations (LEGACY - keep for backward compatibility)
        client.execute("""
            CREATE TABLE IF NOT EXISTS measurements (
                wld_id UInt32,
                wtp_id UInt32,
                wp_pos_x Int32,
                wp_pos_y Int32,
                wptm_value Float64,
                wptm_created_date DateTime,
                test_flag UInt8,
                segment UInt8,
                file_hash String  -- Added for file-level deduplication
            ) ENGINE = MergeTree()
            PARTITION BY toYYYYMM(wptm_created_date)
            ORDER BY (wld_id, wtp_id, wp_pos_x, wp_pos_y, test_flag, segment)
        """)
        
        # Create the reference table for device info
        client.execute("""
            CREATE TABLE IF NOT EXISTS device_info (
                wld_id UInt32,
                wld_device_dmc String,
                wld_phoenix_id String,
                wld_latest String,
                wld_bin_code String,
                wld_bin_desc String,
                wfi_facility String,
                wfi_operation String,
                wl_lot_name String,
                wmp_prog_name String,
                wmp_prog_version String,
                wfi_equipment String,
                sft_name String,
                sft_group String,
                wld_created_date DateTime
            ) ENGINE = MergeTree()
            ORDER BY (wld_id)
        """)

        print("ClickHouse schema setup completed")
        
    except Exception as e:
        print(f"Error setting up ClickHouse schema: {e}")
        raise


def _create_setup_connection_pool(host, port, database, user, password):
    """Create connection pool for setup operations."""
    setup_settings = {
        'max_threads': 8,
        'max_memory_usage': 10000000000,
        'max_execution_time': 600,
        'receive_timeout': 600,
        'send_timeout': 600
    }
    
    return ClickHouseConnectionPool(
        host=host,
        port=port,
        database=database,
        user=user,
        password=password,
        max_connections=4,
        settings=setup_settings
    )


def _setup_schema_and_optimize(client, extractor):
    """Setup schema and optimize tables."""
    setup_clickhouse_schema(client)
    device_ids = {d['WLD_ID'] for d in extractor.data_store['measurements']}
    optimize_table_for_batch_loading(client, list(device_ids))


def _push_device_mappings(client, extractor, batch_size):
    """Push device mappings to ClickHouse."""
    device_start = time.time()
    print("Pushing device mappings...")
    
    device_data = [
        {'wld_id': device_id, 'wld_device_dmc': device_dmc}
        for device_dmc, device_id in extractor.device_id_map.items()
    ]
    
    for i in range(0, len(device_data), batch_size):
        batch = device_data[i:i + batch_size]
        if batch:
            client.execute(
                "INSERT INTO device_mapping (wld_id, wld_device_dmc) VALUES",
                batch
            )
    
    print(f"Pushed {len(extractor.device_id_map)} device mappings in {time.time() - device_start:.2f} seconds")


def _collect_device_info_map(extractor):
    """Collect device info from measurements."""
    device_info_map = {}
    for m in extractor.data_store['measurements']:
        wld_id = m['WLD_ID']
        if wld_id not in device_info_map:
            device_info_map[wld_id] = {
                'wld_id': wld_id,
                'wld_device_dmc': m.get('WLD_DEVICE_DMC', ''),
                'wld_phoenix_id': m.get('WLD_PHOENIX_ID', ''),
                'wld_latest': m.get('WLD_LATEST', ''),
                'wld_bin_code': m.get('WLD_BIN_CODE', ''),
                'wld_bin_desc': m.get('WLD_BIN_DESC', ''),
                'wfi_facility': m.get('WFI_FACILITY', ''),
                'wfi_operation': m.get('WFI_OPERATION', ''),
                'wl_lot_name': m.get('WL_LOT_NAME', ''),
                'wmp_prog_name': m.get('WMP_PROG_NAME', ''),
                'wmp_prog_version': m.get('WMP_PROG_VERSION', ''),
                'wfi_equipment': m.get('WFI_EQUIPMENT', ''),
                'sft_name': m.get('SFT_NAME', ''),
                'sft_group': m.get('SFT_GROUP', ''),
                'wld_created_date': m.get('WLD_CREATED_DATE', datetime.now())
            }
    return device_info_map


def _push_device_info(client, device_info_map, batch_size):
    """Push device info to ClickHouse."""
    device_info_start = time.time()
    device_info_data = list(device_info_map.values())
    print(f"Pushing {len(device_info_data)} device info records...")
    
    for i in range(0, len(device_info_data), batch_size):
        batch = device_info_data[i:i + batch_size]
        if batch:
            try:
                client.execute(
                    """INSERT INTO device_info (
                        wld_id, wld_device_dmc, wld_phoenix_id, wld_latest, 
                        wld_bin_code, wld_bin_desc, wfi_facility, wfi_operation, 
                        wl_lot_name, wmp_prog_name, wmp_prog_version, wfi_equipment, 
                        sft_name, sft_group, wld_created_date
                    ) VALUES""",
                    batch
                )
            except Exception as e:
                print(f"Warning: Error inserting device info batch: {e}")
    
    print(f"Device info processing completed in {time.time() - device_info_start:.2f} seconds")


def _push_parameter_info(client, extractor, batch_size):
    """Push parameter info to ClickHouse."""
    param_start = time.time()
    print("Pushing parameter info...")
    
    param_data = [
        {'wtp_id': param_id, 'wtp_param_name': param_name}
        for param_name, param_id in extractor.param_id_map.items()
    ]
    
    for i in range(0, len(param_data), batch_size):
        batch = param_data[i:i + batch_size]
        if batch:
            client.execute(
                "INSERT INTO parameter_info (wtp_id, wtp_param_name) VALUES",
                batch
            )
    
    print(f"Pushed {len(extractor.param_id_map)} parameter info records in {time.time() - param_start:.2f} seconds")


def push_to_clickhouse(extractor, host='localhost', port=9000, database='default', 
                      user='default', password='', batch_size=100000, 
                      on_measurements_start=None):
    """
    Push STDF data to ClickHouse with optimized performance using connection pooling
    
    Parameters:
    - extractor: StdfDataExtractor instance with processed data
    - host: ClickHouse server hostname
    - port: ClickHouse server port
    - database: Database name
    - user: Username for authentication
    - password: Password for authentication
    - batch_size: Size of batches for inserts
    - on_measurements_start: Callback function when measurements push starts
    """
    start_time = time.time()
    
    try:
        setup_pool = _create_setup_connection_pool(host, port, database, user, password)
        
        with ConnectionManager(setup_pool) as client:
            _setup_schema_and_optimize(client, extractor)
            _push_device_mappings(client, extractor, batch_size)
            
            print("Collecting device info data...")
            device_info_map = _collect_device_info_map(extractor)
            _push_device_info(client, device_info_map, batch_size)
            _push_parameter_info(client, extractor, batch_size)
        
        setup_pool.close_all()
        
        if on_measurements_start:
            on_measurements_start()
        
        connection_params = {
            'host': host, 'port': port, 'database': database,
            'user': user, 'password': password
        }

        push_measurements_clickhouse(connection_params, extractor.data_store['measurements'], batch_size)

        print(f"Total push time: {time.time() - start_time:.2f} seconds")
        
        # Print string mappings summary if available  
        try:
            if hasattr(extractor, 'field_extractor') and hasattr(extractor.field_extractor, 'get_string_mappings'):
                mappings = extractor.field_extractor.get_string_mappings()
                if mappings:
                    print(f"\n📋 String-to-Numeric Mappings Created: {len(mappings)}")
                    # Show first few mappings as examples
                    for i, (key, value) in enumerate(list(mappings.items())[:5]):
                        print(f"  {key} -> {value}")
                    if len(mappings) > 5:
                        print(f"  ... and {len(mappings) - 5} more mappings")
        except Exception:
            pass  # Ignore if mappings not available
        
        return True
        
    except Exception as e:
        print(f"Error pushing data to ClickHouse: {e}")
        import traceback
        traceback.print_exc()
        return False


def _organize_measurements_by_partition(measurements):
    """Organize measurements by WLD_ID for partitioned processing."""
    measurements_by_wld_id = {}
    for m in measurements:
        wld_id = m['WLD_ID']
        if wld_id not in measurements_by_wld_id:
            measurements_by_wld_id[wld_id] = []
        measurements_by_wld_id[wld_id].append(m)
    return measurements_by_wld_id


def _create_connection_pool(connection_params, pool_size):
    """Create optimized ClickHouse connection pool."""
    batch_settings = {
        'max_insert_block_size': 100000,
        'min_insert_block_size_rows': 10000,
        'max_threads': 32,
        'max_insert_threads': 32,
        'receive_timeout': 600,
        'send_timeout': 600,
        'socket_timeout': 600
    }
    
    return ClickHouseConnectionPool(
        host=connection_params.get('host', 'localhost'),
        port=connection_params.get('port', 9000),
        database=connection_params.get('database', 'default'),
        user=connection_params.get('user', 'default'),
        password=connection_params.get('password', ''),
        max_connections=pool_size,
        settings=batch_settings
    )


def _get_duplicate_segment(duplicate_key, duplicate_tracker, duplicate_lock):
    """Thread-safe duplicate segment lookup."""
    with duplicate_lock:
        if duplicate_key in duplicate_tracker:
            segment = duplicate_tracker[duplicate_key] + 1
            duplicate_tracker[duplicate_key] = segment
        else:
            segment = 0
            duplicate_tracker[duplicate_key] = 0
    return segment


def _convert_measurement_to_batch_data(measurement, segment):
    """Convert measurement record to batch data format."""
    return {
        'wld_id': measurement['WLD_ID'],
        'wtp_id': measurement['WTP_ID'],
        'wp_pos_x': int(measurement['WP_POS_X']),
        'wp_pos_y': int(measurement['WP_POS_Y']),
        'wptm_value': float(measurement['WPTM_VALUE']),
        'wptm_created_date': measurement['WPTM_CREATED_DATE'],
        'test_flag': 1 if measurement['TEST_FLAG'] else 0,
        'segment': segment,
        'file_hash': measurement.get('FILE_HASH', '')
    }


def _execute_batch_with_retry(connection_pool, batch_data, max_retries=3):
    """Execute batch insertion with retry logic."""
    retry_count = 0
    while retry_count < max_retries:
        try:
            with ConnectionManager(connection_pool) as client:
                client.execute(
                    "INSERT INTO measurements (wld_id, wtp_id, wp_pos_x, wp_pos_y, wptm_value, wptm_created_date, test_flag, segment, file_hash) VALUES",
                    batch_data
                )
            return True
        except Exception as e:
            retry_count += 1
            if retry_count >= max_retries:
                raise
            print(f"Batch execution failed, retrying ({retry_count}/{max_retries}): {e}")
            time.sleep(1)
    return False


def _update_progress(measurements_pushed, batch_size, total_measurements, progress_lock):
    """Update and log progress with thread safety."""
    with progress_lock:
        new_count = measurements_pushed + batch_size
        if new_count % 30000 == 0 or new_count == total_measurements:
            print(f"Pushed {new_count}/{total_measurements} measurements ({new_count / total_measurements * 100:.2f}%)")
        return new_count


def _process_measurement_batch(measurements, batch_size, duplicate_tracker, duplicate_lock, 
                              connection_pool, progress_lock, total_measurements, measurements_pushed_ref):
    """Process a batch of measurements for a partition."""
    batch_data = []
    
    for m in measurements:
        duplicate_key = (m['WLD_ID'], m['WTP_ID'], str(m['WP_POS_X']), str(m['WP_POS_Y']), m['TEST_FLAG'])
        segment = _get_duplicate_segment(duplicate_key, duplicate_tracker, duplicate_lock)
        batch_record = _convert_measurement_to_batch_data(m, segment)
        batch_data.append(batch_record)
        
        if len(batch_data) >= batch_size:
            _execute_batch_with_retry(connection_pool, batch_data)
            measurements_pushed_ref[0] = _update_progress(measurements_pushed_ref[0], len(batch_data), total_measurements, progress_lock)
            batch_data = []
    
    # Insert any remaining records
    if batch_data:
        _execute_batch_with_retry(connection_pool, batch_data)
        measurements_pushed_ref[0] = _update_progress(measurements_pushed_ref[0], len(batch_data), total_measurements, progress_lock)
    
    return len(measurements)


def _print_performance_summary(measurements_pushed, elapsed_time, batch_size, max_workers, partition_count):
    """Print performance summary statistics."""
    measurements_per_second = measurements_pushed / elapsed_time if elapsed_time > 0 else 0
    print("\n===== PERFORMANCE SUMMARY =====")
    print(f"Total measurements pushed: {measurements_pushed:,}")
    print(f"Total time: {elapsed_time:.2f} seconds")
    print(f"Throughput: {measurements_per_second:.2f} measurements/second")
    print(f"Batch size: {batch_size:,}")
    print(f"Worker threads: {max_workers}")
    print(f"Partitions: {partition_count}")
    print("==============================\n")


def _print_error_summary(error, measurements_pushed, total_measurements, elapsed_time):
    """Print error summary statistics."""
    print("\n===== ERROR SUMMARY =====")
    print(f"Error in push_measurements_clickhouse: {error}")
    print(f"Partial measurements pushed: {measurements_pushed:,} of {total_measurements:,}")
    print(f"Elapsed time before error: {elapsed_time:.2f} seconds")
    print("=======================\n")


def push_measurements_clickhouse(connection_params, measurements, batch_size=100000):
    """
    High-performance measurements pushing function for ClickHouse with thread-safe connection pool
    Optimized with larger batch sizes and more worker threads for maximum throughput
    
    Parameters:
    - connection_params: Dictionary with ClickHouse connection parameters (host, port, database, user, password)
    - measurements: List of measurements to push
    - batch_size: Number of measurements to push in a single batch (increased to 100,000 for better performance)
    """
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Starting push_measurements_clickhouse with {len(measurements)} measurements")
    
    MAX_WORKERS = 32
    total_measurements = len(measurements)
    measurements_pushed_ref = [0]  # Use list for mutable reference
    progress_lock = threading.Lock()
    duplicate_tracker = {}
    duplicate_lock = threading.Lock()
    start_time = time.time()
    
    # Organize measurements by partition
    print("Organizing measurements by partition key...")
    measurements_by_wld_id = _organize_measurements_by_partition(measurements)
    print(f"Organized {total_measurements} measurements across {len(measurements_by_wld_id)} partitions")
    
    # Create connection pool
    pool_size = min(len(measurements_by_wld_id) * 2, MAX_WORKERS)
    connection_pool = _create_connection_pool(connection_params, pool_size)
    print(f"Created optimized connection pool with {pool_size} connections")
    
    def process_partition(wld_id, partition_measurements):
        try:
            print(f"Processing {len(partition_measurements)} measurements for device ID {wld_id}")
            return _process_measurement_batch(
                partition_measurements, batch_size, duplicate_tracker, duplicate_lock,
                connection_pool, progress_lock, total_measurements, measurements_pushed_ref
            )
        except Exception as e:
            print(f"Error processing partition {wld_id}: {e}")
            import traceback
            traceback.print_exc()
            return 0
    
    try:
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = {executor.submit(process_partition, wld_id, partition_measurements): wld_id
                      for wld_id, partition_measurements in measurements_by_wld_id.items()}
            
            completed_partitions = 0
            for future in futures:
                future.result()
                completed_partitions += 1
                print(f"Completed partition {completed_partitions}/{len(measurements_by_wld_id)} ({completed_partitions / len(measurements_by_wld_id) * 100:.2f}%)")
        
        connection_pool.close_all()
        elapsed_time = time.time() - start_time
        _print_performance_summary(measurements_pushed_ref[0], elapsed_time, batch_size, MAX_WORKERS, len(measurements_by_wld_id))
        return measurements_pushed_ref[0]
        
    except Exception as e:
        elapsed_time = time.time() - start_time
        _print_error_summary(e, measurements_pushed_ref[0], total_measurements, elapsed_time)
        import traceback
        traceback.print_exc()
        return measurements_pushed_ref[0]


def optimize_table_for_batch_loading(client, device_ids=None):
    """
    Optimizes ClickHouse tables for batch loading operations
    
    Parameters:
    - client: ClickHouse client
    - device_ids: Optional list of device IDs to pre-allocate partitions for
    """
    try:
        print("Optimizing ClickHouse tables for batch loading...")
        
        # Optimize the measurements table
        client.execute("""
            OPTIMIZE TABLE measurements FINAL
        """)
        
        # Set up system settings for batch loading
        client.execute("SET max_partitions_per_insert_block = 1000")
        client.execute("SET max_insert_threads = 32")
        client.execute("SET max_threads = 32")
        client.execute("SET max_memory_usage = 20000000000")
        
        # If we have device IDs, pre-allocate partitions
        if device_ids and len(device_ids) > 0:
            print(f"Pre-allocating partitions for {len(device_ids)} devices...")
            
            # Create a small dummy batch for each device to pre-allocate partitions
            current_date = datetime.now()
            
            for device_id in device_ids:
                # Insert a dummy row that will be overwritten later
                # This pre-allocates the partition in memory
                client.execute(
                    "INSERT INTO measurements (wld_id, wtp_id, wp_pos_x, wp_pos_y, wptm_value, wptm_created_date, test_flag, segment) VALUES",
                    [{
                        'wld_id': device_id,
                        'wtp_id': 0,
                        'wp_pos_x': 0,
                        'wp_pos_y': 0,
                        'wptm_value': 0.0,
                        'wptm_created_date': current_date,
                        'test_flag': 0,
                        'segment': 0
                    }]
                )
            
            # Delete the dummy rows
            client.execute("OPTIMIZE TABLE measurements FINAL DEDUPLICATE")
            
        print("Table optimization complete")
        return True
        
    except Exception as e:
        print(f"Error optimizing tables: {e}")
        return False
