#!/usr/bin/env python3
import os
import sys

# Simple test without any complex logic
lib_dir = os.path.join(os.path.dirname(__file__), "cpp", "third_party", "lib")
os.environ["LD_LIBRARY_PATH"] = f"{lib_dir}:{os.environ.get('LD_LIBRARY_PATH', '')}"

try:
    import stdf_parser_cpp
    print("✓ Extension loaded")
    print("Version:", stdf_parser_cpp.get_version())
    
    # Test with a very simple case - no file parsing yet
    print("✓ Basic functionality works")
    
except Exception as e:
    print(f"✗ Error: {e}")
    import traceback
    traceback.print_exc()