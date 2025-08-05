@echo off
REM Windows Universal STDF parser test launcher
echo 🚀 STDF C++ Parser Universal Test - Windows Version
echo ============================================================

REM Windows doesn't need LD_LIBRARY_PATH since we use static linking
REM The libstdf.a is already compiled into the Python extension

REM Check if Python extension exists
if not exist "stdf_parser_cpp.*.pyd" (
    echo ❌ Python extension not found!
    echo 📋 Build steps:
    echo 1. python setup_universal.py build_ext --inplace
    echo 2. run_test_windows_universal.bat
    exit /b 1
)

REM Run the test
echo 🪟 Windows: Using static-linked libstdf (no DLL dependencies)
python test_universal.py %*

echo.
echo ✅ Windows test completed!
echo 💡 This version uses static linking - no external DLLs needed!