#!/usr/bin/env python3
"""
Enhanced STDF C++ Parser Test - Extract Measurements
Similar to Python parser but with C++ performance
"""

import sys
import os
import platform
import time
from collections import defaultdict, Counter
import json

def setup_platform_libraries():
    """Setup libraries for the current platform"""
    system = platform.system().lower()
    
    if system == "linux":
        lib_dir = os.path.join(os.path.dirname(__file__), "cpp", "third_party", "lib")
        current_path = os.environ.get("LD_LIBRARY_PATH", "")
        if lib_dir not in current_path:
            os.environ["LD_LIBRARY_PATH"] = f"{lib_dir}:{current_path}" if current_path else lib_dir
        print(f" Linux: Set library path to {lib_dir}")
        
    elif system == "windows":
        print("🪟 Windows: Using static linking (no DLL dependencies)")
        lib_dir = os.path.join(os.path.dirname(__file__), "cpp", "third_party", "lib")
        if os.path.exists(lib_dir) and hasattr(os, 'add_dll_directory'):
            try:
                os.add_dll_directory(lib_dir)
                print(f" Added DLL directory: {lib_dir}")
            except:
                pass

def extract_measurements(records):
    """Extract measurements similar to Python parser"""
    measurements = []
    devices = set()
    parameters = set()
    
    # Group records by type for analysis
    record_types = defaultdict(list)
    for record in records:
        record_type = record.get('record_type', 'UNKNOWN')
        record_types[record_type].append(record)
    
    print(f"\n Record Type Summary:")
    for rtype, recs in record_types.items():
        print(f"  {rtype}: {len(recs)} records")
    
    # Extract MIR (Master Information Record) data
    mir_data = {}
    if 'MIR' in record_types:
        mir = record_types['MIR'][0]  # Usually one MIR per file
        fields = mir.get('fields', {})
        mir_data = {
            'lot_name': fields.get('LOT_ID', ''),
            'wafer_id': fields.get('WAFER_ID', ''),
            'part_typ': fields.get('PART_TYP', ''),
            'job_nam': fields.get('JOB_NAM', ''),
            'node_nam': fields.get('NODE_NAM', ''),
            'setup_t': fields.get('SETUP_T', ''),
            'start_t': fields.get('START_T', ''),
            'stat_num': fields.get('STAT_NUM', ''),
            'mode_cod': fields.get('MODE_COD', ''),
            'rtst_cod': fields.get('RTST_COD', ''),
            'prot_cod': fields.get('PROT_COD', ''),
            'burn_tim': fields.get('BURN_TIM', ''),
            'cmod_cod': fields.get('CMOD_COD', '')
        }
        print(f"\n MIR Data:")
        print(f"  Lot: {mir_data['lot_name']}")
        print(f"  Wafer: {mir_data['wafer_id']}")
        print(f"  Part Type: {mir_data['part_typ']}")
        print(f"  Job: {mir_data['job_nam']}")
        print(f"  Node: {mir_data['node_nam']}")
    
    # Process PTR (Parametric Test Records)
    if 'PTR' in record_types:
        print(f"\n Processing {len(record_types['PTR'])} PTR records...")
        for ptr in record_types['PTR']:
            fields = ptr.get('fields', {})
            
            measurement = {
                'record_type': 'PTR',
                'test_num': ptr.get('test_num', 0),
                'head_num': ptr.get('head_num', 0),
                'site_num': ptr.get('site_num', 0),
                'result': ptr.get('result', 0.0),
                'test_flg': fields.get('TEST_FLG', ''),
                'parm_flg': fields.get('PARM_FLG', ''),
                'test_txt': ptr.get('test_txt', ''),
                'alarm_id': ptr.get('alarm_id', ''),
                'opt_flag': fields.get('OPT_FLAG', ''),
                'res_scal': fields.get('RES_SCAL', ''),
                'llm_scal': fields.get('LLM_SCAL', ''),
                'hlm_scal': fields.get('HLM_SCAL', ''),
                'lo_limit': fields.get('LO_LIMIT', ''),
                'hi_limit': fields.get('HI_LIMIT', ''),
                'units': ptr.get('units', ''),
                'c_resfmt': fields.get('C_RESFMT', ''),
                'c_llmfmt': fields.get('C_LLMFMT', ''),
                'c_hlmfmt': fields.get('C_HLMFMT', ''),
                'lo_spec': fields.get('LO_SPEC', ''),
                'hi_spec': fields.get('HI_SPEC', '')
            }


            
            # Extract device info (similar to your Python parser)
            if measurement['test_txt']:
                parameters.add(measurement['test_txt'])
            if measurement['alarm_id']:
                parameters.add(measurement['alarm_id'])
                
            measurements.append(measurement)
    
    # Process MPR (Multiple-Result Parametric Records)
    if 'MPR' in record_types:
        print(f"\n Processing {len(record_types['MPR'])} MPR records...")
        for mpr in record_types['MPR']:
            fields = mpr.get('fields', {})
            
            measurement = {
                'record_type': 'MPR', 
                'test_num': mpr.get('test_num', 0),
                'head_num': mpr.get('head_num', 0),
                'site_num': mpr.get('site_num', 0),
                'test_flg': fields.get('TEST_FLG', ''),
                'parm_flg': fields.get('PARM_FLG', ''),
                'rtn_icnt': fields.get('RTN_ICNT', ''),
                'rslt_cnt': fields.get('RSLT_CNT', ''),
                'test_txt': mpr.get('test_txt', ''),
                'alarm_id': mpr.get('alarm_id', ''),
                'opt_flag': fields.get('OPT_FLAG', ''),
                'res_scal': fields.get('RES_SCAL', ''),
                'llm_scal': fields.get('LLM_SCAL', ''),
                'hlm_scal': fields.get('HLM_SCAL', ''),
                'lo_limit': fields.get('LO_LIMIT', ''),
                'hi_limit': fields.get('HI_LIMIT', ''),
                'start_in': fields.get('START_IN', ''),
                'incr_in': fields.get('INCR_IN', ''),
                'rtn_stat': fields.get('RTN_STAT', ''),
                'rtn_rslt': fields.get('RTN_RSLT', '')
            }
            
            if measurement['test_txt']:
                parameters.add(measurement['test_txt'])
            if measurement['alarm_id']:
                parameters.add(measurement['alarm_id'])
                
            measurements.append(measurement)
    
    # Process FTR (Functional Test Records)  
    if 'FTR' in record_types:
        print(f"\n Processing {len(record_types['FTR'])} FTR records...")
        for ftr in record_types['FTR']:
            fields = ftr.get('fields', {})
            
            measurement = {
                'record_type': 'FTR',
                'test_num': ftr.get('test_num', 0),
                'head_num': ftr.get('head_num', 0), 
                'site_num': ftr.get('site_num', 0),
                'test_flg': fields.get('TEST_FLG', ''),
                'opt_flag': fields.get('OPT_FLAG', ''),
                'cycl_cnt': fields.get('CYCL_CNT', ''),
                'rel_vadr': fields.get('REL_VADR', ''),
                'rept_cnt': fields.get('REPT_CNT', ''),
                'num_fail': fields.get('NUM_FAIL', ''),
                'xfail_ad': fields.get('XFAIL_AD', ''),
                'yfail_ad': fields.get('YFAIL_AD', ''),
                'vect_nam': fields.get('VECT_NAM', ''),
                'time_set': fields.get('TIME_SET', ''),
                'op_code': fields.get('OP_CODE', ''),
                'test_txt': ftr.get('test_txt', ''),
                'alarm_id': ftr.get('alarm_id', ''),
                'prog_txt': fields.get('PROG_TXT', ''),
                'rslt_txt': fields.get('RSLT_TXT', ''),
                'patg_num': fields.get('PATG_NUM', ''),
                'spin_map': fields.get('SPIN_MAP', '')
            }
            
            if measurement['test_txt']:
                parameters.add(measurement['test_txt'])
            if measurement['alarm_id']:
                parameters.add(measurement['alarm_id'])
                
            measurements.append(measurement)
    
    # Process PRR (Part Result Records) for device information
    prr_devices = []
    if 'PRR' in record_types:
        print(f"\n Processing {len(record_types['PRR'])} PRR records...")
        for prr in record_types['PRR']:
            fields = prr.get('fields', {})
            
            device_info = {
                'head_num': prr.get('head_num', 0),
                'site_num': prr.get('site_num', 0),
                'part_flg': fields.get('PART_FLG', ''),
                'num_test': fields.get('NUM_TEST', ''),
                'hard_bin': fields.get('HARD_BIN', ''),
                'soft_bin': fields.get('SOFT_BIN', ''),
                'x_coord': fields.get('X_COORD', ''),
                'y_coord': fields.get('Y_COORD', ''),
                'test_t': fields.get('TEST_T', ''),
                'part_id': fields.get('PART_ID', ''),
                'part_txt': fields.get('PART_TXT', ''),
                'part_fix': fields.get('PART_FIX', '')
            }
            
            if device_info['part_txt']:
                devices.add(device_info['part_txt'])
            if device_info['part_id']:
                devices.add(device_info['part_id'])
                
            prr_devices.append(device_info)
    
    return {
        'measurements': measurements,
        'devices': list(devices),
        'parameters': list(parameters), 
        'mir_data': mir_data,
        'prr_devices': prr_devices,
        'record_summary': {k: len(v) for k, v in record_types.items()}
    }

