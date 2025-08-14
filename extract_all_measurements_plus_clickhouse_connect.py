#!/usr/bin/env python3
"""
Extract ALL Measurements + ClickHouse Integration - C++ STDF Parser Edition
==========================================================================
Windows/macOS/Linux Compatible Version using clickhouse-connect

Complete STDF processing pipeline:
1. Fast C++ binary parsing (from extract_all_measurements.py)  
2. Direct ClickHouse push (skipping slow transformation)
3. Push to ClickHouse using clickhouse-connect (official driver with C optimizations)

This version works on ALL platforms including Windows!
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

# Import ClickHouse integration using clickhouse-connect
try:
    from clickhouse_utils_connect import (
        optimize_clickhouse_connection, 
        setup_clickhouse_schema, 
        push_to_clickhouse,
        create_materialized_views
    )
    print("✅ ClickHouse integration loaded (clickhouse-connect)")
except ImportError as e:
    print(f"❌ ClickHouse integration not available: {e}")
    print("Make sure clickhouse-connect is installed: pip install clickhouse-connect")
    exit(1)


class STDFProcessor:
    """Main STDF processor with C++ parsing + ClickHouse integration using clickhouse-connect"""
    
    def __init__(self, enable_clickhouse=True, batch_size=10000):
        """
        Initialize the STDF processor
        
        Args:
            enable_clickhouse: Whether to enable ClickHouse push functionality
            batch_size: Batch size for ClickHouse operations
        """
        self.enable_clickhouse = enable_clickhouse
        self.batch_size = batch_size
        self.measurements = []
        self.devices = {}
        self.parameters = {}
        self.processing_stats = {}
        
        # Persistent ID mapping (like original STDF_Parser_CH.py)
        self.device_id_map = {}  # WLD_DEVICE_DMC -> WLD_ID
        self.param_id_map = {}   # WTP_PARAM_NAME -> WTP_ID
        self.device_counter = 0
        self.param_counter = 0
        self.current_file_hash = None  # For deduplication
        
        # Debug counters from original
        self.debug_comma_tests = 0
        self.debug_single_tests = 0
        
        print(f"🚀 STDFProcessor initialized (clickhouse-connect edition)")
        print(f"   ClickHouse integration: {'✅ Enabled' if enable_clickhouse else '❌ Disabled'}")
        print(f"   Batch size: {batch_size:,}")
        print(f"   Platform: {platform.system()} ({platform.machine()})")
    
    def get_device_id(self, device_dmc, client=None):
        """Get or create a consistent WLD_ID for a device DMC with database persistence"""
        # First check if we already have a mapping in memory
        if device_dmc in self.device_id_map:
            return self.device_id_map[device_dmc]
        
        # If ClickHouse client exists, check if mapping exists in database
        if client:
            try:
                # Use format() for clickhouse-connect parameter substitution
                query = f"SELECT wld_id FROM device_mapping WHERE wld_device_dmc = '{device_dmc}'"
                rows = client.execute(query)
                if rows:
                    wld_id = rows[0][0]
                    self.device_id_map[device_dmc] = wld_id
                    # Update counter to avoid ID conflicts
                    if wld_id >= self.device_counter:
                        self.device_counter = wld_id + 1
                    return wld_id
            except Exception as e:
                print(f"⚠️ Error checking for existing device in ClickHouse: {e}")
        
        # If we get here, no mapping exists - create new mapping
        new_wld_id = self.device_counter
        self.device_id_map[device_dmc] = new_wld_id
        self.device_counter += 1
        
        # Insert new mapping to database if client available
        if client:
            try:
                # Use format() for clickhouse-connect parameter substitution
                query = f"INSERT INTO device_mapping (wld_id, wld_device_dmc) VALUES ({new_wld_id}, '{device_dmc}')"
                client.execute(query)
            except Exception as e:
                print(f"⚠️ Error inserting device mapping to ClickHouse: {e}")
        
        return new_wld_id
    
    def get_param_id(self, param_name, client=None):
        """Get or create a consistent WTP_ID for a parameter name with database persistence"""
        # First check if we already have a mapping in memory
        if param_name in self.param_id_map:
            return self.param_id_map[param_name]
        
        # If ClickHouse client exists, check if mapping exists in database
        if client:
            try:
                # Escape single quotes in parameter name for SQL safety
                escaped_param_name = param_name.replace("'", "\\'")
                query = f"SELECT wtp_id FROM parameter_info WHERE wtp_param_name = '{escaped_param_name}'"
                rows = client.execute(query)
                if rows:
                    wtp_id = rows[0][0]
                    self.param_id_map[param_name] = wtp_id
                    # Update counter to avoid ID conflicts
                    if wtp_id >= self.param_counter:
                        self.param_counter = wtp_id + 1
                    return wtp_id
            except Exception as e:
                print(f"⚠️ Error checking for existing parameter in ClickHouse: {e}")
        
        # If we get here, no mapping exists - create new mapping
        new_wtp_id = self.param_counter
        self.param_id_map[param_name] = new_wtp_id
        self.param_counter += 1
        
        # Insert new mapping to database if client available
        if client:
            try:
                # Escape single quotes in parameter name for SQL safety
                escaped_param_name = param_name.replace("'", "\\'")
                query = f"INSERT INTO parameter_info (wtp_id, wtp_param_name) VALUES ({new_wtp_id}, '{escaped_param_name}')"
                client.execute(query)
            except Exception as e:
                print(f"⚠️ Error inserting parameter mapping to ClickHouse: {e}")
        
        return new_wtp_id
    
    def _generate_file_hash(self, file_path):
        """Generate MD5 hash of the file for deduplication (like original STDF_Parser_CH.py)"""
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
        """Check if file with this hash has already been processed"""
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
    
    def extract_measurements(self, stdf_file_path):
        """Extract ALL measurements from STDF file using C++ parser"""
        print(f"\n🔄 Processing: {os.path.basename(stdf_file_path)}")
        
        start_time = time.time()
        
        # Parse with C++ - get ALL records with ALL fields
        result = stdf_parser_cpp.parse_stdf_file(stdf_file_path)
        records = result.get('records', [])
        
        cpp_time = time.time() - start_time
        print(f"⚡ C++ parsed {len(records):,} records in {cpp_time:.2f}s")
        
        # Group records by type
        record_types = {}
        for record in records:
            rtype = record.get('record_type', 'UNKNOWN')
            if rtype not in record_types:
                record_types[rtype] = []
            record_types[rtype].append(record)
        
        print(f"📊 Record types: {list(record_types.keys())}")
        
        # Extract measurements from test records (same logic as original)
        measurement_start = time.time()
        self._extract_from_records(record_types)
        measurement_time = time.time() - measurement_start
        
        total_time = time.time() - start_time
        print(f"🎯 Extracted {len(self.measurements):,} measurements in {measurement_time:.2f}s")
        print(f"⏱️ Total parsing time: {total_time:.2f}s")
        
        # Store processing stats
        self.processing_stats = {
            'cpp_parsing_time': cpp_time,
            'measurement_extraction_time': measurement_time,
            'total_parsing_time': total_time,
            'total_measurements': len(self.measurements),
            'total_records': len(records),
            'record_types': list(record_types.keys())
        }
        
        return self.measurements
    
    def _extract_from_records(self, record_types):
        """Extract measurements from parsed records using CROSS-PRODUCT logic (from original)"""
        
        # Get MIR info for context
        mir_info = self._get_mir_info(record_types.get('MIR', []))
        
        # Extract PRR records (device information) - following original logic
        prr_records = record_types.get('PRR', [])
        if not prr_records:
            print("❌ No PRR records found - cannot create measurements")
            return
        
        print(f"🔧 Found {len(prr_records)} PRR records (devices)")
        
        # Get ALL test records - CRITICAL: Original processes MPR and PTR separately!
        test_records = []
        
        # Original processes these record types
        for record_type in ['MPR', 'PTR']:  # Focus on main test records like original
            if record_type in record_types:
                test_records.extend(record_types[record_type])
                print(f"📊 Found {len(record_types[record_type]):,} {record_type} records")
        
        # Also include other test record types if available
        for record_type in ['FTR', 'SBR', 'HBR']:
            if record_type in record_types:
                test_records.extend(record_types[record_type])
                print(f"📊 Found {len(record_types[record_type]):,} {record_type} records")
        
        print(f"🧪 Total test records to process: {len(test_records):,}")
        print(f"🔄 Cross-product calculation: {len(prr_records)} devices × {len(test_records):,} tests = {len(prr_records) * len(test_records):,} base operations")
        print(f"📈 Each test can create multiple measurements from comma-separated values")
        
        # CROSS-PRODUCT LOGIC: For each device, process ALL test records
        processed_devices = 0
        total_measurements_created = 0
        
        for prr in prr_records:
            prr_fields = prr.get('fields', {})
            
            # Extract device data from PRR (following original logic)
            device_dmc = prr_fields.get('PART_ID', prr_fields.get('PART_TXT', ''))
            bin_code = prr_fields.get('SOFT_BIN', prr_fields.get('HARD_BIN', ''))
            default_x_pos = self._safe_int(prr_fields.get('X_COORD', 0))
            default_y_pos = self._safe_int(prr_fields.get('Y_COORD', 0))
            
            # Get consistent device ID (following original logic)
            device_id = len(self.devices)
            if device_dmc not in self.devices:
                self.devices[device_dmc] = device_id
            else:
                device_id = self.devices[device_dmc]
            
            prr_data = {
                'device_dmc': device_dmc,
                'device_id': device_id,
                'bin_code': bin_code,
                'default_x_pos': default_x_pos,
                'default_y_pos': default_y_pos
            }
            
            device_measurements_before = len(self.measurements)
            
            # Process EVERY test record for THIS device (cross-product logic)
            for test in test_records:
                self._process_single_test(test, prr_data, mir_info)
            
            device_measurements_created = len(self.measurements) - device_measurements_before
            total_measurements_created += device_measurements_created
            processed_devices += 1
            
            if device_measurements_created > 0:
                avg_per_test = device_measurements_created / len(test_records) if test_records else 0
                print(f"  Device {processed_devices}/{len(prr_records)}: {device_dmc} → {device_measurements_created:,} measurements (avg {avg_per_test:.1f} per test)")
        
        print(f"✅ Cross-product processing completed:")
        print(f"   📊 Processed {processed_devices} devices")
        print(f"   📊 Created {total_measurements_created:,} total measurements")
        print(f"   📊 Average {total_measurements_created//processed_devices if processed_devices > 0 else 0:,} measurements per device")
        print(f"   🔍 DEBUG: Tests with commas: {self.debug_comma_tests:,}")
        print(f"   🔍 DEBUG: Tests with single values: {self.debug_single_tests:,}")
        if (self.debug_comma_tests + self.debug_single_tests) > 0:
            print(f"   🔍 DEBUG: Comma ratio: {self.debug_comma_tests/(self.debug_comma_tests+self.debug_single_tests)*100:.1f}% have commas")
    
    def _get_mir_info(self, mir_records):
        """Extract basic info from MIR record (from original)"""
        if not mir_records:
            return {}
        
        mir_fields = mir_records[0].get('fields', {})
        return {
            'facility': mir_fields.get('FACIL_ID', mir_fields.get('FLOOR_ID', '')),
            'lot_name': mir_fields.get('LOT_ID', mir_fields.get('PART_TYP', '')),
            'operation': mir_fields.get('OPER_NAM', mir_fields.get('SPEC_NAM', '')),
            'equipment': mir_fields.get('NODE_NAM', mir_fields.get('JOB_NAM', '')),
            'start_time': mir_fields.get('START_T', ''),
            'prog_name': mir_fields.get('JOB_REV', ''),
            'prog_version': mir_fields.get('SBLOT_ID', '')
        }
    
    def _process_single_test(self, test_record, prr_data, mir_info):
        """Process a single test record (adapted from original extract_all_measurements.py)"""
        test_fields = test_record.get('fields', {})
        
        # Extract test data from C++ extraction
        # Use direct test_txt field as parameter name (since fields ALARM_ID is empty)
        param_name = test_record.get('test_txt', '')  # Direct field has clean parameter names
        test_txt = test_record.get('test_txt', '')    # Same as param_name for this data
        test_num = test_fields.get('TEST_NUM', '')
        test_flg = test_fields.get('TEST_FLG', '')
        result_value = test_fields.get('RESULT', '0')
        units = test_fields.get('UNITS', '')
        head_num = test_fields.get('HEAD_NUM', '')
        site_num = test_fields.get('SITE_NUM', '')
        
        # CRITICAL: Original DOES filter for pixel tests!
        if not self._is_pixel_test(param_name, test_txt):
            return  # Exit early like original
        
        # Extract coordinates
        pixel_x, pixel_y = self._extract_test_coordinates(
            param_name, test_txt, prr_data['default_x_pos'], prr_data['default_y_pos']
        )
        
        # Clean parameter name
        cleaned_param_name = self._clean_param_name(param_name)
        param_id = len(self.parameters)
        if cleaned_param_name not in self.parameters:
            self.parameters[cleaned_param_name] = param_id
        else:
            param_id = self.parameters[cleaned_param_name]
        
        # Handle measurement values (RTN_RSLT arrays, etc.)
        rtn_rslt = test_fields.get('RTN_RSLT', '')
        
        if test_record.get('record_type') == 'MPR' and rtn_rslt and rtn_rslt != '[float_array]':
            if ',' in rtn_rslt:
                rtn_values = self._parse_test_values(rtn_rslt)
                measurement_values = [self._safe_float(val) for val in rtn_values]
            else:
                measurement_values = [self._safe_float(rtn_rslt)]
        else:
            test_values = self._parse_test_values(test_txt)
            measurement_values = [(self._safe_float(value) if value else self._safe_float(result_value)) for value in test_values]
        
        # Update debug counters
        if len(measurement_values) > 1:
            self.debug_comma_tests += 1
        else:
            self.debug_single_tests += 1
        
        # Create measurements using C++ pre-computed fields (fallback to Python)
        precomputed_fields = self._get_precomputed_fields(mir_info, prr_data)
        
        # Create measurements for EACH value/result
        for i, float_value in enumerate(measurement_values):
            measurement = {
                # Fields that change per measurement:
                'WTP_PARAM_NAME': cleaned_param_name,
                'WPTM_VALUE': float_value,
                'WP_POS_X': pixel_x,
                'WP_POS_Y': pixel_y,
                'WTP_ID': param_id,
                'WLD_ID': prr_data['device_id'],
                'TEST_NUM': test_num,
                'TEST_FLG': test_flg,
                'RECORD_TYPE': test_record.get('record_type', 'MPR'),
                'HEAD_NUM': head_num,
                'SITE_NUM': site_num,
                'UNITS': units,
                
                # Pre-computed fields (same for all measurements from this test):
                **precomputed_fields
            }
            
            self.measurements.append(measurement)
    
    def _get_precomputed_fields(self, mir_info, prr_data):
        """Get pre-computed fields (fallback Python implementation)"""
        return {
            'WFI_FACILITY': mir_info.get('facility', ''),
            'WFI_OPERATION': mir_info.get('operation', ''),
            'WL_LOT_NAME': mir_info.get('lot_name', ''),
            'WLD_DEVICE_DMC': prr_data['device_dmc'],
            'WLD_PHOENIX_ID': '',
            'WLD_LATEST': 'Y',
            'WLD_BIN_CODE': prr_data['bin_code'],
            'WLD_BIN_DESC': 'PASS' if prr_data['bin_code'] and prr_data['bin_code'].isdigit() and int(prr_data['bin_code']) == 1 else 'FAIL',
            'WMP_PROG_NAME': mir_info.get('prog_name', ''),
            'WMP_PROG_VERSION': mir_info.get('prog_version', ''),
            'WPTM_CREATED_DATE': mir_info.get('start_time', ''),
            'SFT_NAME': 'STDF_CPP',
            'SFT_GROUP': 'STDF_CPP',
            'WFI_EQUIPMENT': mir_info.get('equipment', ''),
            'TEST_FLAG': prr_data['bin_code'] and prr_data['bin_code'].isdigit() and int(prr_data['bin_code']) == 1,
            'WLD_CREATED_DATE': mir_info.get('start_time', ''),
        }
    
    def _extract_test_coordinates(self, alarm_id, test_txt, default_x, default_y):
        """Extract pixel coordinates (from original)"""
        x_pos, y_pos = self._parse_pixel_coords(alarm_id)
        if x_pos is None and test_txt:
            x_pos, y_pos = self._parse_pixel_coords(test_txt)
        return x_pos if x_pos is not None else default_x, y_pos if y_pos is not None else default_y
    
    def _parse_pixel_coords(self, text):
        """Parse Pixel=R##C## pattern (from original)"""
        if not text or 'Pixel=' not in text:
            return None, None
        
        import re
        match = re.search(r'Pixel=R(\d+)C(\d+)', text)
        if match:
            row = int(match.group(1))  # R = Row = Y
            col = int(match.group(2))  # C = Column = X  
            return col, row  # Return as (X, Y)
        
        return None, None
    
    def _clean_param_name(self, param_name):
        """Clean parameter name (from original)"""
        if not param_name:
            return param_name
        
        import re
        cleaned = re.sub(r';Pixel=R\d+C\d+', '', param_name)
        cleaned = re.sub(r'^Pixel=R\d+C\d+;', '', cleaned)
        return cleaned
    
    def _parse_test_values(self, test_txt):
        """Parse test values (from original)"""
        if not test_txt:
            return ['0.0']
        
        if ',' in test_txt:
            values = [x.strip() for x in test_txt.split(',') if x.strip()]
            return values if values else ['0.0']
        
        return [test_txt]
    
    def _is_pixel_test(self, alarm_id, test_txt):
        """Check if test involves pixels (from original)"""
        if alarm_id and 'Pixel=' in alarm_id:
            return True
        if test_txt and 'Pixel=' in test_txt:
            return True
        return False
    
    def _safe_float(self, value):
        """Safely convert to float (from original)"""
        try:
            return float(value) if value else 0.0
        except (ValueError, TypeError):
            return 0.0
    
    def _safe_int(self, value):
        """Safely convert to int (from original)"""
        try:
            return int(float(value)) if value else 0
        except (ValueError, TypeError):
            return 0
    
    def push_to_clickhouse(self, stdf_file_path, host='localhost', port=8123, database='default', 
                          user='default', password=''):
        """
        Push measurements to ClickHouse using clickhouse-connect (Windows compatible!)
        
        Args:
            stdf_file_path: Path to original STDF file (for hash generation)
            host: ClickHouse server hostname
            port: ClickHouse HTTP port (default 8123 for clickhouse-connect)
            database: Database name
            user: Username for authentication
            password: Password for authentication
        """
        if not self.enable_clickhouse:
            print("⚠️ ClickHouse integration is disabled")
            return False
        
        if not self.measurements:
            print("⚠️ No measurements to push")
            return False
        
        print(f"\n🚀 Starting ClickHouse integration (clickhouse-connect)...")
        clickhouse_start = time.time()
        
        try:
            # Step 1: Use C++ measurements directly (skip slow transformation)
            print(f"🚀 Using C++ measurements directly (skipping transformation)...")
            transform_time = 0.0  # No transformation time since we skip it
            
            # Fix DateTime fields - convert strings to datetime objects
            from datetime import datetime
            current_time = datetime.now()
            
            # Fix measurements with proper DateTime objects and add segment field
            fixed_measurements = []
            duplicate_tracker = {}  # Track duplicates like STDF_Parser_CH.py
            
            for measurement in self.measurements:
                fixed_measurement = measurement.copy()
                
                # Convert string timestamps to datetime objects for ClickHouse
                if 'WPTM_CREATED_DATE' in fixed_measurement:
                    fixed_measurement['WPTM_CREATED_DATE'] = current_time
                if 'WLD_CREATED_DATE' in fixed_measurement:
                    fixed_measurement['WLD_CREATED_DATE'] = current_time
                
                # Add segment field for deduplication (like STDF_Parser_CH.py)
                # Create duplicate key based on device + parameter + coordinates + test_flag (like clickhouse_utils.py line 768)
                duplicate_key = (
                    fixed_measurement.get('WLD_ID', 0),
                    fixed_measurement.get('WTP_ID', 0), 
                    str(fixed_measurement.get('WP_POS_X', 0)),  # Convert to string like original
                    str(fixed_measurement.get('WP_POS_Y', 0)),  # Convert to string like original
                    fixed_measurement.get('TEST_FLG', 0)        # Add TEST_FLG (raw STDF flag) for deduplication
                )
                
                # Get segment number (0 for first occurrence, increment for duplicates)
                if duplicate_key in duplicate_tracker:
                    segment = duplicate_tracker[duplicate_key] + 1
                    duplicate_tracker[duplicate_key] = segment
                else:
                    segment = 0
                    duplicate_tracker[duplicate_key] = 0
                
                fixed_measurement['segment'] = segment
                fixed_measurements.append(fixed_measurement)
            
            # Create a simple data store using fixed C++ measurements
            data_store = {
                'measurements': fixed_measurements,
                'landing_records': []  # Empty for now
            }
            
            # Create a simple extractor-like object that mimics STDF_Parser_CH.py interface
            class SimpleExtractorLike:
                def __init__(self, data_store, measurements, processor_instance):
                    self.data_store = data_store
                    self.processor = processor_instance  # Reference to main processor for persistent ID methods
                    
                    # Use processor's persistent ID mapping (will be updated with database lookup)
                    self.device_id_map = self.processor.device_id_map
                    self.param_id_map = self.processor.param_id_map
                
                def update_measurements_with_persistent_ids(self, client=None):
                    """Update measurements with database-persistent device and parameter IDs"""
                    for measurement in self.data_store['measurements']:
                        # Get persistent device ID (with database lookup)
                        device_name = measurement.get('WLD_DEVICE_DMC', 'unknown')
                        if device_name and device_name != 'unknown':
                            persistent_device_id = self.processor.get_device_id(device_name, client)
                            measurement['WLD_ID'] = persistent_device_id
                        
                        # Get persistent parameter ID (with database lookup)
                        param_name = measurement.get('WTP_PARAM_NAME', 'unknown')
                        if param_name and param_name != 'unknown':
                            persistent_param_id = self.processor.get_param_id(param_name, client)
                            measurement['WTP_ID'] = persistent_param_id
                        
                        # Add file hash for deduplication (like original STDF_Parser_CH.py)
                        if self.processor.current_file_hash:
                            measurement['FILE_HASH'] = self.processor.current_file_hash
                    
                    # Update the mappings in this object
                    self.device_id_map = self.processor.device_id_map
                    self.param_id_map = self.processor.param_id_map
                            
            extractor_like = SimpleExtractorLike(data_store, fixed_measurements, self)
            
            # Step 2: Setup ClickHouse connection and schema
            print(f"🔧 Setting up ClickHouse connection and schema...")
            setup_start = time.time()
            
            client = optimize_clickhouse_connection(host, port, database, user, password)
            setup_clickhouse_schema(client)
            
            # Step 2.1: Check for file deduplication
            print(f"🔍 Checking file deduplication...")
            file_hash = self._generate_file_hash(stdf_file_path)
            if file_hash:
                print(f"   📄 File hash: {file_hash}")
                self.current_file_hash = file_hash
                
                if self._is_file_already_processed(file_hash, client):
                    filename = os.path.basename(stdf_file_path)
                    print(f"⚠️ File {filename} already processed (hash: {file_hash})")
                    print(f"⚠️ Skipping to prevent duplicates")
                    return {
                        'success': False,
                        'message': 'File already processed',
                        'file_hash': file_hash,
                        'duplicate_prevention': True
                    }
                else:
                    print(f"✅ File not previously processed, continuing...")
            else:
                print(f"⚠️ Could not generate file hash, proceeding without deduplication")
            
            # Try to create materialized views
            try:
                create_materialized_views(client)
            except Exception as e:
                print(f"⚠️ Some materialized views may not be supported: {e}")
            
            setup_time = time.time() - setup_start
            print(f"✅ Schema setup completed in {setup_time:.2f}s")
            
            # Step 2.5: Update measurements with database-persistent IDs
            print(f"🔧 Updating measurements with persistent device/parameter IDs...")
            id_start = time.time()
            extractor_like.update_measurements_with_persistent_ids(client)
            id_time = time.time() - id_start
            print(f"✅ ID mapping completed in {id_time:.2f}s")
            print(f"   📊 Device mappings: {len(self.device_id_map):,}")
            print(f"   📊 Parameter mappings: {len(self.param_id_map):,}")
            
            # Step 3: Push data to ClickHouse
            print(f"📊 Pushing data to ClickHouse...")
            push_start = time.time()
            
            success = push_to_clickhouse(
                extractor_like,
                host=host,
                port=port,
                database=database,
                user=user,
                password=password,
                batch_size=self.batch_size
            )
            
            push_time = time.time() - push_start
            total_clickhouse_time = time.time() - clickhouse_start
            
            if success:
                print(f"✅ ClickHouse push completed in {push_time:.2f}s")
                print(f"📊 Total ClickHouse time: {total_clickhouse_time:.2f}s")
                
                # Store ClickHouse stats
                self.processing_stats.update({
                    'clickhouse_transform_time': transform_time,
                    'clickhouse_setup_time': setup_time,
                    'clickhouse_push_time': push_time,
                    'total_clickhouse_time': total_clickhouse_time,
                    'clickhouse_measurements': len(data_store['measurements']),
                    'clickhouse_landing_records': len(data_store['landing_records'])
                })
                
                return True
            else:
                print(f"❌ ClickHouse push failed")
                return False
            
        except Exception as e:
            print(f"❌ Error in ClickHouse integration: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def print_statistics(self):
        """Print comprehensive processing statistics"""
        print(f"\n📈 COMPREHENSIVE PROCESSING STATISTICS:")
        print("=" * 60)
        
        # Parsing stats
        if self.processing_stats:
            print(f"C++ Parsing:")
            print(f"  Records parsed:        {self.processing_stats.get('total_records', 0):,}")
            print(f"  Measurements created:  {self.processing_stats.get('total_measurements', 0):,}")
            print(f"  C++ parsing time:      {self.processing_stats.get('cpp_parsing_time', 0):.2f}s")
            print(f"  Extraction time:       {self.processing_stats.get('measurement_extraction_time', 0):.2f}s")
            print(f"  Total parsing time:    {self.processing_stats.get('total_parsing_time', 0):.2f}s")
            
            # ClickHouse stats
            if 'total_clickhouse_time' in self.processing_stats:
                print(f"\nClickHouse Integration (clickhouse-connect):")
                print(f"  Transform time:        {self.processing_stats.get('clickhouse_transform_time', 0):.2f}s")
                print(f"  Schema setup time:     {self.processing_stats.get('clickhouse_setup_time', 0):.2f}s")
                print(f"  Data push time:        {self.processing_stats.get('clickhouse_push_time', 0):.2f}s")
                print(f"  Total ClickHouse time: {self.processing_stats.get('total_clickhouse_time', 0):.2f}s")
                print(f"  CH measurements:       {self.processing_stats.get('clickhouse_measurements', 0):,}")
                print(f"  CH landing records:    {self.processing_stats.get('clickhouse_landing_records', 0):,}")
            
            # Overall stats
            total_time = self.processing_stats.get('total_parsing_time', 0) + self.processing_stats.get('total_clickhouse_time', 0)
            if total_time > 0:
                throughput = self.processing_stats.get('total_measurements', 0) / total_time
                print(f"\nOverall Performance:")
                print(f"  Total processing time: {total_time:.2f}s")
                print(f"  Overall throughput:    {throughput:.2f} measurements/second")
                print(f"  Platform:              {platform.system()} ({platform.machine()})")
        
        print("=" * 60)


def main():
    """Main function with command-line interface"""
    parser = argparse.ArgumentParser(description="Extract measurements from STDF files with ClickHouse integration (Windows compatible)")
    parser.add_argument("--stdf-file", required=True, help="Path to STDF file")
    parser.add_argument("--push-clickhouse", action="store_true", help="Push results to ClickHouse")
    parser.add_argument("--batch-size", type=int, default=10000, help="ClickHouse batch size")
    parser.add_argument("--stdf-dir", help="Process all STDF files in directory")
    
    # ClickHouse connection args
    parser.add_argument("--ch-host", default="localhost", help="ClickHouse host")
    parser.add_argument("--ch-port", type=int, default=8123, help="ClickHouse HTTP port (default 8123)")
    parser.add_argument("--ch-database", default="default", help="ClickHouse database")
    parser.add_argument("--ch-user", default="default", help="ClickHouse user")
    parser.add_argument("--ch-password", default="", help="ClickHouse password")
    
    args = parser.parse_args()
    
    print("🚀 Extract ALL Measurements + ClickHouse Integration")
    print("   Windows/macOS/Linux Compatible Edition")
    print("=" * 60)
    
    # Process single file or directory
    stdf_files = []
    
    if args.stdf_dir:
        if not os.path.exists(args.stdf_dir):
            print(f"❌ Directory not found: {args.stdf_dir}")
            return 1
        stdf_files = [os.path.join(args.stdf_dir, f) for f in os.listdir(args.stdf_dir) if f.endswith('.stdf')]
        if not stdf_files:
            print(f"❌ No .stdf files found in {args.stdf_dir}")
            return 1
    else:
        if not os.path.exists(args.stdf_file):
            print(f"❌ File not found: {args.stdf_file}")
            return 1
        stdf_files = [args.stdf_file]
    
    print(f"📁 Processing {len(stdf_files)} STDF file(s)")
    
    total_start = time.time()
    overall_measurements = 0
    successful_files = 0
    
    for stdf_file in stdf_files:
        try:
            print(f"\n📂 Processing: {os.path.basename(stdf_file)}")
            
            # Create processor
            processor = STDFProcessor(
                enable_clickhouse=args.push_clickhouse,
                batch_size=args.batch_size
            )
            
            # Extract measurements
            measurements = processor.extract_measurements(stdf_file)
            overall_measurements += len(measurements)
            
            # Push to ClickHouse if requested
            if args.push_clickhouse:
                success = processor.push_to_clickhouse(
                    stdf_file,
                    host=args.ch_host,
                    port=args.ch_port,
                    database=args.ch_database,
                    user=args.ch_user,
                    password=args.ch_password
                )
                if success:
                    print(f"✅ ClickHouse integration completed for {os.path.basename(stdf_file)}")
                else:
                    print(f"❌ ClickHouse integration failed for {os.path.basename(stdf_file)}")
            
            # Print statistics
            processor.print_statistics()
            successful_files += 1
            
        except Exception as e:
            print(f"❌ Error processing {stdf_file}: {e}")
            import traceback
            traceback.print_exc()
            continue
    
    # Overall summary
    total_time = time.time() - total_start
    print(f"\n🎯 OVERALL SUMMARY:")
    print("=" * 40)
    print(f"Files processed:       {successful_files}/{len(stdf_files)}")
    print(f"Total measurements:    {overall_measurements:,}")
    print(f"Total time:            {total_time:.2f}s")
    if total_time > 0:
        print(f"Overall throughput:    {overall_measurements/total_time:.2f} measurements/second")
    print(f"ClickHouse integration: {'✅ Enabled' if args.push_clickhouse else '❌ Disabled'}")
    print(f"Platform:              {platform.system()} ({platform.machine()})")
    
    return 0 if successful_files > 0 else 1


if __name__ == "__main__":
    sys.exit(main())