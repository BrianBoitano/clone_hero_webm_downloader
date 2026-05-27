@echo off
setlocal EnableDelayedExpansion
cd /d "%~dp0"

set "STATEFILE=%~dp0last_scan_path.txt"
set "DEFAULTROOT=\\10.0.0.115\Vault\Clone Hero\01_songs"
set "SCANROOT="

if exist "%STATEFILE%" (
    set /p SCANROOT=<"%STATEFILE%"
)

if not defined SCANROOT (
    set "SCANROOT=%DEFAULTROOT%"
)

echo.
echo ==================================================
echo Clone Hero WebM Downloader - Fuzzy Match Edition
echo ==================================================
echo.
echo This tool will:
echo   - scan the folder you choose in alphabetical order
echo   - use song.ini artist/title when available
echo   - score multiple YouTube results
echo   - pick the best match
echo   - download and convert it to video.webm
echo.
echo Overwrite explanation:
echo   - YES = replace an existing video.webm if one is already there
echo   - NO  = skip folders that already have video.webm
echo.
echo Current default scan path:
echo   %SCANROOT%
echo.
set /p USERPATH=Enter folder to scan, or press Enter to use the default: 

if not "%USERPATH%"=="" (
    set "SCANROOT=%USERPATH%"
)

if "%SCANROOT%"=="" (
    echo No path entered. Exiting.
    pause
    exit /b 1
)

> "%STATEFILE%" echo %SCANROOT%

echo.
set /p SUFFIX=Search suffix [default: none]: 

echo.
set /p SEARCHCOUNT=How many YouTube results to score [default: 5]: 
if "%SEARCHCOUNT%"=="" set "SEARCHCOUNT=5"

echo.
set /p OVERWRITECHOICE=Overwrite existing video.webm files? (Y/N): 
set "OVERWRITEARG="
if /I "%OVERWRITECHOICE%"=="Y" set "OVERWRITEARG=--overwrite"
if /I "%OVERWRITECHOICE%"=="YES" set "OVERWRITEARG=--overwrite"

echo.
set /p ALIGNCHOICE=Try auto-align against song audio in each folder? (Y/N): 
set "ALIGNARG="
if /I "%ALIGNCHOICE%"=="Y" set "ALIGNARG=--auto-align"
if /I "%ALIGNCHOICE%"=="YES" set "ALIGNARG=--auto-align"

echo.
echo ==================================================
echo Running with:
echo   Scan path    : %SCANROOT%
echo   Search suffix: %SUFFIX%
echo   Search count : %SEARCHCOUNT%
if defined OVERWRITEARG (
    echo   Overwrite    : YES
) else (
    echo   Overwrite    : NO
)
if defined ALIGNARG (
    echo   Auto-align   : YES
) else (
    echo   Auto-align   : NO
)
echo ==================================================
echo.

python "%~dp0CloneHeroWebmDownloader_fuzzy_v2.py" "%SCANROOT%" --suffix "%SUFFIX%" --search-count %SEARCHCOUNT% %OVERWRITEARG% %ALIGNARG%

echo.
pause
