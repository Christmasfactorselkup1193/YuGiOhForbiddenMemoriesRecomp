@echo off
REM ---------------------------------------------------------------------------
REM Yu-Gi-Oh! Forbidden Memories - Recompiled
REM
REM SDL_JOYSTICK_DIRECTINPUT=0 is REQUIRED on this machine. Without it the
REM process hangs during SDL joystick init inside DirectInput HID enumeration
REM (SDL_DINPUT_JoystickDetect -> HidD_GetProductString -> DeviceIoControl)
REM and never reaches the emulation loop - it looks like a dead black window.
REM XInput and RAWINPUT still provide controller support, so nothing is lost.
REM
REM Usage:   Play.bat          normal (Release build)
REM          Play.bat -dbg     instrumented build, TCP debug server on port 4370
REM ---------------------------------------------------------------------------

setlocal

set "SDL_JOYSTICK_DIRECTINPUT=0"
set "EXE=Yu_Gi_Oh_Forbidden_Memories_Recompiled.exe"

if /I "%~1"=="-dbg" (
    set "GAMEDIR=%~dp0build-dbg"
) else (
    set "GAMEDIR=%~dp0build"
)

if not exist "%GAMEDIR%\%EXE%" (
    echo ERROR: %EXE% not found in "%GAMEDIR%".
    echo Build it first, from "%~dp0":
    echo     cmake --build build --target psx-runtime
    echo.
    pause
    exit /b 1
)

REM Run from the game dir so saves/settings/bios resolve beside the exe, but
REM invoke by FULL PATH - a bare "name.exe" needs cmd to search the current
REM directory, which fails when NoDefaultCurrentDirectoryInExePath is set.
cd /d "%GAMEDIR%"
"%GAMEDIR%\%EXE%"
set "RC=%ERRORLEVEL%"

if not "%RC%"=="0" (
    echo.
    echo Exited with code %RC%.
    pause
)

exit /b %RC%
