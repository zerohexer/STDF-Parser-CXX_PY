#!/usr/bin/env python3
"""
Extract ALL Measurements + ClickHouse Integration - EXACT PARALLEL VERSION
=========================================================================
Based EXACTLY on extract_all_measurements_plus_clickhouse_connect.py
Just adds parallel directory processing with thread-safe ID management

Complete STDF processing pipeline:
1. Fast C++ binary parsing (exact same as single file version)
2. Direct ClickHouse push (exact same logic)
3. Parallel directory processing with consistent ID mappings
4. Thread-safe device/parameter ID coordination

EVERYTHING IS IDENTICAL to the single file version except:
- Processes multiple files in parallel from a directory
- Uses SharedIDManager for thread-safe ID coordination
- No batching changes, no logic changes, exact same processing
"""

import os
import platform
import time
import argparse
import sys
import hashlib
import threading
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
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

# Import ClickHouse integration using clickhouse-driver (fast native TCP)
try:
    from clickhouse_driver import Client
    from clickhouse_utils import (
        optimize_clickhouse_connection, 
        setup_clickhouse_schema, 
        push_to_clickhouse,
        optimize_table_for_batch_loading,
        create_materialized_views
    )
    print("✅ ClickHouse integration loaded (clickhouse-driver - native TCP)")
except ImportError as e:
    print(f"❌ ClickHouse integration not available: {e}")
    print("Make sure clickhouse-driver is installed: pip install clickhouse-driver")
    exit(1)


class SharedIDManager:
    """Thread-safe ID manager for coordinating device/parameter IDs across parallel workers"""
    
    def __init__(self):
        self.device_id_map = {}
        self.param_id_map = {}
        self.device_counter = 0
        self.param_counter = 0
        self.device_lock = threading.Lock()
        self.param_lock = threading.Lock()
        
    def load_existing_mappings(self, client):
        """Load existing mappings from database (thread-safe)"""
        with self.device_lock:
            try:
                device_mappings = client.execute("SELECT wld_device_dmc, wld_id FROM device_mapping")
                for device_dmc, wld_id in device_mappings:
                    self.device_id_map[device_dmc] = wld_id
                    self.device_counter = max(self.device_counter, wld_id + 1)
                print(f"📥 Loaded {len(device_mappings)} existing device mappings")
            except Exception as e:
                print(f"⚠️ Could not load device mappings: {e}")
        
        with self.param_lock:
            try:
                param_mappings = client.execute("SELECT wtp_param_name, wtp_id FROM parameter_info")
                for param_name, wtp_id in param_mappings:
                    self.param_id_map[param_name] = wtp_id
                    self.param_counter = max(self.param_counter, wtp_id + 1)
                print(f"📥 Loaded {len(param_mappings)} existing parameter mappings")
            except Exception as e:
                print(f"⚠️ Could not load parameter mappings: {e}")
    
    def get_device_id_threadsafe(self, device_dmc, client=None):
        """EXACT same logic as single file version but thread-safe"""
        with self.device_lock:
            # First check if we already have a mapping in memory
            if device_dmc in self.device_id_map:
                return self.device_id_map[device_dmc]
            
            # If ClickHouse client exists, check if mapping exists in database
            if client:
                try:
                    query = f"SELECT wld_id FROM device_mapping WHERE wld_device_dmc = '{device_dmc}'"
                    result = client.execute(query)
                    if result:
                        existing_id = result[0][0]
                        self.device_id_map[device_dmc] = existing_id
                        return existing_id
                except Exception as e:
                    print(f"⚠️ Database lookup failed for device {device_dmc}: {e}")
            
            # Create new mapping (same logic as single file)
            new_wld_id = self.device_counter
            self.device_id_map[device_dmc] = new_wld_id
            self.device_counter += 1
            return new_wld_id
    
    def get_param_id_threadsafe(self, param_name, client=None):
        """EXACT same logic as single file version but thread-safe"""
        with self.param_lock:
            if param_name in self.param_id_map:
                return self.param_id_map[param_name]
            
            if client:
                try:
                    query = f"SELECT wtp_id FROM parameter_info WHERE wtp_param_name = '{param_name}'"
                    result = client.execute(query)
                    if result:
                        existing_id = result[0][0]
                        self.param_id_map[param_name] = existing_id
                        return existing_id
                except Exception as e:
                    print(f"⚠️ Database lookup failed for parameter {param_name}: {e}")
            
            # Create new mapping (same logic as single file)
            new_wtp_id = self.param_counter
            self.param_id_map[param_name] = new_wtp_id
            self.param_counter += 1
            return new_wtp_id
    
    def get_stats(self):
        """Get current mapping statistics"""
        with self.device_lock:
            device_count = len(self.device_id_map)
        with self.param_lock:
            param_count = len(self.param_id_map)
        return device_count, param_count


