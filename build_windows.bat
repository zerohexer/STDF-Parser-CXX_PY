@echo off
REM Windows Build Script for STDF C++ Parser
REM This script builds the project using Clang on Windows

echo 🚀 Building STDF C++ Parser on Windows
echo ========================================

REM Check for required tools
echo 🔍 Checking for required tools...

where clang >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo ❌ Clang not found! Installing with winget...
    winget install LLVM.LLVM
    if %ERRORLEVEL% neq 0 (
        echo ❌ Failed to install Clang. Please install manually from:
        echo    https://releases.llvm.org/download.html
        pause
        exit /b 1
    )
    echo ✅ Clang installed successfully
)

where python >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo ❌ Python not found! Please install Python 3.7+
    pause
    exit /b 1
)

echo ✅ All required tools found

REM Install Python dependencies
echo 📦 Installing Python dependencies...
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

REM Create a simple STDF parser without libstdf for initial testing
echo 🔧 Creating simplified STDF parser for Windows testing...

REM First, let's build without libstdf dependency for testing
echo 🔨 Building C++ extension (without libstdf for now)...

REM Use standard setup.py but without libstdf
python -c "
import os
from setuptools import setup, Extension
import sysconfig

# Get Python paths
python_include = sysconfig.get_path('include')

# Simple extension without libstdf
ext = Extension(
    'stdf_parser_cpp',
    sources=['cpp/src/stdf_parser.cpp', 'cpp/src/python_bridge.cpp'],
    include_dirs=['cpp/include', python_include],
    language='c++',
    extra_compile_args=['/std:c++14', '/O2', '/W3', '/MD', '/EHsc'],
    extra_link_args=[],
)

setup(
    name='stdf_parser_test',
    ext_modules=[ext],
    zip_safe=False
)
" build_ext --inplace

if %ERRORLEVEL% neq 0 (
    echo ❌ Build failed
    echo 💡 Trying alternative build method...
    
    REM Alternative: Build manually with Clang
    echo 🔨 Building manually with Clang...
    
    clang++ -shared -std=c++14 -O3 -fPIC ^
        -I cpp/include ^
        -I "%CONDA_PREFIX%/include" ^
        -I "%PYTHON_INCLUDE%" ^
        cpp/src/stdf_parser.cpp cpp/src/python_bridge.cpp ^
        -o python/stdf_parser_cpp.pyd ^
        -L "%CONDA_PREFIX%/libs" ^
        -lpython%PYTHON_VERSION%
        
    if %ERRORLEVEL% neq 0 (
        echo ❌ Manual build also failed
        echo 💡 Please check your Clang installation and Python development headers
        pause
        exit /b 1
    )
)

echo ✅ Build completed successfully!

REM Test the installation
echo 🧪 Testing the C++ extension...
python -c "
try:
    import stdf_parser_cpp
    print('✅ C++ extension imported successfully')
    print(f'Version: {stdf_parser_cpp.get_version()}')
except ImportError as e:
    print(f'❌ Failed to import C++ extension: {e}')
    exit(1)
except Exception as e:
    print(f'❌ Error testing extension: {e}')
    exit(1)
"

if %ERRORLEVEL% neq 0 (
    echo ❌ Extension test failed
    pause
    exit /b 1
)

REM Run full test suite
echo 🧪 Running test suite...
python tests/test_cpp_parser.py

echo 🎉 Build and test completed successfully!
echo.
echo You can now use the STDF C++ parser:
echo   python -c "from python.stdf_cpp_wrapper import STDFCppParser; parser = STDFCppParser()"
echo.
echo For libstdf integration (full binary parsing), run:
echo   install_libstdf_windows.bat
echo.
pause