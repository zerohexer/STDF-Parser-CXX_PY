# PowerShell Build Script for STDF C++ Parser on Windows
# This script builds the project using Clang

Write-Host "🚀 Building STDF C++ Parser on Windows (PowerShell)" -ForegroundColor Green
Write-Host "====================================================" -ForegroundColor Green

# Function to check if command exists
function Test-CommandExists {
    param($Command)
    $null = Get-Command $Command -ErrorAction SilentlyContinue
    return $?
}

# Check for required tools
Write-Host "🔍 Checking for required tools..." -ForegroundColor Yellow

if (-not (Test-CommandExists "clang")) {
    Write-Host "❌ Clang not found! Attempting to install with winget..." -ForegroundColor Red
    try {
        winget install LLVM.LLVM --accept-source-agreements --accept-package-agreements
        Write-Host "✅ Clang installed successfully" -ForegroundColor Green
        
        # Refresh PATH
        $env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path", "User")
    }
    catch {
        Write-Host "❌ Failed to install Clang. Please install manually from:" -ForegroundColor Red
        Write-Host "   https://releases.llvm.org/download.html" -ForegroundColor Red
        Read-Host "Press Enter to exit"
        exit 1
    }
}

if (-not (Test-CommandExists "python")) {
    Write-Host "❌ Python not found! Please install Python 3.7+" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host "✅ All required tools found" -ForegroundColor Green

# Get Python information
$pythonVersion = python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
$pythonPath = python -c "import sys; print(sys.executable)"
$pythonInclude = python -c "import sysconfig; print(sysconfig.get_path('include'))"

Write-Host "Python Version: $pythonVersion" -ForegroundColor Cyan
Write-Host "Python Path: $pythonPath" -ForegroundColor Cyan
Write-Host "Python Include: $pythonInclude" -ForegroundColor Cyan

# Install Python dependencies
Write-Host "📦 Installing Python dependencies..." -ForegroundColor Yellow
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Failed to install Python dependencies" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

# Build C++ extension
Write-Host "🔨 Building C++ extension..." -ForegroundColor Yellow

# Create a temporary setup script for building
$setupScript = @"
from setuptools import setup, Extension
import sysconfig
import os

# Get Python paths
python_include = sysconfig.get_path('include')
python_library_dir = sysconfig.get_config_var('LIBDIR')
python_library = sysconfig.get_config_var('LIBRARY')

print(f'Python include: {python_include}')
print(f'Python library dir: {python_library_dir}')
print(f'Python library: {python_library}')

# Define extension
ext = Extension(
    'stdf_parser_cpp',
    sources=[
        'cpp/src/stdf_parser.cpp',
        'cpp/src/python_bridge.cpp'
    ],
    include_dirs=[
        'cpp/include',
        python_include,
    ],
    library_dirs=[
        python_library_dir or '',
    ],
    libraries=[
        # Python library is automatically linked by setuptools
    ],
    language='c++',
    extra_compile_args=[
        '/std:c++14',  # C++ standard
        '/O2',         # Optimization
        '/W3',         # Warning level
        '/MD',         # Runtime library
        '/EHsc',       # Exception handling
    ],
    extra_link_args=[
        '/MACHINE:X64',
    ],
    define_macros=[
        ('WIN32', None),
        ('_WINDOWS', None),
        ('NDEBUG', None),
    ],
)

setup(
    name='stdf_parser_windows_test',
    ext_modules=[ext],
    zip_safe=False
)
"@

# Write temporary setup script
$setupScript | Out-File -FilePath "setup_temp.py" -Encoding UTF8

# Build the extension
python setup_temp.py build_ext --inplace

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Build failed with setuptools" -ForegroundColor Red
    Write-Host "💡 Trying manual build with Clang..." -ForegroundColor Yellow
    
    # Manual build attempt
    $clangCmd = @(
        "clang++",
        "-shared",
        "-std=c++14",
        "-O3",
        "-I", "cpp/include",
        "-I", $pythonInclude,
        "cpp/src/stdf_parser.cpp",
        "cpp/src/python_bridge.cpp",
        "-o", "python/stdf_parser_cpp.pyd"
    )
    
    Write-Host "Running: $($clangCmd -join ' ')" -ForegroundColor Cyan
    & $clangCmd[0] $clangCmd[1..($clangCmd.Length-1)]
    
    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ Manual build also failed" -ForegroundColor Red
        Write-Host "💡 Please check your Clang installation and Python development headers" -ForegroundColor Yellow
        Read-Host "Press Enter to exit"
        exit 1
    }
}

# Clean up temporary setup script
Remove-Item "setup_temp.py" -ErrorAction SilentlyContinue

Write-Host "✅ Build completed successfully!" -ForegroundColor Green

# Test the installation
Write-Host "🧪 Testing the C++ extension..." -ForegroundColor Yellow

python -c @"
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
"@

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Extension test failed" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

# Run test suite
Write-Host "🧪 Running test suite..." -ForegroundColor Yellow
python tests/test_cpp_parser.py

Write-Host "🎉 Build and test completed successfully!" -ForegroundColor Green
Write-Host ""
Write-Host "You can now use the STDF C++ parser:" -ForegroundColor Cyan
Write-Host "  python -c `"from python.stdf_cpp_wrapper import STDFCppParser; parser = STDFCppParser()`"" -ForegroundColor Cyan
Write-Host ""
Write-Host "For libstdf integration (full binary parsing), run:" -ForegroundColor Cyan
Write-Host "  .\install_libstdf_windows.bat" -ForegroundColor Cyan
Write-Host ""

Read-Host "Press Enter to exit"