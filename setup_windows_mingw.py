#!/usr/bin/env python3
"""
Windows native build using MinGW from MSYS2
Forces gcc.exe instead of cl.exe to handle Linux-style libstdf headers
"""

from setuptools import setup, Extension
import os
import sys
import platform

print("🔧 Setting up STDF Parser for Windows with MinGW...")

# Force MinGW compiler on Windows
if platform.system() == "Windows":
    print("🪟 Windows detected - forcing MinGW compiler...")
    
    # Set environment to use MinGW
    os.environ['CC'] = 'gcc'
    os.environ['CXX'] = 'g++'
    
    # Windows configuration with MinGW
    extension_config = {
        'sources': [
            'cpp/src/python_bridge.cpp',
            'cpp/src/stdf_parser.cpp',
            'cpp/src/dynamic_field_extractor.cpp',
            'cpp/src/ultra_fast_processor.cpp'
        ],
        'include_dirs': [
            'cpp/include',
            'cpp/third_party_windows/include',  # Use Windows libstdf headers
        ],
        'extra_objects': [
            'cpp/third_party_windows/lib/libstdf.a',  # Use Windows static library
        ],
        'language': 'c++',
        'extra_compile_args': [
            '-std=c++17',  # Updated for X-Macros
            '-O3',
            '-DWIN32',
            '-DNDEBUG',
        ],
        'extra_link_args': [
            '-static-libgcc',
            '-static-libstdc++',
            '-static',  # Static link EVERYTHING including MSVC runtime
        ],
    }
    
    print("✅ Using MinGW compiler with Windows libstdf")
    
else:
    print("❌ This script is designed for Windows only!")
    sys.exit(1)

# Create extension
stdf_extension = Extension('stdf_parser_cpp', **extension_config)

setup(
    name='stdf-parser-cpp-windows-mingw',
    version='1.0.0',
    description='Native Windows STDF parser using MinGW',
    ext_modules=[stdf_extension],
    zip_safe=False,
)

print("🎉 Windows MinGW build complete!")