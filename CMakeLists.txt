cmake_minimum_required(VERSION 3.12)
project(STDFReader_CPP VERSION 1.0.0 LANGUAGES C CXX)

# Set C++ standard
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

# Set C standard for libstdf compatibility
set(CMAKE_C_STANDARD 99)
set(CMAKE_C_STANDARD_REQUIRED ON)

# Build type
if(NOT CMAKE_BUILD_TYPE)
    set(CMAKE_BUILD_TYPE Release)
endif()

# Compiler flags
if(MSVC)
    set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} /W4 /O2")
    set(CMAKE_C_FLAGS "${CMAKE_C_FLAGS} /W3 /O2")
else()
    set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -Wall -Wextra -O3")
    set(CMAKE_C_FLAGS "${CMAKE_C_FLAGS} -Wall -Wextra -O3")
endif()

# Platform detection
if(WIN32)
    message(STATUS "Building for Windows")
    set(PLATFORM_SUFFIX "_windows")
    set(LIB_EXTENSION ".dll")
else()
    message(STATUS "Building for Unix/Linux")
    set(PLATFORM_SUFFIX "")
    set(LIB_EXTENSION ".so")
endif()

# Find Python for extension building
find_package(Python3 COMPONENTS Interpreter Development REQUIRED)
message(STATUS "Found Python: ${Python3_VERSION}")

# ============================================================================
# PROJECT STRUCTURE DETECTION
# ============================================================================

# ============================================================================
# LIBSTDF DETECTION WITH FALLBACK OPTIONS
# ============================================================================

# Try multiple libstdf locations in order of preference
set(LIBSTDF_SEARCH_PATHS
    "${CMAKE_CURRENT_SOURCE_DIR}/cpp/third_party${PLATFORM_SUFFIX}"  # Platform-specific
    "${CMAKE_CURRENT_SOURCE_DIR}/cpp/third_party"                    # Generic
    "${CMAKE_CURRENT_SOURCE_DIR}/libstdf-0.4"                        # Source build
    "/usr/local"                                                      # System install
    "/usr"                                                           # System install
)

set(LIBSTDF_FOUND FALSE)
set(LIBSTDF_SOURCE_FOUND FALSE)

# Search for libstdf in order of preference
foreach(search_path ${LIBSTDF_SEARCH_PATHS})
    if(NOT LIBSTDF_FOUND)
        set(LIBSTDF_INCLUDE_DIR "${search_path}/include")
        set(LIBSTDF_LIB_DIR "${search_path}/lib")
        
        # Check for headers
        if(EXISTS "${LIBSTDF_INCLUDE_DIR}/libstdf.h")
            message(STATUS "Found libstdf headers: ${LIBSTDF_INCLUDE_DIR}")
            
            # Find library files
            find_library(LIBSTDF_LIBRARY
                NAMES stdf libstdf
                PATHS ${LIBSTDF_LIB_DIR} "${search_path}/src/.libs"
                NO_DEFAULT_PATH
            )
            
            if(LIBSTDF_LIBRARY)
                message(STATUS "Found libstdf library: ${LIBSTDF_LIBRARY}")
                set(LIBSTDF_FOUND TRUE)
                set(THIRD_PARTY_BASE ${search_path})
                break()
            else()
                message(STATUS "libstdf headers found at ${search_path} but no library")
            endif()
        endif()
    endif()
endforeach()

