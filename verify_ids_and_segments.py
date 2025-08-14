#!/usr/bin/env python3
"""
Verify WLD_ID, WTP_ID, and Segments - Check if our ID fix worked
"""
import sys
import os
from collections import Counter
sys.path.append('.')

def verify_ids_and_segments():
    try:
        print("🔄 Verifying WLD_ID, WTP_ID, and segment generation after fix...")
        
        from extract_all_measurements_plus_clickhouse_connect import STDFProcessor
        processor = STDFProcessor(enable_clickhouse=False)
        stdf_file = 'STDF_Files/OSBE25_KEWGBCLD1U_BE_HRG3301Y.06_KEWGBCLD1U__Prod_TPP202_03_Agilent_93000MT9510_25C_5264_2_20240903225946.stdf'
        
        print('🔄 Getting measurements to check ID assignments...')
        measurements = processor.extract_measurements(stdf_file)
        
        if measurements:
            print(f'✅ Extracted {len(measurements)} measurements')
            
            # Check first 10 measurements for ID values
            print(f'\n📊 First 10 measurements ID analysis:')
            for i in range(min(10, len(measurements))):
                m = measurements[i]
                print(f'   Measurement {i}:')
                print(f'     WLD_DEVICE_DMC: {repr(m.get("WLD_DEVICE_DMC", "MISSING"))}')
                print(f'     WLD_ID: {m.get("WLD_ID", "MISSING")}')
                print(f'     WTP_PARAM_NAME: {repr(m.get("WTP_PARAM_NAME", "MISSING"))}')
                print(f'     WTP_ID: {m.get("WTP_ID", "MISSING")}')
                print(f'     WP_POS_X: {m.get("WP_POS_X", "MISSING")}')
                print(f'     WP_POS_Y: {m.get("WP_POS_Y", "MISSING")}')
                print(f'     TEST_FLG: {repr(m.get("TEST_FLG", "MISSING"))}')
                print()
            
            # Analyze ID distributions
            sample_size = min(10000, len(measurements))
            print(f'📈 ID Distribution Analysis (first {sample_size:,} measurements):')
            
            # WLD_ID distribution
            wld_ids = [m.get('WLD_ID', 'MISSING') for m in measurements[:sample_size]]
            wld_id_counter = Counter(wld_ids)
            print(f'\n🏢 WLD_ID distribution:')
            for wld_id, count in wld_id_counter.most_common():
                percentage = (count / sample_size) * 100
                print(f'   WLD_ID {wld_id}: {count:,} ({percentage:.1f}%)')
            
            # WTP_ID distribution  
            wtp_ids = [m.get('WTP_ID', 'MISSING') for m in measurements[:sample_size]]
            wtp_id_counter = Counter(wtp_ids)
            print(f'\n📊 WTP_ID distribution (top 20):')
            for wtp_id, count in wtp_id_counter.most_common(20):
                percentage = (count / sample_size) * 100
                print(f'   WTP_ID {wtp_id}: {count:,} ({percentage:.1f}%)')
            
            print(f'\n📊 Total unique IDs:')
            print(f'   Unique WLD_IDs: {len(wld_id_counter)}')
            print(f'   Unique WTP_IDs: {len(wtp_id_counter)}')
            
            # Test duplicate key generation with fixed IDs
            print(f'\n🔍 Testing duplicate key generation with fixed IDs...')
            duplicate_tracker = {}
            segments_over_255 = []
            
            # Apply the same segment logic as our main code but with updated measurements
            from datetime import datetime
            current_time = datetime.now()
            
            # Test on sample
            test_size = min(50000, len(measurements))
            print(f'🧪 Testing segment generation on {test_size:,} measurements...')
            
            for i in range(test_size):
                measurement = measurements[i]
                
                # Apply the same duplicate key logic from our main code
                duplicate_key = (
                    measurement.get('WLD_ID', 0),
                    measurement.get('WTP_ID', 0), 
                    str(measurement.get('WP_POS_X', 0)),
                    str(measurement.get('WP_POS_Y', 0)),
                    measurement.get('TEST_FLG', 0)
                )
                
                if duplicate_key in duplicate_tracker:
                    segment = duplicate_tracker[duplicate_key] + 1
                    duplicate_tracker[duplicate_key] = segment
                else:
                    segment = 0
                    duplicate_tracker[duplicate_key] = 0
                
                if segment > 255:
                    segments_over_255.append((i, segment, duplicate_key))
                    if len(segments_over_255) >= 10:  # Stop after finding 10 examples
                        break
            
            print(f'\n📊 Segment Analysis Results:')
            print(f'   Test sample size: {test_size:,}')
            print(f'   Unique duplicate keys: {len(duplicate_tracker):,}')
            print(f'   Max segment value: {max(duplicate_tracker.values()) if duplicate_tracker else 0}')
            print(f'   Segments over 255: {len(segments_over_255)}')
            
            if segments_over_255:
                print(f'\n⚠️ Still found segments over 255:')
                for idx, segment_val, dup_key in segments_over_255[:5]:
                    print(f'     Index {idx}: segment = {segment_val}, key = {dup_key}')
            else:
                print(f'\n✅ All segments under 255!')
            
            # Show most duplicated keys
            top_duplicates = sorted(duplicate_tracker.items(), key=lambda x: x[1], reverse=True)[:10]
            print(f'\n🔍 Top 10 most duplicated keys:')
            for key, count in top_duplicates:
                print(f'     {key}: {count} duplicates')
            
            # Compare to expected Python parser results
            print(f'\n📊 Comparison to Python parser:')
            python_unique_keys = 92440
            python_max_segment = 39
            
            improvement_keys = len(duplicate_tracker) / python_unique_keys if python_unique_keys else 0
            print(f'   Expected unique keys (Python): {python_unique_keys:,}')
            print(f'   Our unique keys (C++): {len(duplicate_tracker):,}')
            print(f'   Ratio: {improvement_keys:.2f}x')
            
            print(f'   Expected max segment (Python): {python_max_segment}')
            print(f'   Our max segment (C++): {max(duplicate_tracker.values()) if duplicate_tracker else 0}')
            
            if len(duplicate_tracker) > 50000 and max(duplicate_tracker.values()) < 100:
                print(f'\n🎉 SUCCESS: ID fix appears to be working!')
            else:
                print(f'\n⚠️ ID fix may not be working as expected')
                
        else:
            print('❌ No measurements extracted')
            
    except Exception as e:
        print(f'❌ Error: {e}')
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    verify_ids_and_segments()