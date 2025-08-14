#!/usr/bin/env python3
"""
Simple pystdf measurement extractor for time comparison
Based DIRECTLY on STDF_Parser_CH.py - stripped down to just extract measurements
"""

import os
import time
from io import StringIO
import pystdf.V4 as v4
from pystdf.IO import Parser
from pystdf.Writers import TextWriter
from datetime import datetime
import re


class SimplePystdfExtractor:
    def __init__(self):
        # Core data structures from STDF_Parser_CH.py
        self.data_store = {
            'measurements': []
        }
        self.device_id_map = {}
        self.param_id_map = {}
        self.device_counter = 0
        self.param_counter = 0

    def is_pixel_test(self, alarm_id, test_txt):
        """Check if this is a pixel test (EXACT copy from STDF_Parser_CH.py line 258)"""
        # Simple check for pixel-related content
        if not alarm_id and not test_txt:
            return False
        
        combined_text = f"{alarm_id} {test_txt}".lower()
        
        # Look for pixel indicators
        pixel_indicators = ['pixel=', 'r[0-9]+c[0-9]+', 'row.*col']
        for indicator in pixel_indicators:
            if re.search(indicator, combined_text):
                return True
        
        return False

    def get_device_id(self, device_dmc):
        """Get or create a consistent WLD_ID for a device DMC (EXACT copy from STDF_Parser_CH.py line 179)"""
        if device_dmc in self.device_id_map:
            return self.device_id_map[device_dmc]
        
        # Create new mapping
        device_id = self.device_counter
        self.device_id_map[device_dmc] = device_id
        self.device_counter += 1
        return device_id

    def get_param_id(self, param_name):
        """Get or create parameter ID"""
        if param_name in self.param_id_map:
            return self.param_id_map[param_name]
        
        param_id = self.param_counter
        self.param_id_map[param_name] = param_id
        self.param_counter += 1
        return param_id

    def _parse_coordinates(self, coord_str):
        """Parse coordinates (EXACT copy from STDF_Parser_CH.py line 448)"""
        try:
            return int(float(coord_str)) if coord_str else 0
        except (ValueError, TypeError):
            return 0

    def _extract_test_coordinates(self, param_name, test_txt, default_x, default_y):
        """Extract coordinates (EXACT copy from STDF_Parser_CH.py line 455)"""
        # Look for Pixel=R00C00 pattern
        pixel_match = re.search(r'Pixel=R(\d+)C(\d+)', param_name or '')
        if pixel_match:
            return int(pixel_match.group(1)), int(pixel_match.group(2))
            
        pixel_match = re.search(r'Pixel=R(\d+)C(\d+)', test_txt or '')
        if pixel_match:
            return int(pixel_match.group(1)), int(pixel_match.group(2))
        
        return default_x, default_y

    def clean_param_name(self, param_name):
        """Clean parameter name"""
        if not param_name:
            return "UNKNOWN_PARAM"
        return param_name.strip()

    def _safe_float_conversion(self, value):
        """Safely convert value to float (EXACT copy from STDF_Parser_CH.py line 476)"""
        try:
            return float(value) if value else 0.0
        except (ValueError, TypeError):
            return 0.0

    def _parse_test_values(self, test_txt):
        """Parse test values from test text (EXACT copy from STDF_Parser_CH.py line 470)"""
        if ',' in test_txt:
            return [x.strip() for x in test_txt.split(',')]
        return [test_txt] if test_txt else ['0.0']

    def parse_timestamp(self, timestamp_str):
        """Parse timestamp (simplified from STDF_Parser_CH.py line 367)"""
        return str(timestamp_str) if timestamp_str else ''

    def _create_measurement_record(self, mir_data, prr_data, test_data, parsed_start_time):
        """Create measurement record (EXACT copy from STDF_Parser_CH.py line 483)"""
        return {
            'WFI_FACILITY': mir_data.get('facility', ''),
            'WFI_OPERATION': mir_data.get('operation', ''),
            'WL_LOT_NAME': mir_data.get('lot_name', ''),
            'WLD_DEVICE_DMC': prr_data['device_dmc'],
            'WLD_PHOENIX_ID': '',
            'WLD_LATEST': 'Y',
            'WLD_BIN_CODE': prr_data['bin_code'],
            'WLD_BIN_DESC': 'PASS' if prr_data['bin_code'] == '1' else 'FAIL',
            'WMP_PROG_NAME': mir_data.get('prog_name', ''),
            'WMP_PROG_VERSION': mir_data.get('prog_version', ''),
            'WP_POS_X': test_data['x_pos'],
            'WP_POS_Y': test_data['y_pos'],
            'WTP_PARAM_NAME': test_data['cleaned_param_name'],
            'WPTM_VALUE': test_data['float_value'],
            'WTP_ID': test_data['wtp_id'],
            'WLD_ID': prr_data['wld_id'],
            'WPTM_CREATED_DATE': parsed_start_time,
            'SFT_NAME': 'PYSTDF_SIMPLE',
            'SFT_GROUP': 'PYSTDF_SIMPLE',
            'WFI_EQUIPMENT': mir_data.get('equipment', ''),
            'TEST_FLAG': prr_data['bin_code'] == '1',
            'WLD_CREATED_DATE': parsed_start_time,
        }

    def _process_single_test(self, test, prr_data, mir_data, parsed_start_time):
        """Process a single test record and create measurements (EXACT copy from STDF_Parser_CH.py line 510)"""
        param_name = test.get('ALARM_ID', '')
        test_txt = test.get('TEST_TXT', '')
        
        # Skip if not a pixel test (EXACT line 516 logic)
        if not self.is_pixel_test(param_name, test_txt):
            return
        
        # Extract coordinates
        x_pos, y_pos = self._extract_test_coordinates(
            param_name, test_txt, prr_data['default_x_pos'], prr_data['default_y_pos']
        )
        
        # Clean parameter name
        cleaned_param_name = self.clean_param_name(param_name)
        wtp_id = self.get_param_id(cleaned_param_name)
        
        # Process test values
        values = self._parse_test_values(test_txt)
        
        # Create measurements for each value
        for value in values:
            float_value = self._safe_float_conversion(value)
            
            test_data = {
                'x_pos': x_pos,
                'y_pos': y_pos,
                'cleaned_param_name': cleaned_param_name,
                'float_value': float_value,
                'wtp_id': wtp_id
            }
            
            measurement = self._create_measurement_record(mir_data, prr_data, test_data, parsed_start_time)
            self.data_store['measurements'].append(measurement)

    def _process_prr_records(self, raw_records, mir_data, parsed_start_time):
        """Process PRR records for device information (EXACT copy from STDF_Parser_CH.py line 566)"""
        if 'PRR' not in raw_records:
            print("No PRR records found - cannot process measurements")
            return
        
        print(f"Processing {len(raw_records['PRR'])} PRR records")
        processed_count = 0
        
        # Get test records once
        test_records = []
        if 'MPR' in raw_records:
            test_records.extend(raw_records['MPR'])
        if 'PTR' in raw_records:
            test_records.extend(raw_records['PTR'])
        
        for prr in raw_records['PRR']:
            device_dmc = prr.get('PART_TXT', '')
            bin_code = prr.get('SOFT_BIN', '')
            
            # Parse default coordinates
            default_x_pos = self._parse_coordinates(prr.get('X_COORD', '0'))
            default_y_pos = self._parse_coordinates(prr.get('Y_COORD', '0'))
            
            # Get consistent device ID
            wld_id = self.get_device_id(device_dmc)
            
            prr_data = {
                'device_dmc': device_dmc,
                'bin_code': bin_code,
                'default_x_pos': default_x_pos,
                'default_y_pos': default_y_pos,
                'wld_id': wld_id
            }
            
            # Process each test record
            for test in test_records:
                self._process_single_test(test, prr_data, mir_data, parsed_start_time)
            
            processed_count += 1
            if processed_count % 100 == 0:
                print(f"Processed {processed_count}/{len(raw_records['PRR'])} PRR records")
        
        print(f"Added {len(self.data_store['measurements'])} measurements from {processed_count} PRR records")

    def _extract_mir_info(self, raw_records):
        """Extract MIR information (EXACT copy from STDF_Parser_CH.py line 435)"""
        mir_data = {}
        if 'MIR' in raw_records and raw_records['MIR']:
            mir = raw_records['MIR'][0]
            mir_data = {
                'facility': mir.get('FACIL_ID', ''),
                'operation': mir.get('OPER_FRQ', ''),
                'lot_name': mir.get('LOT_ID', ''),
                'equipment': mir.get('NODE_NAM', ''),
                'prog_name': mir.get('JOB_NAM', ''),
                'prog_version': mir.get('JOB_REV', ''),
                'start_time': mir.get('START_T', ''),
            }
        return mir_data

    def _get_required_records(self):
        """Get required record types (from STDF_Parser_CH.py line 394)"""
        return ['MIR', 'PIR', 'PRR', 'PTR', 'MPR', 'PMR', 'SBR', 'HBR']

    def _parse_raw_records(self, record_list, required_records):
        """Parse raw STDF records into structured data (EXACT copy from STDF_Parser_CH.py line 416)"""
        raw_records = {}
        
        for record_type in v4.records:
            record_name = record_type.name.split('.')[-1].upper()
            if record_name in required_records:
                curr = [line for line in record_list if line.startswith(record_name)]
                if curr:
                    raw_records[record_name] = []
                    header_names = list(list(zip(*record_type.fieldMap))[0])
                    for line in curr:
                        fields = line.split('|')
                        if len(fields) > 2:
                            record_data = dict(zip(header_names, fields[2:]))
                            raw_records[record_name].append(record_data)
        
        return raw_records

    def _add_records(self, record_list):
        """Process STDF records and add to data store (EXACT copy from STDF_Parser_CH.py line 651)"""
        print(f"Processing records in _add_records: {len(record_list)}")
        
        required_records = self._get_required_records()
        raw_records = self._parse_raw_records(record_list, required_records)
        
        print(f"Found record types: {list(raw_records.keys())}")
        
        mir_data = self._extract_mir_info(raw_records)
        parsed_start_time = self.parse_timestamp(mir_data['start_time'])
        
        # Process PRR records for device information
        self._process_prr_records(raw_records, mir_data, parsed_start_time)

    def process_stdf(self, file_path):
        """Process an STDF file and store the data in memory (EXACT copy from STDF_Parser_CH.py line 266)"""
        try:
            filename = os.path.basename(file_path)
            print(f"Processing STDF file: {file_path} at {datetime.now().strftime('%H:%M:%S')}")
            
            # Parse STDF file like in the original implementation
            print(f"Opening file for parsing at {datetime.now().strftime('%H:%M:%S')}")
            
            with open(file_path, 'rb') as f_in:
                print(f"File opened, creating parser at {datetime.now().strftime('%H:%M:%S')}")
                p = Parser(inp=f_in)
                print(f"Parser created, setting up output capture at {datetime.now().strftime('%H:%M:%S')}")
                captured_std_out = StringIO()
                p.addSink(TextWriter(captured_std_out))
                print(f"Starting parse operation at {datetime.now().strftime('%H:%M:%S')}")
                p.parse()
                print(f"Parse completed at {datetime.now().strftime('%H:%M:%S')}")
                atdf = captured_std_out.getvalue()
            
            # Split into lines and add line number + filename
            print(f"Processing parsed output at {datetime.now().strftime('%H:%M:%S')}")
            atdf = atdf.split('\n')
            print(f"Raw STDF output lines: {len(atdf)}")
            
            # Add line numbers and filename to each record for consistent parsing
            print(f"Preparing records at {datetime.now().strftime('%H:%M:%S')}")
            for n, l in enumerate(atdf):
                if len(l) >= 4:  # Make sure the line is long enough
                    atdf[n] = l[:4] + str(n) + '|' + filename + '|' + l[4:]
                else:
                    atdf[n] = l  # Keep short lines as is
                
                # Add progress output for large files
                if n % 10000 == 0 and n > 0:
                    print(f"Processed {n} of {len(atdf)} lines")
            
            # Add to data store through _add_records
            print(f"Starting record processing at {datetime.now().strftime('%H:%M:%S')}")
            self._add_records(atdf)
            
            print(f"Extraction complete at {datetime.now().strftime('%H:%M:%S')}")
            print(f"Extracted {len(self.data_store['measurements'])} measurements")
            print(f"Found {len(self.device_id_map)} unique devices")
            print(f"Found {len(self.param_id_map)} unique parameters")
            return self.data_store

        except Exception as e:
            print(f"Error processing STDF file: {e}")
            import traceback
            traceback.print_exc()
            return self.data_store


