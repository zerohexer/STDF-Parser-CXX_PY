@echo off
REM Windows STDF parser test launcher

echo Testing STDF C++ Parser on Windows...

REM Add library path for Windows (if using DLLs)
set PATH=%~dp0cpp\third_party\lib;%PATH%

REM Run the test
python test_parser.py %*

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ❌ Test failed with error code: %ERRORLEVEL%
    pause
) else (
    echo.
    echo ✅ Test completed successfully!
)

REM Keep window open for results
pause