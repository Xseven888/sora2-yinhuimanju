"""
Fix PyInstaller Qt plugin path encoding issue
Run this before building to create a hook file
"""
import os
import sys
from pathlib import Path

# Create hooks directory if it doesn't exist
hooks_dir = Path(__file__).parent / "hooks"
hooks_dir.mkdir(exist_ok=True)

# Create a hook file to fix Qt plugin path
hook_content = '''"""
PyInstaller hook to fix Qt plugin path encoding issue with Chinese characters
This hook prevents PyInstaller from trying to access Qt plugins with wrong encoding
"""
import os
import sys

# Override the problematic Qt plugin collection
# We'll let PyInstaller handle it normally but skip the encoding-sensitive parts
binaries = []
datas = []
hiddenimports = []

# Try to find and collect Qt plugins manually with proper encoding
try:
    import PyQt5
    pyqt5_path = os.path.dirname(PyQt5.__file__)
    plugins_path = os.path.join(pyqt5_path, 'Qt5', 'plugins')
    
    if os.path.exists(plugins_path):
        # Use absolute path with proper encoding
        plugins_path = os.path.abspath(plugins_path)
        plugins_path = os.path.normpath(plugins_path)
        
        # Collect plugin files
        for root, dirs, files in os.walk(plugins_path):
            for file in files:
                if file.endswith(('.dll', '.so')):
                    src = os.path.join(root, file)
                    rel_path = os.path.relpath(root, plugins_path)
                    if rel_path == '.':
                        dst = 'PyQt5/Qt5/plugins'
                    else:
                        dst = os.path.join('PyQt5', 'Qt5', 'plugins', rel_path).replace('\\\\', '/')
                    datas.append((src, dst))
except Exception as e:
    # If we can't collect plugins, PyInstaller will handle it
    # This prevents the encoding error from crashing the build
    pass
'''

hook_file = hooks_dir / "hook-PyQt5.QtWidgets.py"
with open(hook_file, 'w', encoding='utf-8') as f:
    f.write(hook_content)

print(f"Created hook file: {hook_file}")

