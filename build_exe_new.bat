@echo off
chcp 65001 >nul
echo ====================================
echo Sora2 程序打包工具 - 新版本
echo ====================================
echo.

echo [检查] 检查Python环境...
python --version
if %errorlevel% neq 0 (
    echo 错误: 未找到Python，请先安装Python
    pause
    exit /b 1
)
echo.

echo [检查] 检查PyInstaller...
python -c "import PyInstaller" 2>nul
if %errorlevel% neq 0 (
    echo PyInstaller未安装，正在安装...
    python -m pip install pyinstaller
    if %errorlevel% neq 0 (
        echo 安装PyInstaller失败！
        pause
        exit /b 1
    )
)
echo.

echo [执行] 开始打包...
echo.
python build_exe_new.py

if %errorlevel% neq 0 (
    echo.
    echo 打包失败！请查看上面的错误信息。
    pause
    exit /b 1
)

echo.
pause

