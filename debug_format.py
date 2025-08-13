#!/usr/bin/env python3
"""
Debug script to see what format the C++ parser returns
"""

import sys
import os
import platform
import time

def setup_platform_libraries():
    """Setup libraries for the current platform"""
    system = platform.system().lower()
    
    if system == "linux":
        lib_dir = os.path.join(os.path.dirname(__file__), "cpp", "third_party", "lib")
        current_path = os.environ.get("LD_LIBRARY_PATH", "")
        if lib_dir not in current_path:
            os.environ["LD_LIBRARY_PATH"] = f"{lib_dir}:{current_path}" if current_path else lib_dir
        print(f"🐧 Linux: Set library path to {lib_dir}")
        
    elif system == "windows":
        print("🪟 Windows: Using static linking (no DLL dependencies)")
        lib_dir = os.path.join(os.path.dirname(__file__), "cpp", "third_party", "lib")
        if os.path.exists(lib_dir) and hasattr(os, 'add_dll_directory'):
            try:
                os.add_dll_directory(lib_dir)
                print(f"📂 Added DLL directory: {lib_dir}")
            except:
                pass

def debug_format():
    """Debug the format returned by C++ parser"""
    
    setup_platform_libraries()
    
    try:
        import stdf_parser_cpp
        print("✅ Extension loaded successfully")
        print(f"Version: {stdf_parser_cpp.get_version()}")
        
    except ImportError as e:
        print(f"❌ Failed to load extension: {e}")
        return False
    
    # Test with STDF files
    stdf_dir = "STDF_Files"
    if not os.path.exists(stdf_dir):
        print(f"⚠️  STDF_Files directory not found")
        return True
    
    stdf_files = [f for f in os.listdir(stdf_dir) if f.endswith('.stdf')]
    if not stdf_files:
        print("⚠️  No .stdf files found in STDF_Files directory")
        return True
    
    # Test with first file
    test_file = os.path.join(stdf_dir, stdf_files[0])
    print(f"\n📁 Testing with: {os.path.basename(test_file)}")
    
    try:
        print("🚀 Starting C++ STDF parsing...")
        result = stdf_parser_cpp.parse_stdf_file(test_file)
        
        print(f"\n🔍 Debug Information:")
        print(f"Type of result: {type(result)}")
        print(f"Length of result: {len(result) if hasattr(result, '__len__') else 'N/A'}")
        
        if hasattr(result, '__iter__'):
            print(f"\nFirst few items:")
            for i, item in enumerate(result):
                print(f"  Item {i}: Type={type(item)}")
                print(f"  Item {i}: Value={repr(item)}")
                if i >= 2:  # Show first 3 items
                    break
        else:
            print(f"Result value: {result}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🔍 STDF C++ Parser - Format Debug")
    print("=" * 50)
    
    success = debug_format()
    
    print("=" * 50)
    if success:
        print("✅ Debug completed!")
    else:
        print("❌ Debug failed!")
    
    sys.exit(0 if success else 1)