# Check for libstdf source code (for building from source if needed)
if(EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/libstdf-0.4/src/libstdf.c")
    set(LIBSTDF_SOURCE_FOUND TRUE)
    message(STATUS "Found libstdf source code: libstdf-0.4/")
endif()

# Option to build libstdf from source
option(BUILD_LIBSTDF_FROM_SOURCE "Build libstdf from source if available" OFF)

# Auto-build libstdf from source if requested and source is available
if(BUILD_LIBSTDF_FROM_SOURCE AND LIBSTDF_SOURCE_FOUND AND NOT LIBSTDF_FOUND)
    message(STATUS "Building libstdf from source using your build commands...")
    set(LIBSTDF_SOURCE_DIR "${CMAKE_CURRENT_SOURCE_DIR}/libstdf-0.4")
    
    # Use your exact build commands with proper target directory
    if(WIN32)
        # Windows build - use your cross-compilation commands
        set(LIBSTDF_TARGET_DIR "${CMAKE_CURRENT_SOURCE_DIR}/cpp/third_party_windows")
        set(CONFIGURE_ARGS --host=x86_64-w64-mingw32 --prefix=${LIBSTDF_TARGET_DIR} --enable-static --disable-shared --enable-endian=little)
        message(STATUS "Building libstdf for Windows (cross-compiled)")
    else()
        # Linux/Unix build - use your standard commands  
        set(LIBSTDF_TARGET_DIR "${CMAKE_CURRENT_SOURCE_DIR}/cpp/third_party")
        set(CONFIGURE_ARGS --prefix=${LIBSTDF_TARGET_DIR} --enable-static --enable-shared)
        message(STATUS "Building libstdf for Unix/Linux")
    endif()
    
    # Configure and build libstdf using your exact commands
    include(ExternalProject)
    ExternalProject_Add(libstdf_external
        SOURCE_DIR ${LIBSTDF_SOURCE_DIR}
        CONFIGURE_COMMAND <SOURCE_DIR>/configure ${CONFIGURE_ARGS}
        BUILD_COMMAND make
        INSTALL_COMMAND make install
        BUILD_IN_SOURCE 1
        LOG_CONFIGURE ON
        LOG_BUILD ON
        LOG_INSTALL ON
    )
    
    # Set paths for the built library (will be available after build)
    set(LIBSTDF_INCLUDE_DIR "${LIBSTDF_TARGET_DIR}/include")
    set(LIBSTDF_LIB_DIR "${LIBSTDF_TARGET_DIR}/lib")
    
    # Find the appropriate library file
    if(WIN32)
        set(LIBSTDF_LIBRARY "${LIBSTDF_LIB_DIR}/libstdf.a")  # Static only for Windows
    else()
        # Prefer shared library on Linux, fallback to static
        find_library(LIBSTDF_LIBRARY
            NAMES stdf libstdf
            PATHS ${LIBSTDF_LIB_DIR}
            NO_DEFAULT_PATH
        )
        if(NOT LIBSTDF_LIBRARY)
            set(LIBSTDF_LIBRARY "${LIBSTDF_LIB_DIR}/libstdf.a")
        endif()
    endif()
    
    set(LIBSTDF_FOUND TRUE)
    set(THIRD_PARTY_BASE ${LIBSTDF_TARGET_DIR})
    
    message(STATUS "libstdf will be built to: ${LIBSTDF_TARGET_DIR}")
    message(STATUS "Build command: cd libstdf-0.4 && ./configure ${CONFIGURE_ARGS} && make && make install")
endif()

# Final status
if(LIBSTDF_FOUND)
    message(STATUS "libstdf integration: ENABLED")
    message(STATUS "Using libstdf from: ${THIRD_PARTY_BASE}")
elseif(LIBSTDF_SOURCE_FOUND)
    message(STATUS "libstdf integration: SOURCE AVAILABLE")
    message(STATUS "Use -DBUILD_LIBSTDF_FROM_SOURCE=ON to build automatically")
    message(STATUS "")
    message(STATUS "Or build manually:")
    if(WIN32)
        message(STATUS "  cd libstdf-0.4")
        message(STATUS "  ./configure --host=x86_64-w64-mingw32 --prefix=$PWD/../cpp/third_party_windows --enable-static --disable-shared --enable-endian=little")
        message(STATUS "  make && make install")
    else()
        message(STATUS "  cd libstdf-0.4") 
        message(STATUS "  ./configure --prefix=$PWD/../cpp/third_party --enable-static --enable-shared")
        message(STATUS "  make && make install")
    endif()
else()
    message(STATUS "libstdf integration: DISABLED")
    message(STATUS "STDF parsing will use fallback implementation")
endif()

# ============================================================================
# SOURCE FILES DETECTION
# ============================================================================

# Core C++ sources
set(CPP_SRC_DIR "${CMAKE_CURRENT_SOURCE_DIR}/cpp/src")
set(CPP_INC_DIR "${CMAKE_CURRENT_SOURCE_DIR}/cpp/include")

# Detect all C++ source files
file(GLOB STDF_CORE_SOURCES "${CPP_SRC_DIR}/*.cpp")
file(GLOB STDF_CORE_HEADERS "${CPP_INC_DIR}/*.h")

# Filter out python_bridge.cpp for separate handling
list(FILTER STDF_CORE_SOURCES EXCLUDE REGEX ".*python_bridge.cpp$")

list(LENGTH STDF_CORE_SOURCES source_count)
message(STATUS "Found ${source_count} core C++ source files:")
foreach(source ${STDF_CORE_SOURCES})
    get_filename_component(name ${source} NAME)
    message(STATUS "   - ${name}")
endforeach()

# Check for Python bridge
set(PYTHON_BRIDGE "${CPP_SRC_DIR}/python_bridge.cpp")
if(EXISTS ${PYTHON_BRIDGE})
    message(STATUS "Found Python bridge: python_bridge.cpp")
    set(PYTHON_BRIDGE_FOUND TRUE)
else()
    message(STATUS "Python bridge not found")
    set(PYTHON_BRIDGE_FOUND FALSE)
endif()

# ============================================================================
# INCLUDE AND LIBRARY DIRECTORIES
# ============================================================================

include_directories(
    ${CPP_INC_DIR}
    ${LIBSTDF_INCLUDE_DIR}
    ${Python3_INCLUDE_DIRS}
)

link_directories(
    ${LIBSTDF_LIB_DIR}
)

# ============================================================================
# BUILD TARGETS
# ============================================================================

# Core static library
if(STDF_CORE_SOURCES)
    add_library(stdf_parser_core STATIC ${STDF_CORE_SOURCES})
    
    target_compile_definitions(stdf_parser_core PRIVATE
        -D__STDF_VER4__
        $<$<CONFIG:Debug>:-DDEBUG>
        $<$<BOOL:${LIBSTDF_FOUND}>:-DHAVE_LIBSTDF>
    )
    
    if(LIBSTDF_FOUND)
        target_link_libraries(stdf_parser_core ${LIBSTDF_LIBRARY})
        
        # Add dependency if building from external project
        if(TARGET libstdf_external)
            add_dependencies(stdf_parser_core libstdf_external)
        endif()
    endif()
    
    message(STATUS "Building core static library")
else()
    message(FATAL_ERROR "No C++ source files found in ${CPP_SRC_DIR}")
endif()

# Python extension module
if(PYTHON_BRIDGE_FOUND AND Python3_FOUND)
    add_library(stdf_parser_cpp MODULE
        ${PYTHON_BRIDGE}
        ${STDF_CORE_SOURCES}
    )
    
    # Python extension properties
    set_target_properties(stdf_parser_cpp PROPERTIES
        PREFIX ""
        SUFFIX ${LIB_EXTENSION}
        LIBRARY_OUTPUT_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}
    )
    
    # Link libraries
    target_link_libraries(stdf_parser_cpp 
        ${Python3_LIBRARIES}
        $<$<BOOL:${LIBSTDF_FOUND}>:${LIBSTDF_LIBRARY}>
    )
    
    # Add dependency if building from external project
    if(TARGET libstdf_external)
        add_dependencies(stdf_parser_cpp libstdf_external)
    endif()
    
    target_compile_definitions(stdf_parser_cpp PRIVATE
        -D__STDF_VER4__
        $<$<CONFIG:Debug>:-DDEBUG>
        $<$<BOOL:${LIBSTDF_FOUND}>:-DHAVE_LIBSTDF>
    )
    
    message(STATUS "Building Python extension: stdf_parser_cpp${LIB_EXTENSION}")
