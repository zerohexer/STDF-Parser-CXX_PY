#!/usr/bin/env python3
"""
Universal libstdf builder - detects platform and builds accordingly
One script that builds the right library for your platform!
"""

import os
import sys
import platform
import subprocess
import shutil
import tempfile
import urllib.request
import tarfile

def detect_platform():
    """Detect platform and return build configuration"""
    system = platform.system().lower()
    arch = platform.machine().lower()
    
    config = {
        'system': system,
        'arch': arch,
        'is_windows': system == 'windows',
        'is_linux': system == 'linux',
        'is_64bit': '64' in arch or 'x86_64' in arch or 'amd64' in arch
    }
    
    print(f"🔍 Detected: {system} {arch} ({'64-bit' if config['is_64bit'] else '32-bit'})")
    return config

def download_libstdf_source():
    """Download libstdf source if not present"""
    if os.path.exists('libstdf-0.4'):
        print("✅ libstdf source already exists")
        return 'libstdf-0.4'
    
    print("📥 Downloading libstdf source...")
    url = "https://freestdf.sourceforge.net/libstdf-0.4.tar.bz2"
    
    try:
        with tempfile.NamedTemporaryFile(suffix='.tar.bz2', delete=False) as tmp:
            urllib.request.urlretrieve(url, tmp.name)
            
            # Extract
            with tarfile.open(tmp.name, 'r:bz2') as tar:
                tar.extractall('.')
            
            os.unlink(tmp.name)
            print("✅ Downloaded and extracted libstdf source")
            return 'libstdf-0.4'
            
    except Exception as e:
        print(f"❌ Failed to download: {e}")
        if os.path.exists('libstdf-0.4.tar.bz2'):
            print("🔧 Found local tarball, extracting...")
            with tarfile.open('libstdf-0.4.tar.bz2', 'r:bz2') as tar:
                tar.extractall('.')
            return 'libstdf-0.4'
        return None

def build_linux(source_dir):
    """Build libstdf for Linux (what we already did)"""
    print("🐧 Building libstdf for Linux...")
    
    os.chdir(source_dir)
    
    # Configure and build
    commands = [
        ['./configure', '--prefix=' + os.path.abspath('../cpp/third_party')],
        ['make', 'clean'],
        ['make', '-j4'],
        ['make', 'install']
    ]
    
    for cmd in commands:
        print(f"Running: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"❌ Command failed: {' '.join(cmd)}")
            print(f"Error: {result.stderr}")
            return False
    
    print("✅ Linux build completed!")
    return True

def build_windows(source_dir):
    """Build libstdf for Windows"""
    print("🪟 Building libstdf for Windows...")
    
    # Create Windows-compatible Makefile
    windows_makefile = """
# Simple Windows Makefile for libstdf
CC = gcc
CXX = g++
AR = ar
CFLAGS = -O2 -Wall -DWIN32 -D_WINDOWS -DNDEBUG
CXXFLAGS = $(CFLAGS) -std=c++14

# Source files
SOURCES = src/libstdf.c src/dtc.c src/rec.c
OBJECTS = $(SOURCES:.c=.o)

# Target
TARGET = libstdf.a

all: $(TARGET)

$(TARGET): $(OBJECTS)
\t$(AR) rcs $@ $^

%.o: %.c
\t$(CC) $(CFLAGS) -Iinclude -c $< -o $@

clean:
\trm -f $(OBJECTS) $(TARGET)

install: $(TARGET)
\tmkdir -p ../cpp/third_party/lib
\tmkdir -p ../cpp/third_party/include
\tcp $(TARGET) ../cpp/third_party/lib/
\tcp include/*.h ../cpp/third_party/include/

.PHONY: all clean install
"""
    
    os.chdir(source_dir)
    
    # Write Windows Makefile
    with open('Makefile.windows', 'w') as f:
        f.write(windows_makefile)
    
    # Build commands for Windows
    commands = [
        ['make', '-f', 'Makefile.windows', 'clean'],
        ['make', '-f', 'Makefile.windows', '-j4'],
        ['make', '-f', 'Makefile.windows', 'install']
    ]
    
    for cmd in commands:
        print(f"Running: {' '.join(cmd)}")
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"❌ Command failed: {' '.join(cmd)}")
            print(f"Error: {result.stderr}")
            return False
    
    # Convert .a to .lib for MSVC compatibility
    lib_dir = '../cpp/third_party/lib'
    if os.path.exists(f'{lib_dir}/libstdf.a'):
        shutil.copy(f'{lib_dir}/libstdf.a', f'{lib_dir}/libstdf.lib')
        print("✅ Created libstdf.lib for MSVC compatibility")
    
    print("✅ Windows build completed!")
    return True

def main():
    """Main build function"""
    print("🚀 Universal libstdf Builder")
    print("=" * 50)
    
    # Detect platform
    config = detect_platform()
    
    # Download source if needed
    source_dir = download_libstdf_source()
    if not source_dir:
        print("❌ Could not obtain libstdf source")
        return False
    
    # Save current directory
    original_dir = os.getcwd()
    
    try:
        # Build for detected platform
        if config['is_linux']:
            success = build_linux(source_dir)
        elif config['is_windows']:
            success = build_windows(source_dir)
        else:
            print(f"❌ Unsupported platform: {config['system']}")
            return False
        
        # Return to original directory
        os.chdir(original_dir)
        
        if success:
            print("\n🎉 Build completed successfully!")
            print(f"📦 Library built for {config['system']}")
            
            # Show what was built
            lib_dir = "cpp/third_party/lib"
            if os.path.exists(lib_dir):
                print(f"\n📁 Built libraries in {lib_dir}:")
                for file in os.listdir(lib_dir):
                    if file.startswith('libstdf'):
                        size = os.path.getsize(os.path.join(lib_dir, file))
                        print(f"  - {file} ({size:,} bytes)")
            
            print("\n✅ Ready to build Python extension:")
            print("   python setup_universal.py build_ext --inplace")
            
            return True
        else:
            print("❌ Build failed!")
            return False
            
    except Exception as e:
        os.chdir(original_dir)
        print(f"❌ Build error: {e}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)