def analyze_measurements(extracted_data):
    """Analyze measurements like Python parser"""
    measurements = extracted_data['measurements']
    devices = extracted_data['devices']
    parameters = extracted_data['parameters']
    
    print(f"\n Measurement Analysis:")
    print(f"  Total measurements: {len(measurements):,}")
    print(f"  Unique devices: {len(devices):,}")
    print(f"  Unique parameters: {len(parameters):,}")
    
    # Analyze by record type
    type_counts = Counter(m['record_type'] for m in measurements)
    print(f"\n Measurement Types:")
    for mtype, count in type_counts.most_common():
        print(f"  {mtype}: {count:,} measurements")
    
    # Show parameter samples
    if parameters:
        print(f"\n Sample Parameters:")
        for i, param in enumerate(parameters[:10]):
            print(f"  {i+1}. {param}")
        if len(parameters) > 10:
            print(f"  ... and {len(parameters) - 10} more")
    
    # Show device samples
    if devices:
        print(f"\n Sample Devices:")
        for i, device in enumerate(devices[:5]):
            print(f"  {i+1}. {device}")
        if len(devices) > 5:
            print(f"  ... and {len(devices) - 5} more")
    
    # Analyze PRR devices
    prr_devices = extracted_data['prr_devices']
    if prr_devices:
        print(f"\n Device Summary:")
        hard_bins = Counter(d['hard_bin'] for d in prr_devices if d['hard_bin'])
        soft_bins = Counter(d['soft_bin'] for d in prr_devices if d['soft_bin'])
        
        print(f"  Total parts tested: {len(prr_devices):,}")
        if hard_bins:
            print(f"  Hard bin distribution: {dict(hard_bins.most_common(5))}")
        if soft_bins:
            print(f"  Soft bin distribution: {dict(soft_bins.most_common(5))}")

