cmake_minimum_required(VERSION 3.12)
project(STDFParserCpp)

# Set C++ standard
set(CMAKE_CXX_STANDARD 14)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Compiler flags
set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -Wall -Wextra -O3")

# Find Python
find_package(Python3 COMPONENTS Interpreter Development REQUIRED)

# Include directories
include_directories(
    ${CMAKE_CURRENT_SOURCE_DIR}/include
    ${CMAKE_CURRENT_SOURCE_DIR}/third_party/include
    ${Python3_INCLUDE_DIRS}
)

# Library directories
link_directories(
    ${CMAKE_CURRENT_SOURCE_DIR}/third_party/lib
)

# Source files
set(SOURCES
    src/stdf_parser.cpp
)

# Create static library for the STDF parser core
add_library(stdf_parser_core STATIC ${SOURCES})

# Python extension module
add_library(stdf_parser_cpp MODULE
    src/python_bridge.cpp
    ${SOURCES}
)

# Link libraries
target_link_libraries(stdf_parser_cpp 
    ${Python3_LIBRARIES}
    # stdf  # Uncomment when libstdf is available
)

# Set module properties
set_target_properties(stdf_parser_cpp PROPERTIES
    PREFIX ""
    SUFFIX ".so"
    LIBRARY_OUTPUT_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}/../python
)

# Installation
install(TARGETS stdf_parser_cpp 
        LIBRARY DESTINATION ${CMAKE_CURRENT_SOURCE_DIR}/../python)

# Optional: Build standalone executable for testing
add_executable(stdf_test
    src/stdf_parser.cpp
    tests/test_main.cpp
)

target_link_libraries(stdf_test
    # stdf  # Uncomment when libstdf is available
)