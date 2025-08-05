@echo off
REM STDF C++ Parser - libstdf Installation Script for Windows
REM This script downloads and builds libstdf using Clang on Windows

echo 🚀 Installing libstdf for STDF C++ Parser (Windows/Clang)
echo ================================================================

REM Configuration
set LIBSTDF_VERSION=0.4
set LIBSTDF_URL=https://sourceforge.net/projects/freestdf/files/libstdf/libstdf-%LIBSTDF_VERSION%.tar.bz2
set LIBSTDF_DIR=libstdf-%LIBSTDF_VERSION%
set THIRD_PARTY_DIR=cpp\third_party

REM Create third_party directories
if not exist "%THIRD_PARTY_DIR%\include" mkdir "%THIRD_PARTY_DIR%\include"
if not exist "%THIRD_PARTY_DIR%\lib" mkdir "%THIRD_PARTY_DIR%\lib"
if not exist "%THIRD_PARTY_DIR%\bin" mkdir "%THIRD_PARTY_DIR%\bin"

REM Check for required tools
echo 🔍 Checking for required tools...

where clang >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo ❌ Clang not found! Please install LLVM/Clang
    echo    Download from: https://releases.llvm.org/download.html
    echo    Or use: winget install LLVM.LLVM
    pause
    exit /b 1
)

where python >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo ❌ Python not found! Please install Python 3.7+
    pause
    exit /b 1
)

REM Check for MSYS2/MinGW tools (needed for autotools)
where bash >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo ❌ Bash not found! You need MSYS2 or Git Bash for autotools
    echo    Install MSYS2 from: https://www.msys2.org/
    echo    Or use Git Bash that comes with Git for Windows
    pause
    exit /b 1
)

echo ✅ All required tools found

REM Download libstdf if not already present
if not exist "%LIBSTDF_DIR%.tar.bz2" (
    echo 📥 Downloading libstdf %LIBSTDF_VERSION%...
    
    REM Try different download methods
    where curl >nul 2>&1
    if %ERRORLEVEL% equ 0 (
        curl -L -o "%LIBSTDF_DIR%.tar.bz2" "%LIBSTDF_URL%"
    ) else (
        where powershell >nul 2>&1
        if %ERRORLEVEL% equ 0 (
            powershell -Command "& {Invoke-WebRequest -Uri '%LIBSTDF_URL%' -OutFile '%LIBSTDF_DIR%.tar.bz2'}"
        ) else (
            echo ❌ Neither curl nor PowerShell found for downloading
            echo    Please manually download: %LIBSTDF_URL%
            pause
            exit /b 1
        )
    )
) else (
    echo ✅ libstdf archive already present
)

REM Extract using tar (available in Windows 10+) or 7-Zip
if not exist "%LIBSTDF_DIR%" (
    echo 📦 Extracting libstdf...
    
    REM Try Windows 10+ built-in tar
    where tar >nul 2>&1
    if %ERRORLEVEL% equ 0 (
        tar -xjf "%LIBSTDF_DIR%.tar.bz2"
    ) else (
        REM Try 7-Zip
        where 7z >nul 2>&1
        if %ERRORLEVEL% equ 0 (
            7z x "%LIBSTDF_DIR%.tar.bz2"
            7z x "%LIBSTDF_DIR%.tar"
            del "%LIBSTDF_DIR%.tar"
        ) else (
            echo ❌ Neither tar nor 7-Zip found for extraction
            echo    Please install 7-Zip or manually extract the archive
            pause
            exit /b 1
        )
    )
) else (
    echo ✅ libstdf already extracted
)

REM Build libstdf using MSYS2/MinGW environment
echo 🔨 Building libstdf with Clang...
cd "%LIBSTDF_DIR%"

REM Set environment for Clang
set CC=clang
set CXX=clang++
set CFLAGS=-O3 -fPIC
set CXXFLAGS=-O3 -fPIC

REM Configure with autotools (requires MSYS2/MinGW environment)
bash -c "./configure --prefix=$(pwd | sed 's|\\\\|/|g')/../%THIRD_PARTY_DIR% --enable-shared=no --enable-static=yes CC=clang CXX=clang++"

if %ERRORLEVEL% neq 0 (
    echo ❌ Configure failed. Make sure you have MSYS2 installed with autotools
    echo    Run in MSYS2: pacman -S autotools-wrapper automake autoconf
    pause
    exit /b 1
)

REM Build
bash -c "make clean || true"
bash -c "make"

if %ERRORLEVEL% neq 0 (
    echo ❌ Build failed
    pause
    exit /b 1
)

REM Install to third_party
bash -c "make install"

cd ..

REM Verify installation
echo ✅ Verifying libstdf installation...
if exist "%THIRD_PARTY_DIR%\include\libstdf.h" (
    echo ✅ libstdf headers installed
) else (
    echo ❌ libstdf headers not found
    pause
    exit /b 1
)

if exist "%THIRD_PARTY_DIR%\lib\libstdf.a" (
    echo ✅ libstdf static library installed
) else (
    echo ❌ libstdf library not found
    pause
    exit /b 1
)

REM Update setup.py to enable libstdf
echo 🔧 Updating setup.py to enable libstdf...
powershell -Command "(Get-Content setup.py) -replace '# \"stdf\",  # Uncomment when libstdf is available', '\"stdf\",  # libstdf library' | Set-Content setup.py"

REM Update C++ source to enable libstdf
echo 🔧 Updating C++ source to enable libstdf...
powershell -Command "(Get-Content cpp\\src\\stdf_parser.cpp) -replace '// #include <libstdf.h>', '#include <libstdf.h>' | Set-Content cpp\\src\\stdf_parser.cpp"

echo 🎉 libstdf installation completed!
echo.
echo Next steps:
echo 1. Build the C++ extension:
echo    python setup.py build_ext --inplace
echo.
echo 2. Test the installation:
echo    python tests\test_cpp_parser.py
echo.
echo 3. Run performance benchmark:
echo    python -c "from python.stdf_cpp_wrapper import test_cpp_parser; test_cpp_parser()"

REM Cleanup
echo 🧹 Cleaning up temporary files...
if exist "%LIBSTDF_DIR%" rmdir /s /q "%LIBSTDF_DIR%"
if exist "%LIBSTDF_DIR%.tar.bz2" del "%LIBSTDF_DIR%.tar.bz2"

echo ✅ Installation complete!
pause