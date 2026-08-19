@echo off
REM ---------------------------------------------------------------------------
REM Yu-Gi-Oh! Forbidden Memories - Recompiled  (DEBUG BUILD)
REM
REM Same game as Play.bat, but built with PSX_DEBUG_TOOLS=ON, which adds the
REM TCP debug server on 127.0.0.1:4370. That is what lets memory scanning,
REM write-tracing and framebuffer screenshots work while you play.
REM
REM This window stays open and shows the runtime's log, so leave it visible if
REM something misbehaves - the last lines usually say why.
REM
REM SDL_JOYSTICK_DIRECTINPUT=0 is REQUIRED on this machine: without it the
REM process hangs in DirectInput HID enumeration before reaching the game.
REM ---------------------------------------------------------------------------

setlocal

set "SDL_JOYSTICK_DIRECTINPUT=0"
set "EXE=Yu_Gi_Oh_Forbidden_Memories_Recompiled.exe"
set "GAMEDIR=%~dp0build-dbg"

if not exist "%GAMEDIR%\%EXE%" (
    echo ERROR: debug build not found in "%GAMEDIR%".
    echo Build it from "%~dp0":
    echo     cmake -S . -B build-dbg -G Ninja -DCMAKE_BUILD_TYPE=Release -DPSX_REWIND=OFF -DPSX_DEBUG_TOOLS=ON
    echo     cmake --build build-dbg --target psx-runtime
    echo.
    pause
    exit /b 1
)

echo ===============================================================
echo  Yu-Gi-Oh! Forbidden Memories - Recompiled   [DEBUG]
echo  Debug server: 127.0.0.1:4370
echo  Keep this window open; the runtime log prints below.
echo ===============================================================
echo.

REM Run from the game dir so saves/settings/bios resolve beside the exe, but
REM invoke by FULL PATH - a bare "name.exe" needs cmd to search the current
REM directory, which fails when NoDefaultCurrentDirectoryInExePath is set.
cd /d "%GAMEDIR%"
"%GAMEDIR%\%EXE%"
set "RC=%ERRORLEVEL%"

echo.
echo === exited with code %RC% ===

REM Close with the game on a normal exit. Only hold the window open when
REM something went wrong, so the log above stays readable instead of vanishing.
if not "%RC%"=="0" (
    echo Non-zero exit - leaving this window open so you can read the log.
    pause
)

exit /b %RC%
