"""
PyInstaller hook to fix Qt plugin path encoding issue with Chinese characters
"""
from PyInstaller.utils.hooks import collect_submodules, collect_data_files
import os
import sys

# Fix for Chinese path encoding issue
def fix_qt_plugin_path():
    """Fix Qt plugin path encoding for Chinese characters"""
    try:
        # Find PyQt5 installation
        for path in sys.path:
            pyqt5_path = os.path.join(path, 'PyQt5')
            if os.path.exists(pyqt5_path):
                plugins_path = os.path.join(pyqt5_path, 'Qt5', 'plugins')
                if os.path.exists(plugins_path):
                    # Use absolute path with proper encoding
                    plugins_path = os.path.abspath(plugins_path)
                    # Normalize the path
                    plugins_path = os.path.normpath(plugins_path)
                    return plugins_path
    except Exception:
        pass
    return None

# Collect PyQt5 binaries and datas
binaries = []
datas = []
hiddenimports = []

# Try to collect Qt plugins with encoding fix
plugin_path = fix_qt_plugin_path()
if plugin_path:
    try:
        # Collect plugin files
        for root, dirs, files in os.walk(plugin_path):
            for file in files:
                src = os.path.join(root, file)
                rel_path = os.path.relpath(root, plugin_path)
                if rel_path == '.':
                    dst = f'PyQt5/Qt5/plugins/{file}'
                else:
                    dst = f'PyQt5/Qt5/plugins/{rel_path}/{file}'
                datas.append((src, os.path.dirname(dst)))
    except Exception as e:
        print(f"Warning: Could not collect Qt plugins: {e}")

