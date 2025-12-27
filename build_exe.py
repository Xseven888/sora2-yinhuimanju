"""
Build executable using PyInstaller with proper encoding handling
"""
import sys
import os
from pathlib import Path

# Set encoding
os.environ['PYTHONIOENCODING'] = 'utf-8'
os.environ['PYTHONUTF8'] = '1'

# Import PyInstaller
import PyInstaller.__main__

# Get script directory
script_dir = Path(__file__).parent
os.chdir(script_dir)

# Build arguments
# Use --onedir first for easier debugging, can change to --onefile later
args = [
    '--onedir',  # Changed to onedir for easier debugging
    '--windowed',
    '--name', 'Sora2',
    '--hidden-import', 'PyQt5',
    '--hidden-import', 'PyQt5.QtCore',
    '--hidden-import', 'PyQt5.QtGui',
    '--hidden-import', 'PyQt5.QtWidgets',
    '--hidden-import', 'PyQt5.QtMultimedia',
    '--hidden-import', 'PyQt5.QtMultimediaWidgets',
    '--hidden-import', 'PyQt5.QtSql',
    '--hidden-import', 'PyQt5.sip',
    '--hidden-import', 'qfluentwidgets',
    '--hidden-import', 'qfluentwidgets.components',
    '--hidden-import', 'requests',
    '--hidden-import', 'loguru',
    '--hidden-import', 'sqlite3',
    '--hidden-import', 'imageio',
    '--hidden-import', 'imageio_ffmpeg',
    '--hidden-import', 'database_manager',
    '--hidden-import', 'sora_client',
    '--hidden-import', 'constants',
    '--hidden-import', 'ui',
    '--hidden-import', 'ui.settings_interface',
    '--hidden-import', 'ui.task_list_widget',
    '--hidden-import', 'ui.voice_library_interface',
    '--hidden-import', 'components',
    '--hidden-import', 'threads',
    '--hidden-import', 'utils',
    '--collect-all', 'qfluentwidgets',
    '--collect-all', 'imageio_ffmpeg',
    '--collect-all', 'PyQt5',
    '--exclude-module', 'PyQt5.QtWebEngine',
    '--exclude-module', 'PyQt5.QtWebEngineWidgets',
    '--exclude-module', 'matplotlib',
    '--exclude-module', 'numpy.distutils',
    '--add-data', 'sora2_up.json;.',
    '--add-data', 'README.md;.',
    '--add-data', 'logo.png;.',
    '--noconfirm',
]

# Add hooks directory if it exists
hooks_dir = script_dir / 'hooks'
if hooks_dir.exists() and (hooks_dir / 'hook-PyQt5.QtWidgets.py').exists():
    args.insert(0, '--additional-hooks-dir')
    args.insert(1, str(hooks_dir))

# Add icon if it exists
logo_ico = script_dir / 'logo.ico'
logo_png = script_dir / 'logo.png'
if logo_ico.exists():
    args.extend(['--icon', str(logo_ico)])
elif logo_png.exists():
    args.extend(['--icon', str(logo_png)])
    print("Note: Using PNG icon. ICO format is recommended for better compatibility.")

# Add main script
args.append('main.py')

# Run PyInstaller
print("Starting PyInstaller build...")
print(f"Arguments: {' '.join(args)}")
print()

try:
    PyInstaller.__main__.run(args)
    print("\nBuild completed!")
    
    # Check if exe was created
    exe_path = script_dir / 'dist' / 'Sora2' / 'Sora2.exe'
    if exe_path.exists():
        print(f"\n✓ Executable created: {exe_path}")
        print(f"  Size: {exe_path.stat().st_size / 1024 / 1024:.2f} MB")
        print(f"\nTo test the executable, run:")
        print(f"  {exe_path}")
    else:
        print(f"\n⚠ Warning: Executable not found at expected location: {exe_path}")
        print("Please check the build output above for errors.")
        
except Exception as e:
    print(f"\nBuild failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