def test_measurements():
    """Test the STDF parser with measurement extraction"""
    
    setup_platform_libraries()
    
    try:
        import stdf_parser_cpp
        print(" Extension loaded successfully")
        print(f"Version: {stdf_parser_cpp.get_version()}")
        
    except ImportError as e:
        print(f" Failed to load extension: {e}")
        return False
    
    # Test with STDF files
    stdf_dir = "STDF_Files"
    if not os.path.exists(stdf_dir):
        print(f"  STDF_Files directory not found")
        return True
    
    stdf_files = [f for f in os.listdir(stdf_dir) if f.endswith('.stdf')]
    if not stdf_files:
        print("  No .stdf files found in STDF_Files directory")
        return True
    
    # Test with first file
    test_file = os.path.join(stdf_dir, stdf_files[0])
    print(f"\n Testing with: {os.path.basename(test_file)}")
    
    try:
        print(" Starting C++ STDF parsing...")
        start_time = time.time()
        result = stdf_parser_cpp.parse_stdf_file(test_file)
        end_time = time.time()
        
        print(f" C++ parsing completed in {end_time - start_time:.2f} seconds")
        
        # Handle different result formats
        if isinstance(result, dict):
            records = result.get('records', [])
            total_records = result.get('total_records', 0)
            parsed_records = result.get('parsed_records', 0)
            print(f"Total records in file: {total_records:,}")
            print(f"Records parsed: {parsed_records:,}")
        elif isinstance(result, list):
            records = result
            print(f"Raw records returned: {len(records):,}")
        else:
            print(f"Unexpected result type: {type(result)}")
            print(f"Result: {result}")
            return False
        
        print(f"Records to process: {len(records):,}")
        
        # Debug: Check first record format
        if records:
            print(f"\n First record format:")
            print(f"  Type: {type(records[0])}")
            if hasattr(records[0], '__dict__'):
                print(f"  Content: {records[0].__dict__}")
            elif isinstance(records[0], dict):
                print(f"  Keys: {list(records[0].keys())}")
            else:
                print(f"  Value: {repr(records[0])[:200]}...")
        
        # Extract measurements (like Python parser)
        print("\n Extracting measurements (like Python parser)...")
        extract_start = time.time()
        extracted_data = extract_measurements(records)
        extract_end = time.time()
        
        print(f" Measurement extraction completed in {extract_end - extract_start:.2f} seconds")
        
        # Analyze results
        analyze_measurements(extracted_data)
        
        # Performance summary
        total_time = extract_end - start_time
        print(f"\n Performance Summary:")
        print(f"  C++ parsing: {end_time - start_time:.2f}s")
        print(f"  Data extraction: {extract_end - extract_start:.2f}s") 
        print(f"  Total time: {total_time:.2f}s")
        print(f"  Records/second: {len(records)/total_time:,.0f}")
        print(f"  Platform: {platform.system()} {platform.machine()}")
        
        return True
        
    except Exception as e:
        print(f" Error during testing: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("STDF C++ Parser - Measurement Extraction Test")
    print("=" * 60)
    
    success = test_measurements()
    
    print("=" * 60)
    if success:
        print("Test completed successfully!")
    else:
        print("Test failed!")
    
    sys.exit(0 if success else 1)