# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec file para AsistPy Desktop GUI Multiplataforma."""

import os
import sys
from PyInstaller.utils.hooks import collect_submodules, collect_data_files

block_cipher = None

# Recolectar módulos opcionales si están presentes
hiddenimports = [
    "PySide6",
    "PySide6.QtCore",
    "PySide6.QtGui",
    "PySide6.QtWidgets",
    "attendance",
    "attendance.domain",
    "attendance.ports",
    "attendance.application",
    "attendance.adapters",
    "attendance.adapters.gui",
    "attendance.adapters.persistence",
    "attendance.adapters.persistence.sql",
    "attendance.adapters.zk_tcp",
]

# Drivers opcionales de base de datos
for mod in ["psycopg", "pymysql", "pyodbc", "sqlite3", "zk"]:
    try:
        __import__(mod)
        hiddenimports.extend(collect_submodules(mod))
    except ImportError:
        pass

datas = collect_data_files("attendance")

a = Analysis(
    ["../../src/attendance/adapters/gui/__main__.py"],
    pathex=["../../src"],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter", "matplotlib", "scipy", "notebook"],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="AsistPy",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # Ventana GUI sin ventana de terminal negra en Windows
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="AsistPy",
)