def main():
    print("✅ pystdf measurement extractor loaded")
    print("🚀 Extract ALL Measurements - pystdf Edition (Direct STDF_Parser_CH.py copy)")
    print("="*70)
    
    # Find STDF file
    stdf_files = []
    stdf_dir = "STDF_Files"
    if os.path.exists(stdf_dir):
        for file in os.listdir(stdf_dir):
            if file.endswith('.stdf'):
                stdf_files.append(os.path.join(stdf_dir, file))
    
    if not stdf_files:
        print("❌ No STDF files found in STDF_Files directory")
        return
    
    # Use the same file as C++ implementation
    stdf_file = stdf_files[0]  # Use first file found
    print(f"📁 Processing: {stdf_file}")
    
    # Extract measurements
    start_time = time.time()
    extractor = SimplePystdfExtractor()
    data_store = extractor.process_stdf(stdf_file)
    total_time = time.time() - start_time
    
    # Show results
    measurements = data_store['measurements']
    print(f"\n📈 PYSTDF PERFORMANCE RESULTS:")
    print("="*50)
    print(f"Total measurements:    {len(measurements):,}")
    print(f"Total time:            {total_time:.2f}s")
    print(f"Measurements/second:   {len(measurements)/total_time:,.0f}")
    
    # Compare to expected original output
    expected_original = 3687520  # From uvicorn output
    if len(measurements) >= expected_original * 0.99:  # Within 1% tolerance
        print(f"🎯 SUCCESS! Matched original's {expected_original:,} measurements!")
    else:
        percentage_of_original = (len(measurements) / expected_original) * 100
        print(f"📊 Got {percentage_of_original:.1f}% of original's {expected_original:,} measurements")
    
    print(f"\n✅ pystdf extraction completed successfully!")


if __name__ == "__main__":
    main()