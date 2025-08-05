@echo off
REM Build libstdf as a native Windows DLL using MSYS2/MinGW
echo 🔨 Building libstdf as Windows DLL using native MinGW...

REM Check if we're in MSYS2 environment
where gcc >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo ❌ MinGW/GCC not found!
    echo Please run this from MSYS2 MinGW64 terminal
    echo Or install MinGW-w64 standalone
    pause
    exit /b 1
)

REM Clean and configure for Windows DLL
cd libstdf-0.4
make clean
./configure --enable-shared --disable-static --prefix=%CD%/../cpp/third_party_windows

REM Build the DLL
make -j4

REM Install
make install

echo ✅ Windows DLL build complete!
echo 📂 Check cpp/third_party_windows/bin/ for libstdf.dll
pause