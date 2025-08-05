@echo off
REM Run the working WSL STDF parser from Windows
echo 🚀 STDF C++ Parser - WSL Version from Windows
echo ============================================================

echo 🔄 Running WSL-based STDF parser...
echo.

REM Run the working WSL version
wsl cd /mnt/c/Users/AdminPEN.AAn/PycharmProjects/STDFReader_CPP && ./run_test.sh

echo.
echo ✅ WSL parsing completed!
echo 💡 This uses the proven working Linux libstdf with full performance
pause