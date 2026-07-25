# -*- mode: python ; coding: utf-8 -*-
"""Spécification PyInstaller — exécutable Windows autonome.

Construction (sur un poste Windows, Python 3.12) :

    py -3.12 -m pip install -r requirements.txt pyinstaller
    py -3.12 -m PyInstaller CalculateurTPT.spec --noconfirm

Produit `dist/CalculateurTPT.exe`, lançable par simple double-clic depuis un
partage réseau ou une clé USB, sans droits administrateur, sans Microsoft Office
et sans accès Internet.
"""

from pathlib import Path

RACINE = Path(SPECPATH)

# Le template Excel et les polices de repli sont embarqués dans l'exécutable.
donnees = [
    (str(RACINE / "tpt_app" / "export" / "template" / "attestation_template.xlsx"),
     "tpt_app/export/template"),
    (str(RACINE / "tpt_app" / "export" / "assets"), "tpt_app/export/assets"),
]

# PySide6 embarque bien plus de modules que nécessaire : on écarte ceux qui
# alourdissent inutilement le binaire sans servir à l'application.
exclusions = [
    "PySide6.QtWebEngineCore", "PySide6.QtWebEngineWidgets", "PySide6.QtWebEngineQuick",
    "PySide6.QtQuick", "PySide6.QtQuick3D", "PySide6.QtQml", "PySide6.Qt3DCore",
    "PySide6.QtMultimedia", "PySide6.QtMultimediaWidgets", "PySide6.QtCharts",
    "PySide6.QtDataVisualization", "PySide6.QtBluetooth", "PySide6.QtNetworkAuth",
    "PySide6.QtPositioning", "PySide6.QtSerialPort", "PySide6.QtTest",
    "PySide6.QtSql", "PySide6.QtOpenGL", "PySide6.QtOpenGLWidgets",
    "tkinter", "unittest", "pydoc", "doctest", "pytest", "numpy", "matplotlib",
]

analyse = Analysis(
    ["lancer.py"],
    pathex=[str(RACINE)],
    binaries=[],
    datas=donnees,
    hiddenimports=["tpt_app.ui.pages", "tpt_app.ui.widgets"],
    hookspath=[],
    runtime_hooks=[],
    excludes=exclusions,
    noarchive=False,
)

pyz = PYZ(analyse.pure)

exe = EXE(
    pyz,
    analyse.scripts,
    analyse.binaries,
    analyse.datas,
    [],
    name="CalculateurTPT",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    runtime_tmpdir=None,
    console=False,               # --windowed : aucune console noire
    disable_windowed_traceback=False,
    icon=str(RACINE / "tpt_app" / "export" / "assets" / "calculateur_tpt.ico")
    if (RACINE / "tpt_app" / "export" / "assets" / "calculateur_tpt.ico").exists()
    else None,
    version=None,
)
