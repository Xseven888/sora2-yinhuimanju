#!/bin/bash

echo "===================================="
echo "Sora2 视频生成工具 - PyInstaller 打包 (MacOS)"
echo "===================================="
echo

# 检查 PyInstaller 是否已安装
echo "[1/6] 检查 PyInstaller..."
python3 -c "import PyInstaller" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "PyInstaller 未安装，正在安装..."
    python3 -m pip install pyinstaller
    if [ $? -ne 0 ]; then
        echo "安装 PyInstaller 失败！"
        exit 1
    fi
    echo "PyInstaller 安装成功！"
else
    echo "PyInstaller 已安装"
fi
echo

# 清理旧的打包文件
echo "[2/6] 清理旧的打包文件..."
if [ -d "build" ]; then
    rm -rf build
fi

if [ -d "dist" ]; then
    rm -rf dist
fi

if ls *.spec 1> /dev/null 2>&1; then
    rm -f *.spec
fi

# 强制删除可能存在的app文件和dmg文件
if [ -d "dist/Sora2.app" ]; then
    echo "正在强制删除旧的 app 文件..."
    rm -rf dist/Sora2.app
fi

if [ -f "dist/Sora2.dmg" ]; then
    echo "正在强制删除旧的 dmg 文件..."
    rm -f dist/Sora2.dmg
fi

echo "清理完成"
echo

# 开始打包
echo "[3/6] 开始打包..."
echo "正在使用 PyInstaller 打包成 MacOS 应用..."

python3 -m PyInstaller --windowed --onedir \
    --name "Sora2" \
    --hidden-import PyQt5 \
    --hidden-import PyQt5.QtCore \
    --hidden-import PyQt5.QtGui \
    --hidden-import PyQt5.QtWidgets \
    --hidden-import qfluentwidgets \
    --hidden-import requests \
    --hidden-import loguru \
    --hidden-import sqlite3 \
    --collect-all qfluentwidgets \
    --add-data "sora2_up.json:." \
    --add-data "README.md:." \
    --osx-bundle-identifier com.sora2.video.generator \
    --noconfirm main.py

if [ $? -ne 0 ]; then
    echo
    echo "打包失败！请检查错误信息。"
    exit 1
fi

echo
echo "[4/6] 打包完成！"
echo

# 创建 DMG 安装包
echo "[5/6] 创建 DMG 安装包..."
if [ -d "dist/Sora2.app" ]; then
    # 创建临时目录用于制作DMG
    if [ -d "tmp_dmg" ]; then
        rm -rf tmp_dmg
    fi
    mkdir -p tmp_dmg
    
    # 复制应用到临时目录
    cp -R "dist/Sora2.app" "tmp_dmg/"
    
    # 创建软链接到 Applications 文件夹
    ln -s /Applications tmp_dmg/Applications
    
    # 创建 DMG
    hdiutil create -volname "Sora2" \
                   -srcfolder "tmp_dmg" \
                   -ov \
                   -format UDZO \
                   "dist/Sora2.dmg"
    
    # 清理临时目录
    rm -rf tmp_dmg
    
    if [ -f "dist/Sora2.dmg" ]; then
        echo "✓ 成功生成 DMG 安装包: dist/Sora2.dmg"
    else
        echo "✗ 创建 DMG 安装包失败"
    fi
else
    echo "✗ 未找到生成的应用文件，无法创建 DMG"
fi

echo
# 检查生成的文件
echo "[6/6] 检查生成的文件..."
if [ -d "dist/Sora2.app" ] && [ -f "dist/Sora2.dmg" ]; then
    echo "✓ 成功生成: dist/Sora2.app"
    echo "✓ 成功生成: dist/Sora2.dmg"
    echo
    echo "文件信息:"
    ls -lh "dist/Sora2.app"
    ls -lh "dist/Sora2.dmg"
    echo
    echo "===================================="
    echo "打包成功完成！"
    echo "===================================="
    echo
    echo "应用位置: dist/Sora2.app"
    echo "安装包位置: dist/Sora2.dmg"
    echo "您可以将 dist/Sora2.dmg 分发给用户安装"
    echo
elif [ -d "dist/Sora2.app" ]; then
    echo "✓ 成功生成: dist/Sora2.app"
    echo "⚠️  DMG 安装包创建失败"
    echo
    echo "文件信息:"
    ls -lh "dist/Sora2.app"
    echo
    echo "===================================="
    echo "应用打包完成（但DMG创建失败）！"
    echo "===================================="
    echo
    echo "应用位置: dist/Sora2.app"
    echo "您可以将 dist/Sora2.app 复制到 Applications 文件夹中使用"
    echo
else
    echo "✗ 未找到生成的应用文件"
    echo "打包可能失败，请检查上面的错误信息"
fi