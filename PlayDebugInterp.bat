@echo off
REM ---------------------------------------------------------------------------
REM Yu-Gi-Oh! Forbidden Memories - Recompiled  (DEBUG BUILD + FRAME INTERPOLATION)
REM
REM Identical to PlayDebug.bat, but engages presentation-only frame
REM interpolation at 240 FPS before launch. Guest timing is unchanged; only the
REM number of times the finished frame is presented goes up.
REM
REM This exists because the two env vars below are easy to lose: set them in one
REM shell and launch from another and the runtime silently starts WITHOUT
REM interpolation while everything else looks identical. The banner below prints
REM what was actually set, and the runtime prints its own
REM "psxrecomp: GL frame interpolation ..." line a few seconds later - if those
REM two disagree, believe the runtime.
REM ---------------------------------------------------------------------------

setlocal

set "SDL_JOYSTICK_DIRECTINPUT=0"
set "PSX_FRAME_INTERPOLATION=1"
set "PSX_FRAME_INTERPOLATION_FPS=240"
set "EXE=Yu_Gi_Oh_Forbidden_Memories_Recompiled.exe"
set "GAMEDIR=%~dp0build-dbg"

if not exist "%GAMEDIR%\%EXE%" (
    echo ERROR: debug build not found in "%GAMEDIR%".
    echo     cmake --build build-dbg --target psx-runtime
    echo.
    pause
    exit /b 1
)

echo ===============================================================
echo  Yu-Gi-Oh! Forbidden Memories - Recompiled   [DEBUG + INTERP]
echo  PSX_FRAME_INTERPOLATION     = %PSX_FRAME_INTERPOLATION%
echo  PSX_FRAME_INTERPOLATION_FPS = %PSX_FRAME_INTERPOLATION_FPS%
echo  Debug server: 127.0.0.1:4370
echo  Watch for "psxrecomp: GL frame interpolation enabled" below.
echo ===============================================================
echo.

cd /d "%GAMEDIR%"
"%GAMEDIR%\%EXE%"
set "RC=%ERRORLEVEL%"

echo.
echo === exited with code %RC% ===
if not "%RC%"=="0" (
    echo Non-zero exit - leaving this window open so you can read the log.
    pause
)

exit /b %RC%
