@echo off
echo ============================================
echo   Lineage Classic English Translation Patch
echo   1,644 translations (443 strings + 1,201 items)
echo ============================================
echo.

set "GAME_DIR=C:\Program Files (x86)\NCSOFT\Lineage Classic"
set "USER_DIR=%USERPROFILE%"

echo [1/4] Backing up original DLL...
if not exist "%GAME_DIR%\libcrypto_orig.dll" (
    copy "%GAME_DIR%\libcrypto-3-x64.dll" "%GAME_DIR%\libcrypto_orig.dll"
    echo       Backed up original DLL
) else (
    echo       Backup already exists, skipping
)

echo [2/4] Installing proxy DLL...
copy /Y "%~dp0lcx_english.dll" "%GAME_DIR%\libcrypto-3-x64.dll" >nul
echo       Proxy DLL installed

echo [3/4] Installing translation patches...
if not exist "%USER_DIR%\lcx_final" mkdir "%USER_DIR%\lcx_final"
copy /Y "%~dp0string_en_padded.zst" "%USER_DIR%\lcx_final\" >nul
copy /Y "%~dp0items_en_padded.zst" "%USER_DIR%\lcx_final\" >nul
echo       Patches installed

echo [4/4] Installing fingerprint files...
if not exist "%USER_DIR%\lcx_decrypted" mkdir "%USER_DIR%\lcx_decrypted"
copy /Y "%~dp0file_00083.bin" "%USER_DIR%\lcx_decrypted\" >nul
copy /Y "%~dp0file_00084.bin" "%USER_DIR%\lcx_decrypted\" >nul
echo       Fingerprints installed

echo.
echo ============================================
echo   Done! Launch the game to see English text.
echo ============================================
pause
