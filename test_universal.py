#!/usr/bin/env python3
"""
Universal test script for STDF C++ parser
Works on both Linux and Windows with automatic platform detection
"""

import sys
import os
import platform
import time

def setup_platform_libraries():
    """Setup libraries for the current platform"""
    system = platform.system().lower()
    
    if system == "linux":
        # Linux: Set LD_LIBRARY_PATH for shared libraries
        lib_dir = os.path.join(os.path.dirname(__file__), "cpp", "third_party", "lib")
        current_path = os.environ.get("LD_LIBRARY_PATH", "")
        if lib_dir not in current_path:
            os.environ["LD_LIBRARY_PATH"] = f"{lib_dir}:{current_path}" if current_path else lib_dir
        print(f"🐧 Linux: Set library path to {lib_dir}")
        
    elif system == "windows":
        # Windows: Static linking means no runtime dependencies needed!
        print("🪟 Windows: Using static linking (no DLL dependencies)")
        
        # Optional: Add DLL directory if DLLs are present (for hybrid approach)
        lib_dir = os.path.join(os.path.dirname(__file__), "cpp", "third_party", "lib")
        if os.path.exists(lib_dir) and hasattr(os, 'add_dll_directory'):
            try:
                os.add_dll_directory(lib_dir)
                print(f"📂 Added DLL directory: {lib_dir}")
            except:
                pass  # Static linking should work anyway
    else:
        print(f"⚠️  Unknown platform: {system}")

def test_parser():
    """Test the STDF parser"""
    
    # Setup platform-specific library loading
    setup_platform_libraries()
    
    try:
        # Import the C++ extension
        import stdf_parser_cpp
        print("✅ Extension loaded successfully")
        print(f"Version: {stdf_parser_cpp.get_version()}")
        
    except ImportError as e:
        print(f"❌ Failed to load extension: {e}")
        print("\n🔧 Troubleshooting:")
        print("1. Make sure you built the extension:")
        print("   python setup_universal.py build_ext --inplace")
        print("2. Check if libstdf library exists:")
        if platform.system() == "Windows":
            print("   - Windows: cpp/third_party/lib/libstdf.lib")
        else:
            print("   - Linux: cpp/third_party/lib/libstdf.so")
        return False
    
    # Test with STDF files
    stdf_dir = "STDF_Files"
    if not os.path.exists(stdf_dir):
        print(f"⚠️  STDF_Files directory not found")
        return True  # Extension loaded successfully, just no test files
    
    stdf_files = [f for f in os.listdir(stdf_dir) if f.endswith('.stdf')]
    if not stdf_files:
        print("⚠️  No .stdf files found in STDF_Files directory")
        return True
    
    # Test with first file
    test_file = os.path.join(stdf_dir, stdf_files[0])
    print(f"\n📁 Testing with: {os.path.basename(test_file)}")
    
    try:
        start_time = time.time()
        result = stdf_parser_cpp.parse_stdf_file(test_file)
        end_time = time.time()
        
        if isinstance(result, dict):
            records = result.get('records', [])
            total = result.get('total_records', 0)
            parsed = result.get('parsed_records', 0)
            
            print(f"✅ Successfully parsed {len(records)} records")
            print(f"  Total records in file: {total:,}")
            print(f"  Records parsed: {parsed:,}")
            print(f"  Parse time: {end_time - start_time:.2f} seconds")
            print(f"  Platform: {platform.system()} {platform.machine()}")
            
            # Show first few records
            if records:
                print("\n📋 Sample records:")
                for i, record in enumerate(records[:3]):
                    record_type = record.get('record_type', 'UNKNOWN')
                    test_num = record.get('test_num', 'N/A')
                    print(f"  {i+1}. {record_type} - Test #{test_num}")
            
            return True
        else:
            print(f"❌ Unexpected result type: {type(result)}")
            return False
            
    except Exception as e:
        print(f"❌ Error parsing file: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print(f"🚀 STDF C++ Parser Universal Test")
    print(f"Platform: {platform.system()} {platform.release()} {platform.machine()}")
    print(f"Python: {sys.version}")
    print("=" * 60)
    
    success = test_parser()
    
    print("=" * 60)
    if success:
        print("🎉 Test completed successfully!")
    else:
        print("❌ Test failed!")
        sys.exit(1)