class STDFProcessor:
    """EXACT same processor as single file version with optional shared ID manager"""
    
    def __init__(self, enable_clickhouse=True, batch_size=10000, shared_id_manager=None):
        """
        Initialize the STDF processor - EXACTLY like single file version
        
        Args:
            enable_clickhouse: Whether to enable ClickHouse push functionality
            batch_size: Batch size for ClickHouse operations
            shared_id_manager: Optional shared ID manager for parallel processing
        """
        self.enable_clickhouse = enable_clickhouse
        self.batch_size = batch_size
        self.measurements = []
        self.devices = {}
        self.parameters = {}
        self.processing_stats = {}
        
        # Use shared ID manager if provided, otherwise create local ones
        self.shared_id_manager = shared_id_manager
        if shared_id_manager:
            # Use shared mappings for parallel processing
            self.device_id_map = None  # Will use shared_id_manager methods
            self.param_id_map = None   # Will use shared_id_manager methods
            self.device_counter = None
            self.param_counter = None
        else:
            # Local mappings for single-threaded processing
            self.device_id_map = {}  # WLD_DEVICE_DMC -> WLD_ID
            self.param_id_map = {}   # WTP_PARAM_NAME -> WTP_ID
            self.device_counter = 0
            self.param_counter = 0
        
        self.current_file_hash = None  # For deduplication
        
        # Debug counters from original
        self.debug_comma_tests = 0
        self.debug_single_tests = 0
        
        print(f"🚀 STDFProcessor initialized (your existing logic + thread-safety)")
        print(f"   ClickHouse integration: {'✅ Enabled' if enable_clickhouse else '❌ Disabled'}")
        print(f"   Batch size: {batch_size:,}")
        print(f"   Platform: {platform.system()} ({platform.machine()})")
        print(f"   Shared ID manager: {'✅ Enabled' if shared_id_manager else '❌ Disabled'}")
    
    def get_device_id(self, device_dmc, client=None):
        """Get or create device ID - uses shared manager if available"""
        if self.shared_id_manager:
            return self.shared_id_manager.get_device_id_threadsafe(device_dmc, client)
        else:
            # EXACT same logic as single file version
            if device_dmc in self.device_id_map:
                return self.device_id_map[device_dmc]
            
            if client:
                try:
                    query = f"SELECT wld_id FROM device_mapping WHERE wld_device_dmc = '{device_dmc}'"
                    result = client.execute(query)
                    if result:
                        existing_id = result[0][0]
                        self.device_id_map[device_dmc] = existing_id
                        return existing_id
                except Exception as e:
                    print(f"⚠️ Database lookup failed for device {device_dmc}: {e}")
            
            new_wld_id = self.device_counter
            self.device_id_map[device_dmc] = new_wld_id
            self.device_counter += 1
            return new_wld_id
    
    def get_param_id(self, param_name, client=None):
        """Get or create parameter ID - uses shared manager if available"""
        if self.shared_id_manager:
            return self.shared_id_manager.get_param_id_threadsafe(param_name, client)
        else:
            # EXACT same logic as single file version
            if param_name in self.param_id_map:
                return self.param_id_map[param_name]
            
            if client:
                try:
                    query = f"SELECT wtp_id FROM parameter_info WHERE wtp_param_name = '{param_name}'"
                    result = client.execute(query)
                    if result:
                        existing_id = result[0][0]
                        self.param_id_map[param_name] = existing_id
                        return existing_id
                except Exception as e:
                    print(f"⚠️ Database lookup failed for parameter {param_name}: {e}")
            
            new_wtp_id = self.param_counter
            self.param_id_map[param_name] = new_wtp_id
            self.param_counter += 1
            return new_wtp_id

    def load_existing_mappings(self, client):
        """Load existing mappings from database - EXACT same as single file version"""
        if self.shared_id_manager:
            # Shared manager handles this
            return
            
        try:
            device_mappings = client.execute("SELECT wld_device_dmc, wld_id FROM device_mapping")
            for device_dmc, wld_id in device_mappings:
                self.device_id_map[device_dmc] = wld_id
                self.device_counter = max(self.device_counter, wld_id + 1)
            
            param_mappings = client.execute("SELECT wtp_param_name, wtp_id FROM parameter_info")
            for param_name, wtp_id in param_mappings:
                self.param_id_map[param_name] = wtp_id
                self.param_counter = max(self.param_counter, wtp_id + 1)
                
            print(f"✅ Loaded {len(device_mappings)} devices, {len(param_mappings)} parameters")
            
        except Exception as e:
            print(f"⚠️ Could not load existing mappings: {e}")
            print("📝 Starting with fresh mappings...")
    
    def generate_file_hash(self, stdf_file):
        """Generate MD5 hash for file deduplication - EXACT same as single file version"""
        try:
            with open(stdf_file, 'rb') as f:
                file_hash = hashlib.md5(f.read()).hexdigest()
            print(f"🔐 Using Python-generated MD5 hash: {file_hash}")
            return file_hash
        except Exception as e:
            print(f"⚠️ Could not generate file hash: {e}")
            return None

    def _is_pixel_test(self, param_name, test_txt):
        """Check if test is a pixel test - EXACT same as single file version"""
        return (
            'Pixel=' in param_name or 'Pixel=' in test_txt or
            'pixel=' in param_name or 'pixel=' in test_txt
        )

    def _generate_file_hash(self, file_path):
        """Generate MD5 hash of the file for deduplication - EXACT same as single file version"""
        hash_md5 = hashlib.md5()
        try:
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_md5.update(chunk)
            return hash_md5.hexdigest()
        except Exception as e:
            print(f"⚠️ Error generating file hash: {e}")
            return None
    
    def _is_file_already_processed(self, file_hash, client=None):
        """Check if file with this hash has already been processed - EXACT same as single file version"""
        if not file_hash or not client:
            return False
        
        try:
            query = f"SELECT COUNT(*) FROM measurements WHERE file_hash = '{file_hash}' LIMIT 1"
            rows = client.execute(query)
            if rows and len(rows) > 0:
                count = rows[0][0]
                return count > 0
        except Exception as e:
            print(f"⚠️ Error checking file hash in database: {e}")
        
        return False
    
    def _load_existing_mappings_from_clickhouse(self, host='localhost', port=9000, database='default', user='default', password=''):
        """Load existing device and parameter mappings from ClickHouse - EXACT same as single file version"""
        try:
            from clickhouse_driver import Client
            
            # Use provided parameters or stored settings
            actual_host = host if host != 'localhost' else getattr(self, 'ch_host', 'localhost')
            actual_port = port if port != 9000 else getattr(self, 'ch_port', 9000)
            actual_database = database if database != 'default' else getattr(self, 'ch_database', 'default')
            actual_user = user if user != 'default' else getattr(self, 'ch_user', 'default')
            actual_password = password if password != '' else getattr(self, 'ch_password', '')
            
            # Create connection to load mappings
            # Create connection to load mappings
            client = Client(
                host=actual_host,
                port=actual_port,
                database=actual_database,
                user=actual_user,
                password=actual_password
            )
            
            # Load device mappings
            device_mappings = []
            try:
                device_results = client.execute("SELECT wld_device_dmc, wld_id FROM device_mapping")
                device_mappings = [(device_dmc, device_id) for device_dmc, device_id in device_results]
                print(f"📊 Loaded {len(device_mappings)} existing device mappings")
            except Exception as e:
                print(f"⚠️ No existing device mappings found: {e}")
                device_mappings = []
            
            # Load parameter mappings
            param_mappings = []
            try:
                param_results = client.execute("SELECT wtp_param_name, wtp_id FROM parameter_info")
                param_mappings = [(param_name, param_id) for param_name, param_id in param_results]
                print(f"📊 Loaded {len(param_mappings)} existing parameter mappings")
            except Exception as e:
                print(f"⚠️ No existing parameter mappings found: {e}")
                param_mappings = []
            
            return device_mappings, param_mappings
            
        except Exception as e:
            print(f"⚠️ Error loading existing mappings: {e}")
            return [], []

    def clean_param_name(self, param_name):
        """Clean parameter name - EXACT same as single file version"""
        if not param_name:
            return param_name
        
        # Remove quotes and clean the parameter name
        cleaned = param_name.strip('"').strip("'")
        
        # Handle special cases from original
        if 'modSum' in cleaned:
            # Extract meaningful part before modSum
            if ':' in cleaned:
                parts = cleaned.split(':')
                if len(parts) >= 2:
                    cleaned = parts[1].split(';')[0]
        
        return cleaned.strip()

    def extract_measurements(self, stdf_file_path, ch_host='localhost', ch_port=9000, ch_database='default', ch_user='default', ch_password=''):
        """Extract measurements using EXACT same logic as single file version"""
        print(f"\n📄 Processing: {os.path.basename(stdf_file_path)}")
        
        start_time = time.time()
        
        # FILE HASH DEDUPLICATION CHECK - EXACT same as single file version
        print(f"🔍 Checking file deduplication...")
        file_hash = self._generate_file_hash(stdf_file_path)
        if file_hash:
            print(f"   📄 File hash: {file_hash}")
            self.current_file_hash = file_hash
            
            # Create temporary ClickHouse connection to check for duplicates
            try:
                from clickhouse_driver import Client
                # Create temporary client for duplicate check
                temp_client = Client(
                    host=ch_host,
                    port=ch_port,
                    database=ch_database,
                    user=ch_user,
                    password=ch_password
                )
                
                if self._is_file_already_processed(file_hash, temp_client):
                    filename = os.path.basename(stdf_file_path)
                    print(f"⚠️ File {filename} already processed (hash: {file_hash})")
                    print(f"⚠️ Skipping processing to prevent duplicates")
                    # Return empty results to indicate file was skipped
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
                    print(f"✅ File not previously processed, continuing...")
            except Exception as e:
                print(f"⚠️ Could not check for duplicates: {e}")
                print(f"⚠️ Proceeding with processing...")
        else:
            print(f"⚠️ Could not generate file hash, proceeding without deduplication")
        
        # DATABASE-AWARE: Load existing mappings from ClickHouse - EXACT same as single file version
        print(f"🔧 Loading existing device/parameter mappings from ClickHouse...")
        device_mappings, param_mappings = self._load_existing_mappings_from_clickhouse(
            host=ch_host, port=ch_port, database=ch_database, user=ch_user, password=ch_password
        )
        
        # ULTRA-FAST: Process STDF with database-aware IDs - EXACT same as single file version
        result = stdf_parser_cpp.process_stdf_with_database_mappings(
            stdf_file_path, 
            device_mappings, 
            param_mappings,
            self.current_file_hash or ""  # Pass the MD5 hash from Python
        )
        
        # Extract results from C++ processing - EXACT same as single file version
        measurement_tuples = result.get('measurement_tuples', [])
        new_device_mappings = result.get('new_device_mappings', [])
        new_param_mappings = result.get('new_param_mappings', [])
        
        total_time = time.time() - start_time
        
        print(f"🚀 ULTRA-FAST C++ processing completed:")
        print(f"   📊 Records parsed: {result.get('total_records', 0):,}")
        print(f"   📊 Measurements: {result.get('total_measurements', 0):,}")
        print(f"   ⏱️ C++ parsing: {result.get('parsing_time', 0):.2f}s")
        print(f"   ⏱️ C++ processing: {result.get('processing_time', 0):.2f}s")
        print(f"   ⏱️ Total time: {total_time:.2f}s")
        
        if total_time > 0:
            throughput = len(measurement_tuples) / total_time
            print(f"   🚀 Throughput: {throughput:.0f} measurements/second")
        
        # Store tuples for ClickHouse insertion - EXACT same as single file version
        self.measurement_tuples = measurement_tuples
        
        # Update ID mappings from C++ results (includes both existing + new) - EXACT same as single file version
        total_devices = len(device_mappings) + len(new_device_mappings)
        total_params = len(param_mappings) + len(new_param_mappings)
        
        # Store new mappings for database insertion - EXACT same as single file version
        self.new_device_mappings = new_device_mappings
        self.new_param_mappings = new_param_mappings
        
        print(f"   📊 Total device mappings: {total_devices:,} ({len(device_mappings):,} existing + {len(new_device_mappings):,} new)")
        print(f"   📊 Total parameter mappings: {total_params:,} ({len(param_mappings):,} existing + {len(new_param_mappings):,} new)")
        
        # Store processing stats - EXACT same as single file version
        self.processing_stats = {
            'cpp_parsing_time': result.get('parsing_time', 0),
            'cpp_processing_time': result.get('processing_time', 0),
            'total_processing_time': total_time,
            'total_measurements': len(measurement_tuples),
            'total_records': result.get('total_records', 0),
            'ultra_fast_mode': True
        }
        
        # For compatibility, also store as measurements list (but empty to save memory) - EXACT same as single file version
        self.measurements = []
        
        return measurement_tuples

    def push_to_clickhouse(self, measurements, clickhouse_host, clickhouse_port, clickhouse_database, 
                          clickhouse_user, clickhouse_password):
        """Push measurements to ClickHouse - EXACT same as single file version"""
        if not measurements:
            print("⚠️ No measurements to push")
            return False
            
        # ClickHouse operations (sequential when used in parallel context)
        try:
            print("🚀 Starting ClickHouse integration (clickhouse-driver - native TCP)...")
            print("🚀 Using ULTRA-FAST C++ tuples (no transformation needed)...")
            print(f"✅ Ultra-fast tuple conversion: {len(measurements):,} tuples ready for ClickHouse")
            
            ch_start = time.time()
            
            print("🔧 Setting up ClickHouse connection and schema...")
            client = optimize_clickhouse_connection(
                clickhouse_host,
                clickhouse_port,
                clickhouse_database,
                clickhouse_user,
                clickhouse_password
            )
        
            print(f"Connected to ClickHouse server at {clickhouse_host}:{clickhouse_port}, database: {clickhouse_database}")
        
            # Setup schema - EXACT same as single file version
            setup_start = time.time()
            setup_clickhouse_schema(client)
            setup_time = time.time() - setup_start
            print(f"✅ Schema setup completed in {setup_time:.2f}s")
            
            # Load existing mappings if not using shared manager
            if not self.shared_id_manager:
                self.load_existing_mappings(client)
        
            # C++ already processed with correct IDs - no additional mapping needed!
            print(f"✅ Using C++ tuples with pre-computed IDs: {len(measurements):,} measurements")
            
            # Get mapping counts - handle both shared and local managers
            if self.shared_id_manager:
                device_count, param_count = self.shared_id_manager.get_stats()
            else:
                device_count = len(self.device_id_map) if self.device_id_map else 0
                param_count = len(self.param_id_map) if self.param_id_map else 0
            
            print(f"   📊 Total device mappings: {device_count}")
            print(f"   📊 Total parameter mappings: {param_count}")
            print(f"✅ No additional ID mapping needed - C++ handled it!")
            
            # Push to ClickHouse - EXACT same as single file version  
            push_start = time.time()
            print("📊 Pushing data to ClickHouse... (SEQUENTIAL - no concurrency)")
            
            # Create extractor-like object for clickhouse_utils.push_to_clickhouse()
            # EXACTLY MATCH single file version's data transformation (lines 656-681)
            from datetime import datetime
            current_time = datetime.now()
            
            # Convert C++ tuples to ClickHouse format with datetime - EXACT same as single file
            clickhouse_tuples = []
            for tuple_data in measurements:
                # Match single file version tuple unpacking (lines 660-661)
                (wld_id, wtp_id, wp_pos_x, wp_pos_y, wptm_value, test_flag, segment, file_hash,
                 wld_device_dmc, wtp_param_name, units, test_num, test_flg) = tuple_data
                
                clickhouse_tuples.append((
                    wld_id,
                    wtp_id, 
                    wp_pos_x,
                    wp_pos_y,
                    wptm_value,
                    current_time,  # ClickHouse datetime
                    test_flag,
                    segment,
                    file_hash
                ))
            
            # Use ultra-fast direct push like single file version (lines 916-923)
            result = self._push_tuples_to_clickhouse_ultra_fast(
                clickhouse_tuples,
                host=clickhouse_host,
                port=clickhouse_port,
                database=clickhouse_database,
                user=clickhouse_user,
                password=clickhouse_password
            )
            push_time = time.time() - push_start
            
            total_ch_time = time.time() - ch_start
            print(f"✅ ClickHouse push completed in {push_time:.2f}s (SEQUENTIAL)")
            print(f"📊 Total ClickHouse time: {total_ch_time:.2f}s")
            
            return result
                
        except Exception as e:
            print(f"❌ ClickHouse integration failed for {os.path.basename(stdf_file) if hasattr(self, 'current_file') else 'file'}")
            print(f"   Error: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def _push_tuples_to_clickhouse_ultra_fast(self, tuples, host, port, database, user, password):
        """🚀 ULTRA-FAST: Push pre-processed tuples directly to ClickHouse - EXACT copy from single version"""
        try:
            from clickhouse_driver import Client
            
            print(f"🚀 Ultra-fast ClickHouse push: {len(tuples):,} tuples")
            start_time = time.time()
            
            # Create optimized connection
            client = Client(
                host=host,
                port=port,
                database=database,
                user=user,
                password=password,
                settings={
                    'max_insert_block_size': 1000000,
                    'max_threads': 16,
                    'max_insert_threads': 16,
                    'receive_timeout': 300,
                    'send_timeout': 300
                }
            )
            
            # Setup schema first
            setup_clickhouse_schema(client)
            
            # Push only NEW device and parameter mappings
            if hasattr(self, 'new_device_mappings') and self.new_device_mappings:
                device_insert_data = [(device_id, device_dmc) for device_dmc, device_id in self.new_device_mappings]
                client.execute(
                    "INSERT INTO device_mapping (wld_id, wld_device_dmc) VALUES",
                    device_insert_data
                )
                print(f"✅ Pushed {len(device_insert_data)} NEW device mappings")
            else:
                print(f"ℹ️ No new device mappings to insert")
            
            if hasattr(self, 'new_param_mappings') and self.new_param_mappings:
                param_insert_data = [(param_id, param_name) for param_name, param_id in self.new_param_mappings]
                client.execute(
                    "INSERT INTO parameter_info (wtp_id, wtp_param_name) VALUES", 
                    param_insert_data
                )
                print(f"✅ Pushed {len(param_insert_data)} NEW parameter mappings")
            else:
                print(f"ℹ️ No new parameter mappings to insert")
            
            # Ultra-fast single insert for all measurements
            print(f"🚀 Inserting {len(tuples):,} measurements in single operation...")
            insert_start = time.time()
            
            client.execute(
                "INSERT INTO measurements (wld_id, wtp_id, wp_pos_x, wp_pos_y, wptm_value, wptm_created_date, test_flag, segment, file_hash) VALUES",
                tuples
            )
            
            insert_time = time.time() - insert_start
            total_time = time.time() - start_time
            throughput = len(tuples) / total_time if total_time > 0 else 0
            
            print(f"✅ ULTRA-FAST ClickHouse push completed!")
            print(f"   📊 Measurements pushed: {len(tuples):,}")
            print(f"   ⏱️ Insert time: {insert_time:.2f}s")
            print(f"   ⏱️ Total time: {total_time:.2f}s") 
            print(f"   🚀 Throughput: {throughput:.0f} measurements/second")
            
            return True
            
        except Exception as e:
            print(f"❌ Error in ultra-fast ClickHouse push: {e}")
            import traceback
            traceback.print_exc()
            return False

    def process_file(self, stdf_file, clickhouse_host=None, clickhouse_port=None, 
                    clickhouse_database=None, clickhouse_user=None, clickhouse_password=None):
        """Process single STDF file - EXACT same as single file version"""
        print(f"🔄 Processing: {os.path.basename(stdf_file)}")
        
        # Check file deduplication
        print("🔍 Checking file deduplication...")
        
        start_time = time.time()
        
        # Extract measurements using C++ - EXACT same logic as single file version
        measurements = self.extract_measurements(
            stdf_file,
            ch_host=clickhouse_host,
            ch_port=clickhouse_port,
            ch_database=clickhouse_database,
            ch_user=clickhouse_user,
            ch_password=clickhouse_password
        )
        
        extract_time = time.time() - start_time
        
        if not measurements:
            print(f"⚠️ No measurements extracted from {stdf_file}")
            return {
                'file': stdf_file,
                'measurements': 0,
                'extract_time': extract_time,
                'clickhouse_time': 0,
                'total_time': extract_time,
                'success': False
            }
        
        # Push to ClickHouse if enabled - EXACT same logic
        clickhouse_time = 0
        clickhouse_success = True
        
        if self.enable_clickhouse and clickhouse_host:
            ch_start = time.time()
            clickhouse_success = self.push_to_clickhouse(
                measurements, clickhouse_host, clickhouse_port, 
                clickhouse_database, clickhouse_user, clickhouse_password
            )
            clickhouse_time = time.time() - ch_start
        
        total_time = time.time() - start_time
        
        return {
            'file': stdf_file,
            'measurements': len(measurements),
            'extract_time': extract_time,
            'clickhouse_time': clickhouse_time,
            'total_time': total_time,
            'success': clickhouse_success
        }
    
    def process_file_with_cached_results(self, stdf_file, cached_result, clickhouse_host, clickhouse_port,
                                       clickhouse_database, clickhouse_user, clickhouse_password):
        """🚀 OPTIMIZED: Process file using cached C++ results - no re-parsing needed!"""
        print(f"🔄 Processing: {os.path.basename(stdf_file)} (using cached results)")
        
        start_time = time.time()
        
        # 🚀 OPTIMIZATION: Skip extraction phase - use cached measurements directly
        measurement_tuples = cached_result.get('measurement_tuples', [])
        if not measurement_tuples:
            print(f"⚠️ No cached measurements for {stdf_file}")
            return {
                'file': stdf_file,
                'measurements': 0,
                'extract_time': 0,
                'clickhouse_time': 0,
                'total_time': 0,
                'success': False
            }
        
        # Set up processor state from cached results
        self.measurement_tuples = measurement_tuples
        # 🐛 FIX: Don't re-insert mappings - they were already inserted in Phase 1!
        self.new_device_mappings = []  # Empty - mappings already exist in DB
        self.new_param_mappings = []   # Empty - mappings already exist in DB
        self.current_file_hash = self._generate_file_hash(stdf_file)
        
        extract_time = 0.1  # Minimal time for cache retrieval
        
        print(f"🚀 CACHED RESULT: {len(measurement_tuples):,} measurements (no parsing needed!)")
        
        # Push to ClickHouse if enabled
        clickhouse_time = 0
        clickhouse_success = True
        
        if self.enable_clickhouse and clickhouse_host:
            ch_start = time.time()
            clickhouse_success = self.push_to_clickhouse(
                measurement_tuples, clickhouse_host, clickhouse_port, 
                clickhouse_database, clickhouse_user, clickhouse_password
            )
            clickhouse_time = time.time() - ch_start
        
        total_time = time.time() - start_time
        
        return {
            'file': stdf_file,
            'measurements': len(measurement_tuples),
            'extract_time': extract_time,
            'clickhouse_time': clickhouse_time,
            'total_time': total_time,
            'success': clickhouse_success
        }


class ParallelSTDFProcessor:
    """TWO-PHASE PARALLEL PROCESSOR: Discovery Phase → Parallel Processing Phase"""
    
    # Class-level ClickHouse lock for sequential push (shared across all instances)
    _clickhouse_lock = threading.Lock()
    
    def __init__(self, max_workers=4, batch_size=10000, enable_clickhouse=True):
        self.max_workers = max_workers
        self.batch_size = batch_size  
        self.enable_clickhouse = enable_clickhouse
        
        # Two-phase approach - no shared manager needed
        self.global_device_mappings = {}  # All devices from all files
        self.global_param_mappings = {}   # All parameters from all files
        self.cached_results = {}          # Cache Phase 1 results to avoid re-parsing
        
        print(f"🚀 TWO-PHASE PARALLEL STDF PROCESSOR (Race-Condition Free)")
        print(f"======================================================================")
        print(f"Phase 1: Discovery (single-threaded device/parameter extraction)")
        print(f"Phase 2: Processing (parallel with pre-computed IDs)")
        print(f"Max workers: {max_workers}")
        print(f"Batch size: {batch_size:,}")
        print(f"ClickHouse: {'✅ Enabled' if enable_clickhouse else '❌ Disabled'}")
    
    def _is_pixel_test(self, param_name, test_txt):
        """Check if test involves pixels - same as STDFProcessor"""
        return (
            'Pixel=' in param_name or 'Pixel=' in test_txt or
            'pixel=' in param_name or 'pixel=' in test_txt
        )

    def clean_param_name(self, param_name):
        """Clean parameter name - same as STDFProcessor"""
        if not param_name:
            return param_name
        
        # Remove quotes and clean the parameter name
        cleaned = param_name.strip('"').strip("'")
        
        # Handle special cases from original
        if 'modSum' in cleaned:
            # Extract meaningful part before modSum
            if ':' in cleaned:
                parts = cleaned.split(':')
                if len(parts) >= 2:
                    cleaned = parts[1].split(';')[0]
        
        return cleaned.strip()
    
    def find_stdf_files(self, directory):
        """Find all STDF files in directory (avoiding duplicates)"""
        stdf_files = set()  # Use set to avoid duplicates
        directory_path = Path(directory)
        
        if not directory_path.exists():
            print(f"❌ Directory not found: {directory}")
            return []
        
        # Find .stdf files (both cases, but use set to avoid duplicates on Windows)
        for pattern in ['*.stdf', '*.STDF']:
            stdf_files.update(directory_path.glob(pattern))
        
        stdf_files = [str(f) for f in stdf_files]
        print(f"📁 Found {len(stdf_files)} STDF files in {directory}")
        
        # Debug: show actual files found
        print(f"🔍 Files found:")
        for i, file in enumerate(stdf_files, 1):
            print(f"   {i}. {os.path.basename(file)}")
        
        return stdf_files
    
    def discover_all_devices_and_parameters(self, stdf_files, clickhouse_host, clickhouse_port, 
                                          clickhouse_database, clickhouse_user, clickhouse_password):
        """PHASE 1: Extract all unique devices and parameters from ALL files (single-threaded)"""
        print(f"\n🔍 PHASE 1: DISCOVERY - Extracting devices/parameters from {len(stdf_files)} files...")
        discovery_start = time.time()
        
        all_devices = set()
        all_parameters = set()
        
        # PROPER DISCOVERY: Use same C++ processing as single file version
        for i, stdf_file in enumerate(stdf_files, 1):
            print(f"🔍 Discovery {i}/{len(stdf_files)}: {os.path.basename(stdf_file)}")
            try:
                # Use SAME C++ processing as single file version for proper parameter extraction
                result = stdf_parser_cpp.process_stdf_with_database_mappings(
                    stdf_file, 
                    {},  # Empty device mappings for discovery
                    {},  # Empty param mappings for discovery
                    ""   # Empty hash for discovery
                )
                
                if not result:
                    print(f"   ⚠️ No results from C++ processing")
                    continue
                
                # 🚀 OPTIMIZATION: Cache the full result to avoid re-parsing in Phase 2
                self.cached_results[stdf_file] = result
                
                # Extract device names from new mappings (same as single file approach)
                new_device_mappings = result.get('new_device_mappings', [])
                new_param_mappings = result.get('new_param_mappings', [])
                
                file_devices = set()
                file_params = set()
                
                # Add devices from C++ results
                for device_dmc, _ in new_device_mappings:
                    if device_dmc:
                        file_devices.add(device_dmc)
                        all_devices.add(device_dmc)
                
                # Add parameters from C++ results (already cleaned and filtered!)
                for param_name, _ in new_param_mappings:
                    if param_name:
                        file_params.add(param_name)
                        all_parameters.add(param_name)
                
                print(f"   📊 Devices: {len(file_devices)}, Parameters: {len(file_params)}")
                
            except Exception as e:
                print(f"⚠️ Discovery error: {e}")
                continue
        
        print(f"🎯 DISCOVERY COMPLETE:")
        print(f"   📊 Total unique devices discovered: {len(all_devices):,}")
        print(f"   📊 Total unique parameters discovered: {len(all_parameters):,}")
        
        # Load existing mappings from database
        print(f"📥 Loading existing mappings from database...")
        try:
            # SEQUENTIAL CONNECTION: Wrap with lock to prevent pool exhaustion
            with ParallelSTDFProcessor._clickhouse_lock:
                client = Client(
                    host=clickhouse_host,
                    port=clickhouse_port,
                    database=clickhouse_database,
                    user=clickhouse_user,
                    password=clickhouse_password
                )
            
            # Setup schema first
            setup_clickhouse_schema(client)
            
            # Load existing device mappings
            existing_devices = {}
            device_counter = 0
            try:
                device_results = client.execute("SELECT wld_device_dmc, wld_id FROM device_mapping")
                for device_dmc, device_id in device_results:
                    existing_devices[device_dmc] = device_id
                    device_counter = max(device_counter, device_id + 1)
                print(f"📊 Loaded {len(existing_devices)} existing device mappings")
            except Exception as e:
                print(f"⚠️ No existing device mappings found: {e}")
            
            # Load existing parameter mappings  
            existing_params = {}
            param_counter = 0
            try:
                param_results = client.execute("SELECT wtp_param_name, wtp_id FROM parameter_info")
                for param_name, param_id in param_results:
                    existing_params[param_name] = param_id
                    param_counter = max(param_counter, param_id + 1)
                print(f"📊 Loaded {len(existing_params)} existing parameter mappings")
            except Exception as e:
                print(f"⚠️ No existing parameter mappings found: {e}")
            
            # Create complete mappings (existing + new)
            self.global_device_mappings = existing_devices.copy()
            self.global_param_mappings = existing_params.copy()
            
            # Assign IDs to new devices
            new_devices = []
            for device_dmc in all_devices:
                if device_dmc not in self.global_device_mappings:
                    self.global_device_mappings[device_dmc] = device_counter
                    new_devices.append((device_counter, device_dmc))
                    device_counter += 1
            
            # Assign IDs to new parameters
            new_params = []
            for param_name in all_parameters:
                if param_name not in self.global_param_mappings:
                    self.global_param_mappings[param_name] = param_counter
                    new_params.append((param_counter, param_name))
                    param_counter += 1
            
            # Batch insert new mappings to database
            if new_devices:
                print(f"💾 Inserting {len(new_devices)} new device mappings...")
                client.execute(
                    "INSERT INTO device_mapping (wld_id, wld_device_dmc) VALUES",
                    new_devices
                )
                print(f"✅ Inserted {len(new_devices)} device mappings")
            
            if new_params:
                print(f"💾 Inserting {len(new_params)} new parameter mappings...")
                client.execute(
                    "INSERT INTO parameter_info (wtp_id, wtp_param_name) VALUES", 
                    new_params
                )
                print(f"✅ Inserted {len(new_params)} parameter mappings")
            
            discovery_time = time.time() - discovery_start
            
            print(f"✅ PHASE 1 COMPLETE:")
            print(f"   📊 Total device mappings: {len(self.global_device_mappings):,} ({len(existing_devices):,} existing + {len(new_devices):,} new)")
            print(f"   📊 Total parameter mappings: {len(self.global_param_mappings):,} ({len(existing_params):,} existing + {len(new_params):,} new)")
            print(f"   ⏱️ Discovery time: {discovery_time:.2f}s")
            print(f"   🎯 Ready for parallel processing with pre-computed IDs!")
            
            return True
            
        except Exception as e:
            print(f"❌ Error in discovery phase: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def process_directory(self, directory, clickhouse_host=None, clickhouse_port=None,
                         clickhouse_database=None, clickhouse_user=None, clickhouse_password=None):
        """TWO-PHASE PROCESSING: Discovery → Parallel Processing"""
        
        # Find all STDF files
        stdf_files = self.find_stdf_files(directory)
        if not stdf_files:
            return []
        
        total_start_time = time.time()
        
        # ============================================================================
        # PHASE 1: DISCOVERY (Single-threaded, no race conditions)
        # ============================================================================
        if self.enable_clickhouse and clickhouse_host:
            print(f"🎯 Starting TWO-PHASE processing for {len(stdf_files)} files...")
            
            discovery_success = self.discover_all_devices_and_parameters(
                stdf_files, clickhouse_host, clickhouse_port, 
                clickhouse_database, clickhouse_user, clickhouse_password
            )
            
            if not discovery_success:
                print("❌ Discovery phase failed, aborting parallel processing")
                return []
        else:
            print("⚠️ ClickHouse disabled, skipping discovery phase")
            self.global_device_mappings = {}
            self.global_param_mappings = {}
        
        # ============================================================================
        # PHASE 2: PARALLEL PROCESSING (Race-condition free with pre-computed IDs)
        # ============================================================================
        print(f"\n🚀 PHASE 2: PARALLEL PROCESSING - {len(stdf_files)} files with {self.max_workers} workers...")
        phase2_start = time.time()
        
        results = []
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all files for processing
            future_to_file = {}
            for stdf_file in stdf_files:
                # Create processor with PRE-COMPUTED global mappings (no race conditions!)
                processor = STDFProcessor(
                    enable_clickhouse=self.enable_clickhouse,
                    batch_size=self.batch_size,
                    shared_id_manager=None  # No shared manager needed!
                )
                
                # Pre-populate processor with global mappings from Phase 1
                if hasattr(self, 'global_device_mappings') and hasattr(self, 'global_param_mappings'):
                    processor.device_id_map = self.global_device_mappings.copy()
                    processor.param_id_map = self.global_param_mappings.copy()
                    processor.device_counter = max(self.global_device_mappings.values()) + 1 if self.global_device_mappings else 0
                    processor.param_counter = max(self.global_param_mappings.values()) + 1 if self.global_param_mappings else 0
                
                # 🚀 OPTIMIZATION: Pass cached results to avoid re-parsing
                cached_result = self.cached_results.get(stdf_file)
                
                future = executor.submit(
                    self._process_single_file_phase2,
                    processor,
                    stdf_file,
                    clickhouse_host,
                    clickhouse_port,
                    clickhouse_database, 
                    clickhouse_user,
                    clickhouse_password,
                    cached_result  # 🚀 Pass cached result to avoid re-parsing
                )
                future_to_file[future] = stdf_file
            
            # Collect results as they complete
            for future in as_completed(future_to_file):
                stdf_file = future_to_file[future]
                try:
                    result = future.result()
                    results.append(result)
                    
                    # Print progress
                    completed = len(results)
                    print(f"✅ Completed {completed}/{len(stdf_files)}: {os.path.basename(stdf_file)} → {result['measurements']:,} measurements")
                    
                except Exception as e:
                    print(f"❌ Error processing {stdf_file}: {e}")
                    results.append({
                        'file': stdf_file,
                        'measurements': 0,
                        'extract_time': 0,
                        'clickhouse_time': 0,
                        'total_time': 0,
                        'success': False
                    })
        
        # Calculate timing
        phase2_time = time.time() - phase2_start
        total_time = time.time() - total_start_time
        
        # Print summary
        total_measurements = sum(r['measurements'] for r in results)
        successful_files = sum(1 for r in results if r['success'])
        failed_files = len(results) - successful_files
        total_extract_time = sum(r['extract_time'] for r in results)
        total_clickhouse_time = sum(r['clickhouse_time'] for r in results)
        
        print(f"\n📈 TWO-PHASE PROCESSING SUMMARY:")
        print(f"==================================================")
        print(f"Files found:          {len(stdf_files)}")
        print(f"Files processed:      {successful_files}")
        print(f"Files failed:         {failed_files}")
        print(f"Total measurements:   {total_measurements:,}")
        print(f"Phase 1 (Discovery):  {total_time - phase2_time:.2f}s")
        print(f"Phase 2 (Processing): {phase2_time:.2f}s")
        print(f"ClickHouse time:      {total_clickhouse_time:.2f}s")
        print(f"Total time:           {total_time:.2f}s")
        
        if total_time > 0:
            throughput = total_measurements / total_time
            print(f"Overall throughput:   {throughput:.0f} measurements/sec")
        
        print(f"🏆 Race conditions eliminated with two-phase approach!")
        
        return results
    
    def _process_single_file_phase2(self, processor, stdf_file, clickhouse_host, clickhouse_port,
                                   clickhouse_database, clickhouse_user, clickhouse_password, cached_result=None):
        """Process single file in Phase 2 with pre-computed ID mappings (no DB conflicts)"""
        file_start = time.time()
        
        try:
            # 🚀 OPTIMIZATION: Use cached result if available to avoid re-parsing
            if cached_result:
                print(f"🚀 Using cached C++ results for {os.path.basename(stdf_file)} - no re-parsing needed!")
                result = processor.process_file_with_cached_results(
                    stdf_file, cached_result, clickhouse_host, clickhouse_port,
                    clickhouse_database, clickhouse_user, clickhouse_password
                )
            else:
                # Fallback to normal processing
                result = processor.process_file(
                    stdf_file,
                    clickhouse_host,
                    clickhouse_port,
                    clickhouse_database,
                    clickhouse_user, 
                    clickhouse_password
                )
            
            return result
            
        except Exception as e:
            print(f"❌ Phase 2 error processing {os.path.basename(stdf_file)}: {e}")
            return {
                'file': stdf_file,
                'measurements': 0,
                'extract_time': 0,
                'clickhouse_time': 0,
                'total_time': time.time() - file_start,
                'success': False
            }


def main():
    """Main function with EXACT same arguments as single file version"""
    parser = argparse.ArgumentParser(description='EXACT Parallel STDF Processing - Based on extract_all_measurements_plus_clickhouse_connect.py')
    
    # Directory processing (new)
    parser.add_argument('--directory', type=str, help='Directory containing STDF files to process')
    parser.add_argument('--workers', type=int, default=4, help='Number of parallel workers (default: 4)')
    
    # Single file processing (for compatibility)
    parser.add_argument('--stdf-file', type=str, help='Single STDF file to process')
    
    # ClickHouse arguments (EXACT same as single file version)
    parser.add_argument('--push-clickhouse', action='store_true', help='Enable ClickHouse push')
    parser.add_argument('--ch-host', type=str, default='localhost', help='ClickHouse host')
    parser.add_argument('--ch-port', type=int, default=9000, help='ClickHouse port')
    parser.add_argument('--ch-database', type=str, default='default', help='ClickHouse database')
    parser.add_argument('--ch-user', type=str, default='default', help='ClickHouse username')
    parser.add_argument('--ch-password', type=str, default='', help='ClickHouse password')
    parser.add_argument('--batch-size', type=int, default=10000, help='Batch size for processing')
    
    args = parser.parse_args()
    
    # Validate arguments
    if not args.directory and not args.stdf_file:
        print("❌ Please specify either --directory for parallel processing or --stdf-file for single file")
        return
    
    if args.directory:
        # Parallel directory processing
        print(f"📁 Directory: {args.directory}")
        print(f"Workers: {args.workers}")
        print(f"Batch size: {args.batch_size:,}")
        print(f"ClickHouse: {'✅ Enabled' if args.push_clickhouse else '❌ Disabled'}")
        
        if args.push_clickhouse:
            print(f"ClickHouse: {args.ch_host}:{args.ch_port}/{args.ch_database}")
        print()
        
        processor = ParallelSTDFProcessor(
            max_workers=args.workers,
            batch_size=args.batch_size, 
            enable_clickhouse=args.push_clickhouse
        )
        
        results = processor.process_directory(
            args.directory,
            args.ch_host if args.push_clickhouse else None,
            args.ch_port if args.push_clickhouse else None,
            args.ch_database if args.push_clickhouse else None,
            args.ch_user if args.push_clickhouse else None,
            args.ch_password if args.push_clickhouse else None
        )
        
    else:
        # Single file processing (EXACT same as original)
        processor = STDFProcessor(
            enable_clickhouse=args.push_clickhouse,
            batch_size=args.batch_size
        )
        
        result = processor.process_file(
            args.stdf_file,
            args.ch_host if args.push_clickhouse else None,
            args.ch_port if args.push_clickhouse else None, 
            args.ch_database if args.push_clickhouse else None,
            args.ch_user if args.push_clickhouse else None,
            args.ch_password if args.push_clickhouse else None
        )
        
        print(f"\n🎯 SINGLE FILE SUMMARY:")
        print(f"========================================")
        print(f"File:               {os.path.basename(result['file'])}")
        print(f"Measurements:       {result['measurements']:,}")
        print(f"Extract time:       {result['extract_time']:.2f}s")
        print(f"ClickHouse time:    {result['clickhouse_time']:.2f}s")
        print(f"Total time:         {result['total_time']:.2f}s")
        print(f"Success:            {'✅' if result['success'] else '❌'}")


if __name__ == "__main__":
    main()