else()
    message(STATUS "Skipping Python extension (missing bridge or Python)")
endif()

# ============================================================================
# TEST EXECUTABLES
# ============================================================================

# Find all test C++ files in root directory
file(GLOB TEST_CPP_FILES "${CMAKE_CURRENT_SOURCE_DIR}/test_*.cpp")

if(TEST_CPP_FILES)
    list(LENGTH TEST_CPP_FILES test_count)
    message(STATUS "Found ${test_count} test files:")
    
    foreach(test_file ${TEST_CPP_FILES})
        get_filename_component(test_name ${test_file} NAME_WE)
        message(STATUS "   - ${test_name}")
        
        add_executable(${test_name} ${test_file})
        
        target_link_libraries(${test_name} 
            stdf_parser_core
            $<$<BOOL:${LIBSTDF_FOUND}>:${LIBSTDF_LIBRARY}>
        )
        
        # Set output directory for tests
        set_target_properties(${test_name} PROPERTIES
            RUNTIME_OUTPUT_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}
        )
    endforeach()
else()
    message(STATUS "No test files found (test_*.cpp)")
endif()

# ============================================================================
# PYTHON SCRIPTS DETECTION
# ============================================================================

file(GLOB PYTHON_SCRIPTS "${CMAKE_CURRENT_SOURCE_DIR}/*.py")
if(PYTHON_SCRIPTS)
    list(LENGTH PYTHON_SCRIPTS script_count)
    message(STATUS "Found ${script_count} Python scripts in project root")
