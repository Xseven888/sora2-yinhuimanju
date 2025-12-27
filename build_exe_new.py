"""
全新的打包脚本 - 更可靠的方式
使用spec文件方式，更好的错误处理
"""
import sys
import os
import shutil
from pathlib import Path

# 设置编码
os.environ['PYTHONIOENCODING'] = 'utf-8'
os.environ['PYTHONUTF8'] = '1'

def create_hook_file():
    """创建hook文件来修复路径编码问题"""
    script_dir = Path(__file__).parent
    hooks_dir = script_dir / 'hooks'
    hooks_dir.mkdir(exist_ok=True)
    
    # 需要覆盖的 PyQt5 hook 列表（所有可能触发路径编码问题的模块）
    hook_modules = [
        'PyQt5.QtWidgets',
        'PyQt5.QtGui',
        'PyQt5.QtCore',
        'PyQt5.QtMultimedia',
        'PyQt5.QtMultimediaWidgets',
        'PyQt5.QtNetwork',
        'PyQt5.QtSql',
        'PyQt5.QtSvg',
        'PyQt5.QtXml',
        'PyQt5.QtPrintSupport',
        'PyQt5.QtOpenGL',
        'PyQt5.QtQml',
        'PyQt5.QtQuick',
        'PyQt5.QtQuickWidgets',
        'PyQt5.QtTest',
        'PyQt5.QtBluetooth',
        'PyQt5.QtNfc',
        'PyQt5.QtPositioning',
        'PyQt5.QtLocation',
        'PyQt5.QtSensors',
        'PyQt5.QtSerialPort',
        'PyQt5.QtWebSockets',
    ]
    
    hook_content = '''"""
Hook file to fix PyQt5 path encoding issue
This hook overrides the default PyInstaller hook to avoid path encoding problems
"""
import os
import sys

# Override the problematic hook behavior
# Return empty lists to prevent PyInstaller from trying to access the problematic path
hiddenimports = []
binaries = []
datas = []

# We'll collect Qt plugins in the spec file instead
# This avoids the encoding issue in PyInstaller's hook system
'''
    
    created_files = []
    for module in hook_modules:
        hook_file = hooks_dir / f'hook-{module}.py'
        with open(hook_file, 'w', encoding='utf-8') as f:
            f.write(hook_content)
        created_files.append(hook_file.name)
    
    print(f"✓ Created {len(created_files)} hook files: {', '.join(created_files)}")
    return hooks_dir

def create_spec_file():
    """创建spec文件"""
    script_dir = Path(__file__).parent
    
    # 检查图标
    icon_path = None
    if (script_dir / 'logo.ico').exists():
        icon_path = str(script_dir / 'logo.ico')
    elif (script_dir / 'logo.png').exists():
        icon_path = str(script_dir / 'logo.png')
    
    # 检查hooks目录
    hooks_dir = script_dir / 'hooks'
    hookspath_line = "    hookspath=[],"
    if hooks_dir.exists():
        # 使用相对路径，避免编码问题
        hookspath_line = f"    hookspath=['hooks'],"
    
    # 构建spec文件内容
    icon_line = ""
    if icon_path:
        icon_line = f"    icon='{icon_path}',"
    
    # 检查 logo.ico 是否存在
    logo_ico_line = ""
    if (script_dir / 'logo.ico').exists():
        logo_ico_line = "    ('logo.ico', '.'),"
    
    spec_content = f'''# -*- mode: python ; coding: utf-8 -*-
import sys
import os

# 设置编码
os.environ['PYTHONIOENCODING'] = 'utf-8'
os.environ['PYTHONUTF8'] = '1'

block_cipher = None

# 收集所有数据文件
datas = [
    ('sora2_up.json', '.'),
    ('README.md', '.'),
    ('logo.png', '.'),
{logo_ico_line}
]

# 收集所有二进制文件
binaries = []

# 隐藏导入
hiddenimports = [
    'PyQt5',
    'PyQt5.QtCore',
    'PyQt5.QtGui',
    'PyQt5.QtWidgets',
    'PyQt5.QtMultimedia',
    'PyQt5.QtMultimediaWidgets',
    'PyQt5.QtMultimedia.QMediaPlayer',
    'PyQt5.QtMultimedia.QMediaContent',
    'PyQt5.QtSql',
    'PyQt5.sip',
    'qfluentwidgets',
    'qfluentwidgets.components',
    'requests',
    'loguru',
    'sqlite3',
    'imageio',
    'imageio_ffmpeg',
    'database_manager',
    'sora_client',
    'constants',
    'ui',
    'ui.settings_interface',
    'ui.task_list_widget',
    'ui.voice_library_interface',
    'ui.episode_detail_widget',
    'ui.project_detail_widget',
    'components',
    'threads',
    'utils',
    'models',
]

    # 分析主程序
a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
''' + hookspath_line + '''
    hooksconfig={},
    runtime_hooks=[],
    excludes=['matplotlib', 'numpy.distutils', 'PyQt5.QtWebEngine', 'PyQt5.QtWebEngineWidgets'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# 收集PyQt5的Qt插件（特别是platforms插件，必需）
# 在单文件模式下，EXE 需要 TOC 格式 (dest, src, typecode)
try:
    import PyQt5
    pyqt5_path = os.path.dirname(PyQt5.__file__)
    
    # 创建 TOC 格式的数据列表
    pyqt5_toc = []
    
    # 收集platforms插件（必需）
    platforms_path = os.path.join(pyqt5_path, 'Qt5', 'plugins', 'platforms')
    platforms_path = os.path.abspath(platforms_path)
    platforms_path = os.path.normpath(platforms_path)
    
    if os.path.exists(platforms_path):
        for file in os.listdir(platforms_path):
            if file.endswith('.dll'):
                src = os.path.join(platforms_path, file)
                src = os.path.abspath(src)
                # 单文件模式下，插件需要放在根目录的 plugins/platforms 下
                # TOC 格式: (dest, src, typecode)
                dest = f'plugins/platforms/{file}'
                pyqt5_toc.append((dest, src, 'DATA'))
                print(f"  添加插件: {file} -> {dest}")
    
    # 收集其他常用插件（包括音频插件）
    plugin_dirs = ['styles', 'imageformats', 'audio', 'mediaservice']
    for plugin_dir in plugin_dirs:
        plugin_path = os.path.join(pyqt5_path, 'Qt5', 'plugins', plugin_dir)
        plugin_path = os.path.abspath(plugin_path)
        plugin_path = os.path.normpath(plugin_path)
        if os.path.exists(plugin_path):
            for file in os.listdir(plugin_path):
                if file.endswith('.dll'):
                    src = os.path.join(plugin_path, file)
                    src = os.path.abspath(src)
                    # 单文件模式下，插件需要放在根目录的 plugins 下
                    dest = f'plugins/{plugin_dir}/{file}'
                    pyqt5_toc.append((dest, src, 'DATA'))
    
    if pyqt5_toc:
        # 使用 TOC 类来确保格式正确
        from PyInstaller.building.datastruct import TOC
        pyqt5_toc_obj = TOC(pyqt5_toc)
        a.datas = a.datas + pyqt5_toc_obj
        print(f"Collected {len(pyqt5_toc)} Qt plugin files")
    else:
        print("Warning: No Qt plugins found!")
except Exception as e:
    print("Warning: Could not collect PyQt5 plugins: " + str(e))
    import traceback
    traceback.print_exc()

# 不再手动收集文件，让 PyInstaller 自动处理
# 这样可以避免数据格式问题
# hiddenimports 中已经包含了必要的模块，PyInstaller 会自动收集相关文件

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='Sora2',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
''' + icon_line + '''
)

# 单文件模式，不需要 COLLECT
# 所有文件都打包到 exe 中
'''
    
    spec_file = script_dir / 'Sora2.spec'
    with open(spec_file, 'w', encoding='utf-8') as f:
        f.write(spec_content)
    
    print(f"✓ Created spec file: {spec_file}")
    return spec_file

