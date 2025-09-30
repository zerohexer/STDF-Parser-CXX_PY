import os
import platform
import time
import sys
import glob
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

# Platform setup for C++ library
system = platform.system().lower()
if system == "linux":
    lib_dir = os.path.join(os.path.dirname(__file__), "cpp", "third_party", "lib")
    current_path = os.environ.get("LD_LIBRARY_PATH", "")
    if lib_dir not in current_path:
        os.environ["LD_LIBRARY_PATH"] = f"{lib_dir}:{current_path}" if current_path else lib_dir

try:
    import stdf_parser_cpp
    print("C++ STDF parser loaded")
except ImportError as e:
    print(f"C++ parser not available: {e}")
    exit(1)

def process_single_file(filepath):
    """Process a single STDF file and return measurements count and time"""
    start_time = time.time()
    try:
        result = stdf_parser_cpp.process_stdf_file_measurements(filepath)
        measurement_tuples = result['measurement_tuples']
        end_time = time.time()
        return len(measurement_tuples), end_time - start_time, None
    except Exception as e:
        end_time = time.time()
        return 0, end_time - start_time, str(e)

def find_stdf_files(path):
    """Find STDF files - single file or directory"""
    path_obj = Path(path)

    if path_obj.is_file():
        return [str(path_obj)]
    elif path_obj.is_dir():
        # Use set to avoid duplicates on Windows (case-insensitive filesystem)
        stdf_files = set()
        stdf_files.update(path_obj.glob("*.stdf"))
        stdf_files.update(path_obj.glob("*.STDF"))
        return [str(f) for f in stdf_files]
    else:
        return []

def main():
    if len(sys.argv) < 2:
        print("Usage: python extract_all_only_measurements.py <stdf_file_or_directory>")
        return

    input_path = sys.argv[1]
    files = find_stdf_files(input_path)

    if not files:
        print(f"No STDF files found in: {input_path}")
        return

    print(f"Found {len(files)} STDF file(s)")

    start_time = time.time()
    total_measurements = 0

    if len(files) == 1:
        # Single file - process directly
        print("Single file mode")
        measurements, file_time, error = process_single_file(files[0])
        if error:
            print(f"Error: {error}")
        else:
            total_measurements = measurements
            print(f"File: {measurements:,} measurements ({file_time:.2f}s)")

    else:
        # Multiple files - parallel processing with controlled processes
        MAX_WORKERS = 3  # Limit to avoid memory issues
        print(f"Parallel mode: {len(files)} files with {MAX_WORKERS} workers")

        with ProcessPoolExecutor(max_workers=MAX_WORKERS) as executor:
            # Submit all files
            future_to_file = {executor.submit(process_single_file, file): file for file in files}

            # Collect results as they complete
            max_file_time = 0.0
            for future in as_completed(future_to_file):
                file = future_to_file[future]
                filename = os.path.basename(file)

                try:
                    measurements, file_time, error = future.result()
                    if error:
                        print(f"{filename}: Error - {error}")
                    else:
                        total_measurements += measurements
                        max_file_time = max(max_file_time, file_time)
                        print(f"{filename}: {measurements:,} measurements ({file_time:.2f}s)")
                except Exception as e:
                    print(f"{filename}: Exception - {str(e)}")

        # Calculate speedup
        end_time = time.time()
        total_time = end_time - start_time
        if max_file_time > 0:
            estimated_sequential = max_file_time * len(files)
            speedup = estimated_sequential / total_time
            print(f"Speedup: {speedup:.1f}x")

    end_time = time.time()
    total_time = end_time - start_time

    print(f"\nSummary:")
    print(f"   Files: {len(files)}")
    print(f"   Total measurements: {total_measurements:,}")
    print(f"   Total time: {total_time:.2f}s")

if __name__ == "__main__":
    main()