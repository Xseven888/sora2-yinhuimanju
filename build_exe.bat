@echo off
chcp 65001 >nul
echo ====================================
echo Sora2 Video Generator - PyInstaller Build
echo ====================================
echo.

echo [1/5] Checking PyInstaller...
python -c "import PyInstaller" 2>nul
if %errorlevel% neq 0 (
    echo PyInstaller not found, installing...
    python -m pip install pyinstaller
    :: Check if installation was successful by trying to import again
    python -c "import PyInstaller" 2>nul
    if %errorlevel% neq 0 (
        echo Failed to install PyInstaller!
        pause
        exit /b 1
    )
    echo PyInstaller installed successfully!
) else (
    echo PyInstaller is already installed
)
echo.

echo Installing/updating imageio and imageio-ffmpeg...
python -m pip install --upgrade imageio imageio-ffmpeg
if %errorlevel% neq 0 (
    echo Failed to install dependencies!
    pause
    exit /b 1
)
echo Dependencies installed
echo.

echo [1.5/5] Converting icon file...
if exist logo.ico (
    echo logo.ico already exists, skipping conversion
) else (
    if exist logo.png (
        python convert_icon.py
        if %errorlevel% neq 0 (
            echo Icon conversion failed, will try to use PNG directly
        )
    ) else (
        echo Warning: logo.png not found, will use default icon
    )
)
echo.

echo [1.6/5] Creating PyInstaller hook to fix encoding...
python fix_pyinstaller_qt.py
if %errorlevel% neq 0 (
    echo Warning: Could not create hook file, continuing anyway...
)
echo.

echo [2/5] Cleaning old build files...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist *.spec del /q *.spec

if exist dist\Sora2.exe (
    echo Deleting old exe file...
    del /f /q dist\Sora2.exe
)
echo Cleanup completed
echo.

echo [3/5] Starting build...
echo Building single-file exe with PyInstaller...
echo.
echo Using Python script to handle encoding issues...
python build_exe.py

if %errorlevel% neq 0 (
    echo.
    echo Build failed! Please check the error messages above.
    pause
    exit /b 1
)

echo.
echo [4/5] Build completed!
echo.

echo [5/5] Checking generated files...
if exist dist\Sora2\Sora2.exe (
    echo Successfully generated: dist\Sora2\Sora2.exe
    echo.
    echo File information:
    dir dist\Sora2\Sora2.exe
    echo.
    echo ====================================
    echo Build completed successfully!
    echo ====================================
    echo.
    echo Executable location: dist\Sora2\Sora2.exe
    echo.
    echo NOTE: This is a directory build (onedir mode).
    echo All required DLLs and files are in: dist\Sora2\
    echo You need to keep all files together to run the program.
    echo.
    echo To test, run: dist\Sora2\Sora2.exe
    echo.
) else if exist dist\Sora2.exe (
    echo Successfully generated: dist\Sora2.exe
    echo.
    echo File information:
    dir dist\Sora2.exe
    echo.
    echo ====================================
    echo Build completed successfully!
    echo ====================================
    echo.
    echo Executable location: dist\Sora2.exe
    echo You can copy dist\Sora2.exe to any location to run
    echo.
) else (
    echo Generated exe file not found
    echo Build may have failed, please check error messages above
    echo.
    echo Checking dist directory:
    if exist dist (
        dir dist
    ) else (
        echo dist directory does not exist
    )
)

pause
