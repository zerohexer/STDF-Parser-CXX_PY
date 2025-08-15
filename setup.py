#!/usr/bin/env python3

from setuptools import setup, Extension
import os
import sys
import sysconfig

# Define the extension module
stdf_parser_extension = Extension(
    'stdf_parser_cpp',
    sources=[
        'cpp/src/stdf_parser.cpp',
        'cpp/src/dynamic_field_extractor.cpp',
        'cpp/src/ultra_fast_processor.cpp',
        'cpp/src/python_bridge.cpp'
    ],
    include_dirs=[
        'cpp/include',
        'cpp/third_party/include',  # For libstdf headers
        sysconfig.get_path('include'),  # Python headers
        '/usr/local/include',  # Standard include path
    ],
    library_dirs=[
        'cpp/third_party/lib',  # For libstdf library when we add it
        '/usr/local/lib',  # Standard library path
    ],
    libraries=[
        'stdf',  # libstdf library
        'z',     # zlib (required by libstdf)
    ],
    language='c++',
    extra_compile_args=[
        '-std=c++17',  # Updated for X-Macros
        '-O3',  # Optimization
        '-Wall',
        '-Wextra',
    ],
    extra_link_args=[
        '-std=c++17',
    ],
)

setup(
    name='stdf-parser-cpp',
    version='1.0.0',
    description='High-performance STDF parser using C++',
    long_description='A fast C++ implementation for parsing Standard Test Data Format (STDF) files used in semiconductor testing.',
    author='STDF Parser Team',
    author_email='info@stdfparser.com',
    url='https://github.com/your-repo/stdf-parser-cpp',
    
    # Python packages
    packages=['python'],
    package_dir={'python': 'python'},
    
    # C++ extension
    ext_modules=[stdf_parser_extension],
    
    # Requirements
    python_requires='>=3.7',
    install_requires=[
        'numpy>=1.19.0',
        'clickhouse-driver>=0.2.0',
        'fastapi>=0.68.0',
        'uvicorn>=0.15.0',
        'python-multipart>=0.0.5',
    ],
    
    # Development requirements
    extras_require={
        'dev': [
            'pytest>=6.0',
            'pytest-cov>=2.0',
            'black>=21.0',
            'flake8>=3.8',
        ],
    },
    
    # Entry points
    entry_points={
        'console_scripts': [
            'stdf-parser=python.cli:main',
        ],
    },
    
    # Classifiers
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: C++',
        'Topic :: Scientific/Engineering',
        'Topic :: Software Development :: Libraries',
    ],
    
    # Build options
    zip_safe=False,
    include_package_data=True,
)

