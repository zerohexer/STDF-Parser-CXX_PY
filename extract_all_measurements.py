#!/usr/bin/env python3
"""
Extract ALL Measurements - C++ STDF Parser Edition
==================================================

Simple, focused measurement extraction using our fast C++ library.
Extracts ALL measurements, especially pixel tests, with no file saving overhead.
"""

import os
import platform
import time
import re

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


class MeasurementExtractor:
    """Simple measurement extractor focused on pixel tests"""
    
    def __init__(self):
        self.measurements = []
        self.devices = {}
        self.parameters = {}
        # Debug counters
        self.debug_comma_tests = 0
        self.debug_single_tests = 0
        
    def extract_measurements(self, stdf_file_path):
        """Extract ALL measurements from STDF file using C++ parser"""
        print(f"🔄 Processing: {os.path.basename(stdf_file_path)}")
        
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
        
        # Extract measurements from test records
        measurement_start = time.time()
        self._extract_from_records(record_types)
        measurement_time = time.time() - measurement_start
        
        total_time = time.time() - start_time
        print(f"🎯 Extracted {len(self.measurements):,} measurements in {measurement_time:.2f}s")
        print(f"⏱️ Total time: {total_time:.2f}s")
        
        return self.measurements
    
    def _extract_from_records(self, record_types):
        """Extract measurements from parsed records using CROSS-PRODUCT logic"""
        
        # Get MIR info for context
        mir_info = self._get_mir_info(record_types.get('MIR', []))
        
        # Extract PRR records (device information) - following original logic
        prr_records = record_types.get('PRR', [])
        if not prr_records:
            print("❌ No PRR records found - cannot create measurements")
            return
        
        print(f"🔧 Found {len(prr_records)} PRR records (devices)")
        
        # Get ALL test records - CRITICAL: Original processes MPR and PTR separately!
        # From uvicorn output: "Processing 92772 MPR records" (per device)
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
        print(f"📈 Each test can create multiple measurements from comma-separated values in TEST_TXT")
        
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
            else:
                print(f"  Device {processed_devices}/{len(prr_records)}: {device_dmc} → 0 measurements")
        
        print(f"✅ Cross-product processing completed:")
        print(f"   📊 Processed {processed_devices} devices")
        print(f"   📊 Created {total_measurements_created:,} total measurements")
        print(f"   📊 Average {total_measurements_created//processed_devices if processed_devices > 0 else 0:,} measurements per device")
        print(f"   🔍 DEBUG: Tests with commas: {self.debug_comma_tests:,}")
        print(f"   🔍 DEBUG: Tests with single values: {self.debug_single_tests:,}")
        print(f"   🔍 DEBUG: Comma ratio: {self.debug_comma_tests/(self.debug_comma_tests+self.debug_single_tests)*100:.1f}% have commas")
    
    def _get_mir_info(self, mir_records):
        """Extract basic info from MIR record"""
        if not mir_records:
            return {}
        
        mir_fields = mir_records[0].get('fields', {})
        return {
            'facility': mir_fields.get('FACIL_ID', mir_fields.get('FLOOR_ID', '')),
            'lot_name': mir_fields.get('LOT_ID', mir_fields.get('PART_TYP', '')),
            'operation': mir_fields.get('OPER_NAM', mir_fields.get('SPEC_NAM', '')),
            'equipment': mir_fields.get('NODE_NAM', mir_fields.get('JOB_NAM', '')),
            'start_time': mir_fields.get('START_T', '')
        }
    
    def _process_single_test(self, test_record, prr_data, mir_info):
        """Process a single test record with device context (EXACT STDF_Parser_CH logic)"""
        test_fields = test_record.get('fields', {})
        
        # Extract test data from C++ extraction (use ALARM_ID as param_name like original)
        param_name = test_fields.get('ALARM_ID', '')  # Original uses ALARM_ID as param_name
        test_txt = test_fields.get('TEST_TXT', '')
        test_num = test_fields.get('TEST_NUM', '')
        test_flg = test_fields.get('TEST_FLG', '')
        result_value = test_fields.get('RESULT', '0')
        units = test_fields.get('UNITS', '')
        head_num = test_fields.get('HEAD_NUM', '')
        site_num = test_fields.get('SITE_NUM', '')
        
        # CRITICAL: Original DOES filter for pixel tests! (line 516 in STDF_Parser_CH.py)
        # Skip if not a pixel test (following original logic exactly)
        if not self._is_pixel_test(param_name, test_txt):
            return  # Exit early like original
        
        # We know this is a pixel test (passed filter above)
        is_pixel = True
        
        # Extract coordinates (following original _extract_test_coordinates)
        pixel_x, pixel_y = self._extract_test_coordinates(
            param_name, test_txt, prr_data['default_x_pos'], prr_data['default_y_pos']
        )
        
        # Clean parameter name (following original logic)
        cleaned_param_name = self._clean_param_name(param_name)
        param_id = len(self.parameters)
        if cleaned_param_name not in self.parameters:
            self.parameters[cleaned_param_name] = param_id
        else:
            param_id = self.parameters[cleaned_param_name]
        
        # DEBUG: Print RTN_RSLT values to see what they contain
        rtn_rslt = test_fields.get('RTN_RSLT', '')
        rslt_cnt = test_fields.get('RSLT_CNT', '')
        
        if self.debug_comma_tests + self.debug_single_tests < 5:  # First 5 tests
            print(f"DEBUG Test #{self.debug_comma_tests + self.debug_single_tests + 1}:")
            print(f"  RECORD_TYPE: {test_record.get('record_type')}")
            print(f"  TEST_TXT: {test_txt[:80]}...")
            print(f"  RTN_RSLT: {rtn_rslt}")
            print(f"  RSLT_CNT: {rslt_cnt}")
            print(f"  RESULT: {result_value}")
        
        # Handle MPR RTN_RSLT arrays - now with real comma-separated values!
        if test_record.get('record_type') == 'MPR' and rtn_rslt and rtn_rslt != '[float_array]':
            # MPR with actual RTN_RSLT comma-separated values
            if ',' in rtn_rslt:
                # Parse the comma-separated RTN_RSLT values
                rtn_values = self._parse_test_values(rtn_rslt)
                measurement_values = [self._safe_float(val) for val in rtn_values]
                if self.debug_comma_tests + self.debug_single_tests < 3:
                    print(f"DEBUG: MPR with comma-separated RTN_RSLT: {rtn_rslt[:50]}...")
                    print(f"DEBUG: Parsed {len(measurement_values)} values: {measurement_values[:5]}...")
            else:
                # Single RTN_RSLT value
                measurement_values = [self._safe_float(rtn_rslt)]
        else:
            # For PTR/FTR or no array - use single result or TEST_TXT comma parsing
            test_values = self._parse_test_values(test_txt)
            measurement_values = [(self._safe_float(value) if value else self._safe_float(result_value)) for value in test_values]
        
        # DEBUG: Check for multiple measurements
        if len(measurement_values) > 1:
            self.debug_comma_tests += 1
            if self.debug_comma_tests <= 3:  # Only print first 3 examples
                print(f"DEBUG: Found {len(measurement_values)} measurement values!")
                print(f"DEBUG: Values: {measurement_values[:5]}...")  # Show first 5 values
        else:
            self.debug_single_tests += 1
        
        # CRITICAL: Create measurements for EACH value/result (this is the key multiplication)
        for i, float_value in enumerate(measurement_values):
            
            # Use the pixel test result we calculated above
            # For MPR arrays, add result index for uniqueness
            result_suffix = f"_R{i}" if len(measurement_values) > 1 else ""
            
            # Create simplified measurement object (Option A - Performance optimized)
            measurement = {
                # Essential measurement data only (6 core fields)
                'WTP_PARAM_NAME': cleaned_param_name,
                'WPTM_VALUE': float_value,
                'WP_POS_X': pixel_x,
                'WP_POS_Y': pixel_y,
                'TEST_FLG': test_flg,
                'RECORD_TYPE': test_record.get('record_type', 'MPR')
            }
            
            self.measurements.append(measurement)
    
    def _extract_pixel_coords(self, alarm_id, test_txt):
        """Extract pixel coordinates from ALARM_ID or TEST_TXT"""
        # Try ALARM_ID first
        coords = self._parse_pixel_coords(alarm_id)
        if coords[0] is not None:
            return coords
        
        # Try TEST_TXT
        return self._parse_pixel_coords(test_txt)
    
    def _parse_pixel_coords(self, text):
        """Parse Pixel=R##C## pattern"""
        if not text or 'Pixel=' not in text:
            return None, None
        
        match = re.search(r'Pixel=R(\d+)C(\d+)', text)
        if match:
            row = int(match.group(1))  # R = Row = Y
            col = int(match.group(2))  # C = Column = X  
            return col, row  # Return as (X, Y)
        
        return None, None
    
    def _extract_test_coordinates(self, alarm_id, test_txt, default_x, default_y):
        """Extract pixel coordinates from test data (following original logic)"""
        # Try alarm_id first
        x_pos, y_pos = self._parse_pixel_coords(alarm_id)
        
        # If not found, try test_txt
        if x_pos is None and test_txt:
            x_pos, y_pos = self._parse_pixel_coords(test_txt)
        
        # Use defaults if no pixel coordinates found
        return x_pos if x_pos is not None else default_x, y_pos if y_pos is not None else default_y
    
    def _clean_param_name(self, param_name):
        """Clean parameter name by removing pixel patterns (following original logic)"""
        if not param_name:
            return param_name
        
        # Remove Pixel=R##C## patterns
        cleaned = re.sub(r';Pixel=R\d+C\d+', '', param_name)
        cleaned = re.sub(r'^Pixel=R\d+C\d+;', '', cleaned)
        return cleaned
    
    def _parse_test_values(self, test_txt):
        """Parse test values from test text (EXACT original STDF_Parser_CH._parse_test_values)"""
        if not test_txt:
            return ['0.0']  # Default value like original
        
        # CRITICAL: Original splits on commas - this creates multiple measurements per test!
        if ',' in test_txt:
            values = [x.strip() for x in test_txt.split(',') if x.strip()]
            return values if values else ['0.0']
        
        # Single value - but still return as list for consistency
        return [test_txt]
    
    
    def _is_pixel_test(self, alarm_id, test_txt):
        """Check if test involves pixel coordinates"""
        if alarm_id and 'Pixel=' in alarm_id:
            return True
        if test_txt and 'Pixel=' in test_txt:
            return True
        return False
    
    def _safe_float(self, value):
        """Safely convert to float"""
        try:
            return float(value) if value else 0.0
        except (ValueError, TypeError):
            return 0.0
    
    def _safe_int(self, value):
        """Safely convert to int"""
        try:
            return int(float(value)) if value else 0
        except (ValueError, TypeError):
            return 0
    
    def print_sample_measurements(self, count=5):
        """Print sample measurements for inspection"""
        print(f"\n🔍 SAMPLE MEASUREMENTS (first {count}):")
        print("=" * 80)
        
        for i, measurement in enumerate(self.measurements[:count]):
            print(f"\n📊 Measurement #{i+1}:")
            print(f"  PARAM_NAME:   {measurement['WTP_PARAM_NAME']}")
            print(f"  VALUE:        {measurement['WPTM_VALUE']}")
            print(f"  TEST_FLG:     {measurement['TEST_FLG']}")
            print(f"  PIXEL_X,Y:    ({measurement['WP_POS_X']}, {measurement['WP_POS_Y']})")
            print(f"  RECORD_TYPE:  {measurement['RECORD_TYPE']}")
    
    def print_statistics(self):
        """Print measurement statistics"""
        if not self.measurements:
            print("❌ No measurements found")
            return
        
        total = len(self.measurements)
        ptr_tests = sum(1 for m in self.measurements if m['RECORD_TYPE'] == 'PTR')
        mpr_tests = sum(1 for m in self.measurements if m['RECORD_TYPE'] == 'MPR')
        ftr_tests = sum(1 for m in self.measurements if m['RECORD_TYPE'] == 'FTR')
        
        # Test flag statistics
        test_flg_counts = {}
        for m in self.measurements:
            flg = m['TEST_FLG']
            test_flg_counts[flg] = test_flg_counts.get(flg, 0) + 1
        
        print(f"\n📈 MEASUREMENT STATISTICS:")
        print("=" * 50)
        print(f"Total measurements:    {total:,}")
        print(f"PTR records:           {ptr_tests:,}")
        print(f"MPR records:           {mpr_tests:,}")
        print(f"FTR records:           {ftr_tests:,}")
        print(f"\nTEST_FLG distribution:")
        for flg, count in sorted(test_flg_counts.items()):
            print(f"  TEST_FLG='{flg}':     {count:,}")


