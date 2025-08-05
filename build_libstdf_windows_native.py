#!/usr/bin/env python3
"""
Native Windows libstdf builder - no make required!
Uses direct compiler calls instead of make/autotools
"""

import os
import sys
import platform
import subprocess
import shutil
import glob

def find_compiler():
    """Find available C/C++ compiler on Windows"""
    compilers = [
        # Try GCC/MinGW first (most compatible with libstdf)
        {'name': 'gcc', 'cc': 'gcc', 'cxx': 'g++', 'ar': 'ar'},
        {'name': 'clang', 'cc': 'clang', 'cxx': 'clang++', 'ar': 'llvm-ar'},
        # MSVC (requires more setup)
        {'name': 'msvc', 'cc': 'cl', 'cxx': 'cl', 'ar': 'lib'},
    ]
    
    for compiler in compilers:
        if shutil.which(compiler['cc']):
            print(f"✅ Found {compiler['name']}: {compiler['cc']}")
            return compiler
    
    print("❌ No suitable compiler found!")
    print("Install one of these:")
    print("- MinGW: https://www.mingw-w64.org/")
    print("- LLVM/Clang: https://releases.llvm.org/")
    print("- Visual Studio Build Tools")
    return None

def compile_libstdf_direct(source_dir, compiler):
    """Compile libstdf directly without make"""
    print(f"🔧 Compiling libstdf with {compiler['name']}...")
    
    os.chdir(source_dir)
    
    # Find all C source files
    src_files = []
    for pattern in ['src/*.c']:
        src_files.extend(glob.glob(pattern))
    
    if not src_files:
        print("❌ No source files found!")
        return False
    
    print(f"📁 Found {len(src_files)} source files")
    
    # Compilation flags
    if compiler['name'] == 'msvc':
        cflags = [
            '/O2',           # Optimization
            '/W3',           # Warning level
            '/MD',           # Runtime library
            '/DWIN32',       # Windows defines
            '/D_WINDOWS',
            '/DNDEBUG',
            '/Iinclude',     # Include directory
            '/c',            # Compile only
        ]
        ar_flags = ['/OUT:libstdf.lib']
    else:  # GCC/Clang
        cflags = [
            '-O2',           # Optimization
            '-Wall',         # Warnings
            '-DWIN32',       # Windows defines
            '-D_WINDOWS',
            '-DNDEBUG',
            '-Iinclude',     # Include directory
            '-c',            # Compile only
        ]
        ar_flags = ['rcs', 'libstdf.lib']  # Use .lib extension for Windows compatibility
    
    # Compile each source file
    obj_files = []
    for src_file in src_files:
        obj_file = src_file.replace('.c', '.obj' if compiler['name'] == 'msvc' else '.o')
        obj_files.append(obj_file)
        
        cmd = [compiler['cc']] + cflags + [src_file, '/Fo' + obj_file if compiler['name'] == 'msvc' else '-o', obj_file]
        if compiler['name'] != 'msvc':
            cmd = [compiler['cc']] + cflags + ['-o', obj_file, src_file]
        
        print(f"Compiling {src_file}...")
        result = subprocess.run(cmd, capture_output=True, text=True, shell=True)
        if result.returncode != 0:
            print(f"❌ Failed to compile {src_file}")
            print(f"Command: {' '.join(cmd)}")
            print(f"Error: {result.stderr}")
            return False
    
    # Create static library
    print("📦 Creating static library...")
    if compiler['name'] == 'msvc':
        ar_cmd = [compiler['ar']] + ar_flags + obj_files
    else:
        ar_cmd = [compiler['ar']] + ar_flags + ['libstdf.lib'] + obj_files
    
    result = subprocess.run(ar_cmd, capture_output=True, text=True, shell=True)
    if result.returncode != 0:
        print(f"❌ Failed to create library")
        print(f"Command: {' '.join(ar_cmd)}")
        print(f"Error: {result.stderr}")
        return False
    
    print("✅ Static library created: libstdf.lib")
    return True

def install_library(source_dir):
    """Install library and headers"""
    print("📦 Installing library and headers...")
    
    # Create target directories
    lib_dir = os.path.abspath(os.path.join('..', 'cpp', 'third_party', 'lib'))
    include_dir = os.path.abspath(os.path.join('..', 'cpp', 'third_party', 'include'))
    
    os.makedirs(lib_dir, exist_ok=True)
    os.makedirs(include_dir, exist_ok=True)
    
    # Copy library
    lib_file = os.path.join(source_dir, 'libstdf.lib')
    if os.path.exists(lib_file):
        shutil.copy2(lib_file, lib_dir)
        print(f"✅ Copied libstdf.lib to {lib_dir}")
    else:
        print(f"❌ Library file not found: {lib_file}")
        return False
    
    # Copy headers
    include_src = os.path.join(source_dir, 'include')
    if os.path.exists(include_src):
        for header in glob.glob(os.path.join(include_src, '*.h')):
            shutil.copy2(header, include_dir)
        print(f"✅ Copied headers to {include_dir}")
    else:
        print(f"❌ Include directory not found: {include_src}")
        return False
    
    return True

def main():
    """Main build function for Windows"""
    print("🪟 Native Windows libstdf Builder")
    print("=" * 40)
    
    # Check if source exists
    source_dir = 'libstdf-0.4'
    if not os.path.exists(source_dir):
        print(f"❌ Source directory not found: {source_dir}")
        print("Please extract libstdf-0.4.tar.bz2 first")
        return False
    
    # Find compiler
    compiler = find_compiler()
    if not compiler:
        return False
    
    # Save current directory
    original_dir = os.getcwd()
    
    try:
        # Compile
        if not compile_libstdf_direct(source_dir, compiler):
            return False
        
        # Install
        os.chdir(original_dir)
        if not install_library(source_dir):
            return False
        
        print("\n🎉 Windows build completed successfully!")
        
        # Show results
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
        
    except Exception as e:
        os.chdir(original_dir)
        print(f"❌ Build error: {e}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)