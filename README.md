# STDF Parser C++/Python

High-performance STDF (Standard Test Data Format) parser using C++ with Python integration. Provides 6-10x performance improvement over pure Python implementations for semiconductor test data processing.

## Features

- Native C++ parsing using libstdf library
- Cross-platform support (Linux/WSL and Windows)
- Static linking for Windows (zero external dependencies)
- Python extension interface for seamless integration
- Real-time processing of large STDF files (90K+ records in under 2 seconds)
- Production-ready with comprehensive error handling

## Architecture

The parser consists of three main components:

1. **libstdf**: Mature C library for STDF V4 binary parsing
2. **stdf_parser.cpp**: C++ wrapper providing high-level parsing interface
3. **python_bridge.cpp**: Python C extension API for Python integration

## Quick Start

### Windows (Pre-built Binary)

For Python 3.11 on Windows AMD64, use the included pre-built binary:

```bash
# Download the repository
git clone https://github.com/zerohexer/STDF-Parser-CXX_PY.git
cd STDF-Parser-CXX_PY

# Test with sample data
python test_universal.py
```

### Linux/WSL (Build from Source)

```bash
# Install dependencies (Ubuntu/Debian)
sudo apt-get update
sudo apt-get install build-essential python3-dev python3-setuptools

# Clone repository
git clone https://github.com/zerohexer/STDF-Parser-CXX_PY.git
cd STDF-Parser-CXX_PY

# Build the extension
LD_LIBRARY_PATH=$PWD/cpp/third_party/lib:$LD_LIBRARY_PATH python3 setup.py build_ext --inplace

OR

python3 setup.py build_ext --inplace

# Test
LD_LIBRARY_PATH=$PWD/cpp/third_party/lib:$LD_LIBRARY_PATH python3 test_parser.py

OR

LD_LIBRARY_PATH=$PWD/cpp/third_party/lib:$LD_LIBRARY_PATH python3 test_universal.py

```

## Building from Source

### Windows Build Requirements

- Python 3.7+ with development headers
- MSYS2 with MinGW-w64 toolchain
- Git

### Windows Build Process

1. Install MSYS2 and MinGW:
```bash
# Install MSYS2 from https://www.msys2.org/
# Add to PATH: C:\msys64\ucrt64\bin
```

2. Build the extension:
```bash
# In PowerShell/CMD
cd STDF-Parser-CXX_PY
python -m pip install setuptools
python setup_windows_mingw.py build_ext --inplace --compiler=mingw32
```

3. Test the build:
```bash
python test_universal.py
```

### Linux/WSL Build Process

The Linux build uses the pre-compiled libstdf libraries included in the repository:

```bash
# Build command
LD_LIBRARY_PATH=$PWD/cpp/third_party/lib:$LD_LIBRARY_PATH python3 setup_universal.py build_ext --inplace

# The build process:
# 1. Compiles cpp/src/stdf_parser.cpp (main parsing logic)
# 2. Compiles cpp/src/python_bridge.cpp (Python interface)
# 3. Links against cpp/third_party/lib/libstdf.a (static library)
# 4. Creates stdf_parser_cpp.so extension module
```

## Usage

### Basic Usage

```python
import stdf_parser_cpp

# Parse STDF file
records = stdf_parser_cpp.parse_stdf_file("test_file.stdf")

# Get parser version
version = stdf_parser_cpp.get_version()
print(f"Parser version: {version}")

# Process records
for record in records:
    print(f"Record type: {record['type']}")
    print(f"Fields: {record['fields']}")
```

### Performance Comparison

```python
import time
import stdf_parser_cpp

# Time the parsing
start_time = time.time()
records = stdf_parser_cpp.parse_stdf_file("large_file.stdf")
parse_time = time.time() - start_time

print(f"Parsed {len(records)} records in {parse_time:.2f} seconds")
```

## Technical Details

### libstdf Integration

The parser uses libstdf 0.4 for low-level STDF parsing:

- **cpp/third_party/**: Linux libstdf build (shared libraries)
- **cpp/third_party_windows/**: Windows libstdf build (static libraries)
- **libstdf-0.4/**: Complete libstdf source code

### C++ Components

**stdf_parser.cpp** - Main parsing engine:
- `STDFParser::parse_file()`: Main entry point for file parsing
- `STDFParser::parse_record()`: Individual record parsing
- `STDFParser::parse_ptr_record()`: Parametric Test Record parsing
- `STDFParser::parse_mpr_record()`: Multiple-Result Parametric parsing
- `STDFParser::parse_ftr_record()`: Functional Test Record parsing

**python_bridge.cpp** - Python interface:
- `parse_stdf_file()`: Python-callable parsing function
- `get_version()`: Version information
- Python C API integration with proper error handling

### Supported Record Types

- **PTR**: Parametric Test Record
- **MPR**: Multiple-Result Parametric Record
- **FTR**: Functional Test Record
- **HBR**: Hardware Bin Record
- **SBR**: Software Bin Record
- **PRR**: Part Result Record
- **MIR**: Master Information Record

## File Structure

```
STDF-Parser-CXX_PY/
├── cpp/
│   ├── include/
│   │   ├── stdf_parser.h          # Main parser class definition
│   │   └── stdf_binary_parser.h   # Binary parsing utilities
│   ├── src/
│   │   ├── stdf_parser.cpp        # Core parsing implementation
│   │   └── python_bridge.cpp      # Python C extension
│   ├── third_party/              # Linux libstdf build
│   └── third_party_windows/      # Windows libstdf build
├── libstdf-0.4/                  # libstdf source code
├── STDF_Files/                   # Sample STDF test files
├── setup_universal.py            # Linux/WSL build script
├── setup_windows_mingw.py        # Windows MinGW build script
├── test_universal.py             # Test and benchmark script
└── stdf_parser_cpp.cp311-win_amd64.pyd  # Pre-built Windows binary
```

## libstdf Build Details

### Linux Build (Already Included)

The repository includes pre-built libstdf for Linux:

```bash
# Original build process (already done):
cd libstdf-0.4
./configure --prefix=$PWD/../cpp/third_party --enable-static --enable-shared
make && make install
```

### Windows Build (Already Included)

The repository includes pre-built libstdf for Windows with correct endianness:

```bash
# Original cross-compilation process (already done):
cd libstdf-0.4
./configure --host=x86_64-w64-mingw32 --prefix=$PWD/../cpp/third_party_windows --enable-static --disable-shared --enable-endian=little
make && make install
```

## Troubleshooting

### Windows Issues

**Error: "Cannot find libstdf.dll"**
- Solution: Use the MinGW build process which creates statically linked binaries

**Error: "Unknown compiler option"**
- Solution: Ensure MinGW is in PATH and use `--compiler=mingw32` flag

### Linux Issues

**Error: "libstdf.so: cannot open shared object file"**
- Solution: Set LD_LIBRARY_PATH before running:
```bash
LD_LIBRARY_PATH=$PWD/cpp/third_party/lib:$LD_LIBRARY_PATH python3 your_script.py
```

**Error: Missing development headers**
- Solution: Install python3-dev package:
```bash
sudo apt-get install python3-dev
```

### Troubleshooting records , records type and fields
```bash

Run after build setup.py / setup_windows_mingw.py
python test_universal.py (test if build succeed , and library is in USED)
python debug_record_type.py  (record type and record count comparison accuracy)
python compare_cpp_vs_pystdf.py (compare record fields / record type comparison)
python test_field_extraction.py (Extract each fields from record type using cpp parser)
```

## Performance Notes

- **Windows**: Static linking provides best performance (no DLL overhead)
- **Linux**: Shared library linking is standard and performs well
- **Memory**: Parser uses streaming approach for large files
- **Threading**: Single-threaded design optimized for sequential processing

## License

This project uses libstdf (GPL license) for STDF parsing functionality. See libstdf-0.4/COPYING for license details.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make changes to C++ source files in cpp/src/
4. Test on both Linux and Windows
5. Submit a pull request

## Version History

- **v1.0.0**: Initial release with cross-platform support
  - Native C++ parsing with libstdf integration
  - Windows static linking with MinGW
  - Linux shared library support
  - Production-ready performance (90K+ records/second)

## Clickhouse integration and Debugging

```bash
Pushing to clickhouse
python extract_all_measurements_plus_clickhouse_connect.py --stdf-file "PATH/File Directory" --push-clickhouse --ch-host <IP> --ch-port 9000 --ch-database <DB/namespace> --ch-user <name> --ch-password <password>

Example:
python extract_all_measurements_plus_clickhouse_connect.py --stdf-file "STDF_Files/OS_KEWGBCLD1U_BE_HRG3301Y.06_KEWGBCLD1U__Prod_TPP202_03_Agilent_93000MT9510_25C_5264_2_20240903225946.stdf" --push-clickhouse --ch-host 127.0.0.1 --ch-port 9000 --ch-database iswc --ch-user admin --ch-password admin

Debugging verify ID and segmentation for deduplication:
python verify_ids_and_segments.py --stdf-file "PATH/File Directory" --push-clickhouse --ch-host <IP> --ch-port 9000 --ch-database <DB/namespace> --ch-user <name> --ch-password <password>


```