def build():
    """执行打包"""
    script_dir = Path(__file__).parent
    os.chdir(script_dir)
    
    print("=" * 60)
    print("Sora2 程序打包工具")
    print("=" * 60)
    print()
    
    # 清理旧文件
    print("[1/4] 清理旧文件...")
    for dir_name in ['build', 'dist']:
        dir_path = script_dir / dir_name
        if dir_path.exists():
            shutil.rmtree(dir_path)
            print(f"  删除: {dir_name}/")
    
    spec_files = list(script_dir.glob('*.spec'))
    for spec_file in spec_files:
        if spec_file.name != 'Sora2.spec':
            spec_file.unlink()
            print(f"  删除: {spec_file.name}")
    print("✓ 清理完成")
    print()
    
    # 创建hook文件
    print("[2/4] 创建hook文件...")
    hooks_dir = create_hook_file()
    print()
    
    # 创建spec文件
    print("[3/4] 创建spec文件...")
    spec_file = create_spec_file()
    print()
    
    # 执行打包
    print("[4/4] 开始打包（这可能需要几分钟）...")
    import PyInstaller.__main__
    
    try:
        PyInstaller.__main__.run([
            str(spec_file),
            '--clean',
            '--noconfirm',
        ])
        print("✓ 打包完成")
        print()
    except Exception as e:
        print(f"✗ 打包失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # 检查结果（单文件模式）
    print("[5/5] 检查打包结果...")
    exe_path = script_dir / 'dist' / 'Sora2.exe'
    
    if exe_path.exists():
        size_mb = exe_path.stat().st_size / 1024 / 1024
        print(f"✓ 成功生成: {exe_path}")
        print(f"  文件大小: {size_mb:.2f} MB")
        print()
        print("=" * 60)
        print("打包成功！")
        print("=" * 60)
        print()
        print(f"可执行文件位置: {exe_path}")
        print()
        print("重要提示：")
        print("  1. 这是无控制台版本（Windows 窗口程序）")
        print("  2. 如果程序无法启动，请检查是否有错误提示窗口")
        print("  3. 运行命令: dist\\Sora2.exe")
        print("  4. 如果需要调试版本（带控制台），可以将 build_exe_new.py 中的 console=False 改为 console=True")
        print()
        return True
    else:
        print(f"✗ 未找到生成的文件")
        print(f"  查找位置: {script_dir / 'dist'}")
        print()
        print("请检查上面的错误信息")
        return False

if __name__ == '__main__':
    success = build()
    sys.exit(0 if success else 1)

