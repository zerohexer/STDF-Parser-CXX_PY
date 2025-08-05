#!/bin/bash

# STDF C++ Parser - libstdf Installation Script
# This script downloads and installs libstdf for the STDF parser

set -e  # Exit on any error

echo "🚀 Installing libstdf for STDF C++ Parser"
echo "============================================"

# Configuration
LIBSTDF_VERSION="0.4"
LIBSTDF_URL="https://sourceforge.net/projects/freestdf/files/libstdf/libstdf-${LIBSTDF_VERSION}.tar.bz2"
LIBSTDF_DIR="libstdf-${LIBSTDF_VERSION}"
THIRD_PARTY_DIR="cpp/third_party"

# Create third_party directories
mkdir -p ${THIRD_PARTY_DIR}/include
mkdir -p ${THIRD_PARTY_DIR}/lib

# Download libstdf if not already present
if [ ! -f "${LIBSTDF_DIR}.tar.bz2" ]; then
    echo "📥 Downloading libstdf ${LIBSTDF_VERSION}..."
    wget -O "${LIBSTDF_DIR}.tar.bz2" "${LIBSTDF_URL}"
else
    echo "✅ libstdf archive already present"
fi

# Extract if not already extracted
if [ ! -d "${LIBSTDF_DIR}" ]; then
    echo "📦 Extracting libstdf..."
    tar -xjf "${LIBSTDF_DIR}.tar.bz2"
else
    echo "✅ libstdf already extracted"
fi

# Build libstdf
echo "🔨 Building libstdf..."
cd "${LIBSTDF_DIR}"

# Configure with prefix to current directory
./configure --prefix="$(pwd)/../${THIRD_PARTY_DIR}"

# Build
make clean || true  # Clean any previous build
make

# Install to third_party
make install

cd ..

# Verify installation
echo "✅ Verifying libstdf installation..."
if [ -f "${THIRD_PARTY_DIR}/include/libstdf.h" ]; then
    echo "✅ libstdf headers installed"
else
    echo "❌ libstdf headers not found"
    exit 1
fi

if [ -f "${THIRD_PARTY_DIR}/lib/libstdf.a" ] || [ -f "${THIRD_PARTY_DIR}/lib/libstdf.so" ]; then
    echo "✅ libstdf library installed"
else
    echo "❌ libstdf library not found"
    exit 1
fi

# Update setup.py to enable libstdf
echo "🔧 Updating setup.py to enable libstdf..."
sed -i 's/# "stdf",  # Uncomment when libstdf is available/"stdf",  # libstdf library/g' setup.py || true

# Update CMakeLists.txt to enable libstdf
echo "🔧 Updating CMakeLists.txt to enable libstdf..."
sed -i 's/# stdf  # Uncomment when libstdf is available/stdf  # libstdf library/g' cpp/CMakeLists.txt || true

# Update C++ source to enable libstdf
echo "🔧 Updating C++ source to enable libstdf..."
sed -i 's|// #include <libstdf.h>|#include <libstdf.h>|g' cpp/src/stdf_parser.cpp || true

echo "🎉 libstdf installation completed!"
echo ""
echo "Next steps:"
echo "1. Build the C++ extension:"
echo "   python setup.py build_ext --inplace"
echo ""
echo "2. Test the installation:"
echo "   python tests/test_cpp_parser.py"
echo ""
echo "3. Run performance benchmark:"
echo "   python -c \"from python.stdf_cpp_wrapper import test_cpp_parser; test_cpp_parser()\""

# Cleanup
echo "🧹 Cleaning up temporary files..."
rm -rf "${LIBSTDF_DIR}"
rm -f "${LIBSTDF_DIR}.tar.bz2"

echo "✅ Installation complete!"