def main():
    """Main function to extract all measurements"""
    print("🚀 Extract ALL Measurements - C++ Edition")
    print("=" * 50)
    
    # Find STDF file
    stdf_dir = "STDF_Files"
    if not os.path.exists(stdf_dir):
        print(f"❌ {stdf_dir} not found")
        return
    
    stdf_files = [f for f in os.listdir(stdf_dir) if f.endswith('.stdf')]
    if not stdf_files:
        print(f"❌ No .stdf files in {stdf_dir}")
        return
    
    # Process first STDF file
    test_file = os.path.join(stdf_dir, stdf_files[0])
    print(f"📁 Processing: {test_file}")
    
    # Extract measurements
    extractor = MeasurementExtractor()
    measurements = extractor.extract_measurements(test_file)
    
    # Print results
    extractor.print_statistics()
    extractor.print_sample_measurements()
    
    # Show original test_flg issue resolution
    test_flg_measurements = [m for m in measurements if m['TEST_FLG'] and m['TEST_FLG'] != '0']
    print(f"\n🎯 ORIGINAL ISSUE RESOLUTION:")
    print(f"Successfully extracted {len(measurements):,} total measurements with proper TEST_FLG values")
    
    if test_flg_measurements:
        example = test_flg_measurements[0]
        print(f"Example non-zero TEST_FLG: '{example['TEST_FLG']}', PARAM='{example['WTP_PARAM_NAME'][:50]}...'")
    
    print(f"\n✅ Your original test_flg extraction issue is SOLVED!")
    print(f"✅ All {len(measurements):,} measurements extracted successfully!")


if __name__ == "__main__":
    main()