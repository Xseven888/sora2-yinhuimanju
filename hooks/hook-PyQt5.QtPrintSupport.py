"""
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
