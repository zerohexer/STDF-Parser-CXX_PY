#!/usr/bin/env python3
"""
Performance Comparison: Updated C++ vs Python STDF Parsers
"""
import os
import sys
import time

def test_cpp_parser():
    """Test the fixed C++ parser"""
    print("🚀 Testing C++ Parser (Fixed)")
    print("=" * 40)
    
    try:
        import stdf_parser_cpp
        
        test_file = "STDF_Files/OSBE25_KEWGBBMD1U_BE_HRG39021_KEWGBBMD1U__Prod_TPP202_03_Agilent_93000MT9510_25C_5215_4_20241017193900.stdf"
        
        if not os.path.exists(test_file):
            print(f"❌ Test file not found: {test_file}")
            return None
            
        print(f"📁 Testing file: {os.path.basename(test_file)}")
        
        # Test C++ parser
        start_time = time.time()
        result = stdf_parser_cpp.parse_stdf_file(test_file)
        end_time = time.time()
        
        cpp_time = end_time - start_time
        
        if isinstance(result, dict):
            total_records = result.get('total_records', 0)
            parsed_records = result.get('parsed_records', 0)
            records = result.get('records', [])
            
            print(f"📊 C++ Results:")
            print(f"  Total records: {total_records:,}")
            print(f"  Parsed records: {parsed_records:,}")
            print(f"  Records returned: {len(records):,}")
            print(f"  Parse time: {cpp_time:.2f} seconds")
            print(f"  Records per second: {parsed_records/cpp_time:,.0f}")
            
            # Count record types
            record_types = {}
            for record in records:
                rec_type = record.get('record_type', 'UNKNOWN')
                record_types[rec_type] = record_types.get(rec_type, 0) + 1
            
            print(f"\n📈 Record Type Breakdown:")
            for rec_type in sorted(record_types.keys(), key=lambda x: record_types[x], reverse=True):
                count = record_types[rec_type]
                if count > 0:
                    print(f"  {rec_type}: {count:,} records")
            
            return {
                'total_records': total_records,
                'parsed_records': parsed_records,
                'parse_time': cpp_time,
                'records_per_second': parsed_records/cpp_time,
                'record_types': record_types
            }
        
    except Exception as e:
        print(f"❌ C++ parser failed: {e}")
        import traceback
        traceback.print_exc()
        return None

def run_python_comparison(cpp_results):
    """Run the Python fair comparison test with dynamic C++ results"""
    print(f"\n🐍 Running Python Fair Comparison Test...")
    print("=" * 50)
    
    # Change to Python parser directory
    python_dir = "../STDFReader_Extreme_AW_Simple"
    if os.path.exists(python_dir):
        original_dir = os.getcwd()
        try:
            os.chdir(python_dir)
            import subprocess
            import json
            import tempfile
            
            # Create temporary file with dynamic C++ results
            cpp_data = {
                'record_types': cpp_results['record_types'],
                'parsed_records': cpp_results['parsed_records'],
                'parse_time': cpp_results['parse_time'],
                'records_per_second': cpp_results['records_per_second']
            }
            
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
                json.dump(cpp_data, f)
                cpp_results_file = f.name
            
            # Pass C++ results file as argument
            result = subprocess.run([sys.executable, "test_fair_comparison.py", "--cpp-results", cpp_results_file], 
                                  capture_output=True, text=True, encoding='utf-8', 
                                  errors='replace', timeout=120)
            
            # Clean up temp file
            os.unlink(cpp_results_file)
            
            if result.returncode == 0:
                print("✅ Python comparison completed!")
                print("📄 Python Results:")
                print(result.stdout)
                return True
            else:
                print("❌ Python comparison failed!")
                print("Error:", result.stderr)
                return False
                
        except subprocess.TimeoutExpired:
            print("⏰ Python test timed out after 120 seconds")
            return False
        except Exception as e:
            print(f"❌ Error running Python test: {e}")
            return False
        finally:
            os.chdir(original_dir)
    else:
        print(f"❌ Python directory not found: {python_dir}")
        return False

def main():
    print("🏁 STDF Parser Performance Comparison")
    print("=" * 60)
    
    # Test C++ parser first
    cpp_results = test_cpp_parser()
    
    # Run Python comparison with dynamic C++ results
    if cpp_results:
        python_success = run_python_comparison(cpp_results)
    else:
        print("❌ Cannot run Python comparison without C++ results")
        python_success = False
    
    # Final summary
    if cpp_results:
        print(f"\n🎯 Final Summary:")
        print(f"=" * 40)
        print(f"C++ Parser:")
        print(f"  Records: {cpp_results['parsed_records']:,}")
        print(f"  Time: {cpp_results['parse_time']:.2f}s")
        print(f"  Speed: {cpp_results['records_per_second']:,.0f} records/sec")
        
        # Expected Python results (from previous fair comparison)
        python_records = 94943
        python_time = 40.50
        python_rps = python_records / python_time
        
        print(f"\nPython Parser (Fair Comparison):")
        print(f"  Records: {python_records:,}")
        print(f"  Time: {python_time:.2f}s") 
        print(f"  Speed: {python_rps:,.0f} records/sec")
        
        if cpp_results['parsed_records'] > 0:
            speed_ratio = cpp_results['records_per_second'] / python_rps
            time_ratio = python_time / cpp_results['parse_time']
            record_diff = abs(cpp_results['parsed_records'] - python_records)
            
            print(f"\n⚡ Performance Comparison:")
            print(f"  C++ is {speed_ratio:.1f}x faster than Python")
            print(f"  C++ takes {1/time_ratio:.2f}x less time")
            print(f"  Record count difference: {record_diff:,}")
            
            if record_diff < 1000:
                print(f"  ✅ Record counts are very close!")
            else:
                print(f"  ⚠️  Record count difference detected")

if __name__ == "__main__":
    main()