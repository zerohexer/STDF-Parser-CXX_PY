import os
import platform
import time
import re

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

result = stdf_parser_cpp.process_stdf_file_measurements("STDF_Files/OSBE25_KEWGBCLD1U_BE_HRG3201Y.09_KEWGBCLD1U__Prod_TPP202_03_Agilent_93000MT9510_25C_5264_1_20240910123955.stdf")
measurement_tuple = result['measurement_tuples']
print("parsed")