endif()

# ============================================================================
# INSTALLATION
# ============================================================================

# Install Python extension to project root
if(TARGET stdf_parser_cpp)
    install(TARGETS stdf_parser_cpp
        LIBRARY DESTINATION ${CMAKE_CURRENT_SOURCE_DIR}
    )
endif()

# Install headers for C++ development
install(DIRECTORY ${CPP_INC_DIR}/ 
    DESTINATION include/stdf_parser
    FILES_MATCHING PATTERN "*.h"
)

# Install static library
if(TARGET stdf_parser_core)
    install(TARGETS stdf_parser_core
        ARCHIVE DESTINATION lib
        LIBRARY DESTINATION lib
    )
endif()

# ============================================================================
# BUILD SUMMARY
# ============================================================================

message(STATUS "")
message(STATUS "============================================================")
message(STATUS "STDF Reader C++ - Build Configuration Summary")
message(STATUS "============================================================")
message(STATUS "Project: ${CMAKE_PROJECT_NAME} v${CMAKE_PROJECT_VERSION}")
message(STATUS "Platform: ${CMAKE_SYSTEM_NAME}")
message(STATUS "Build Type: ${CMAKE_BUILD_TYPE}")
message(STATUS "C++ Standard: ${CMAKE_CXX_STANDARD}")
message(STATUS "")
message(STATUS "Components Built:")
message(STATUS "   Core Library: stdf_parser_core")
if(TARGET stdf_parser_cpp)
    message(STATUS "   Python Extension: YES")
else()
    message(STATUS "   Python Extension: NO")
endif()
if(TEST_CPP_FILES)
    list(LENGTH TEST_CPP_FILES test_count)
    message(STATUS "   Test Executables: ${test_count}")
else()
    message(STATUS "   Test Executables: 0")
endif()
message(STATUS "")
message(STATUS "Dependencies:")
message(STATUS "   libstdf: ${LIBSTDF_FOUND}")
message(STATUS "   Python: ${Python3_VERSION}")
message(STATUS "")
message(STATUS "Paths:")
message(STATUS "   Sources: ${CPP_SRC_DIR}")
message(STATUS "   Headers: ${CPP_INC_DIR}")
message(STATUS "   libstdf: ${THIRD_PARTY_BASE}")
message(STATUS "============================================================")
message(STATUS "")