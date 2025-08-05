@echo off
REM Build simple STDF DLL using MSVC
echo 🔨 Building simple STDF DLL using MSVC...

REM Compile the DLL with explicit exports
cl /LD simple_stdf_dll.c /Fe:libstdf.dll /link /EXPORT:simple_stdf_open /EXPORT:simple_stdf_read_record /EXPORT:simple_stdf_close /EXPORT:simple_stdf_version

if %ERRORLEVEL% equ 0 (
    echo ✅ libstdf.dll built successfully!
    echo 📂 File created: libstdf.dll
    dir libstdf.dll
) else (
    echo ❌ Build failed!
)

pause