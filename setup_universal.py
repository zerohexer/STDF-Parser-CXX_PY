#!/usr/bin/env python3
"""
Universal setup.py for STDF C++ Parser
Works on both Linux and Windows with the same C++ code - no changes needed!
"""

from setuptools import setup, Extension
import os
import sys
import platform
import sysconfig

print(f"🔧 Setting up STDF Parser for {platform.system()}...")

# Platform detection
is_windows = platform.system() == "Windows"
is_linux = platform.system() == "Linux"

# Common configuration (same for all platforms)
common_sources = [
    'cpp/src/stdf_parser.cpp',
    'cpp/src/python_bridge.cpp'
]

common_include_dirs = [
    'cpp/include',
    'cpp/third_party/include',  # For libstdf headers
    sysconfig.get_path('include'),  # Python headers
]

# Platform-specific configuration
if is_windows:
    print("🪟 Configuring for Windows (static linking)...")
    
    # Windows: Static linking approach (no DLLs needed at runtime)
    extension_config = {
        'sources': common_sources,
        'include_dirs': common_include_dirs,
        'libraries': [
            'zlib',  # or 'z' depending on Windows zlib installation
        ],
        'extra_objects': [
            'cpp/third_party/lib/libstdf.lib',  # Static library on Windows
        ],
        'language': 'c++',
        'extra_compile_args': [
            '/std:c++14',           # C++14 standard
            '/O2',                  # Optimization
            '/W3',                  # Warning level
            '/MD',                  # Multi-threaded DLL runtime
            '/EHsc',                # Exception handling
            '/DWIN32',              # Windows defines
            '/DNDEBUG',
        ],
        'extra_link_args': [
            '/MACHINE:X64',         # 64-bit target
        ],
        'define_macros': [
            ('WIN32', None),
            ('_WINDOWS', None),
            ('NDEBUG', None),
            ('WIN32_LEAN_AND_MEAN', None),
            ('NOMINMAX', None),
        ],
    }
    
    # Alternative for MinGW on Windows
    if os.environ.get('CC', '').lower().find('gcc') != -1:
        print("🔧 Detected GCC/MinGW, using GCC flags...")
        extension_config.update({
            'extra_compile_args': [
                '-std=c++14',
                '-O3',
                '-Wall',
                '-Wextra',
                '-DWIN32',
                '-DNDEBUG',
            ],
            'extra_link_args': [
                '-static-libgcc',
                '-static-libstdc++',
            ],
        })

elif is_linux:
    print("🐧 Configuring for Linux (shared library)...")
    
    # Linux: Shared library approach (same as our working version)
    extension_config = {
        'sources': common_sources,
        'include_dirs': common_include_dirs,
        'library_dirs': [
            'cpp/third_party/lib',  # For libstdf shared library
            '/usr/local/lib',       # Standard path
        ],
        'libraries': [
            'stdf',  # libstdf shared library
            'z',     # zlib
        ],
        'language': 'c++',
        'extra_compile_args': [
            '-std=c++14',
            '-O3',
            '-Wall',
            '-Wextra',
        ],
        'extra_link_args': [
            '-std=c++14',
        ],
    }

else:
    print(f"❌ Unsupported platform: {platform.system()}")
    print("Supported platforms: Windows, Linux")
    sys.exit(1)

# Create the extension
stdf_parser_extension = Extension('stdf_parser_cpp', **extension_config)

# Universal setup configuration
setup(
    name='stdf-parser-cpp-universal',
    version='1.0.0',
    description=f'High-performance STDF parser using C++ for {platform.system()}',
    long_description='''
    A fast C++ implementation for parsing Standard Test Data Format (STDF) files 
    used in semiconductor testing. This universal version works on both Linux and 
    Windows with the same C++ source code - no modifications needed!
    
    Features:
    - Same C++ code works on Linux and Windows
    - Native performance on both platforms
    - Automatic platform detection and configuration
    - Linux: Shared library approach
    - Windows: Static library approach (no DLL dependencies)
    ''',
    author='STDF Parser Team',
    
    # C++ extension
    ext_modules=[stdf_parser_extension],
    
    # Python packages
    packages=['python'],
    package_dir={'python': 'python'},
    
    # Requirements
    python_requires='>=3.7',
    install_requires=[
        'numpy>=1.19.0',
    ],
    
    # Entry points
    entry_points={
        'console_scripts': [
            'stdf-parser=python.stdf_cpp_wrapper:main',
        ],
    },
    
    # Classifiers
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
        'Programming Language :: C++',
        'Topic :: Scientific/Engineering',
        'Operating System :: POSIX :: Linux',
        'Operating System :: Microsoft :: Windows',
    ],
    
    # Build options
    zip_safe=False,
    include_package_data=True,
)

print(f"✅ {platform.system()} configuration complete!")
print("\n📋 Next steps:")
if is_windows:
    print("1. Build libstdf as static library (.lib) for Windows")
    print("2. Place libstdf.lib in cpp/third_party/lib/")
    print("3. Run: python setup_universal.py build_ext --inplace")
    print("4. Test with: python test_parser.py")
    print("\n💡 Windows will use static linking - no DLL dependencies!")
elif is_linux:
    print("1. libstdf shared library already available")
    print("2. Run: python setup_universal.py build_ext --inplace") 
    print("3. Test with: ./run_test.sh")
    print("\n💡 Linux will use shared library with runtime path loading")