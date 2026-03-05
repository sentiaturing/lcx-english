@echo off
echo Uninstalling English Translation Patch...

set "GAME_DIR=C:\Program Files (x86)\NCSOFT\Lineage Classic"

if exist "%GAME_DIR%\libcrypto_orig.dll" (
    copy /Y "%GAME_DIR%\libcrypto_orig.dll" "%GAME_DIR%\libcrypto-3-x64.dll" >nul
    del "%GAME_DIR%\libcrypto_orig.dll"
    echo   Original DLL restored.
) else (
    echo   ERROR: No backup found at %GAME_DIR%\libcrypto_orig.dll
    echo   Cannot uninstall. You may need to reinstall the game.
)

echo Done!
pause
