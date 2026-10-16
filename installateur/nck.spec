# -*- mode: python ; coding: utf-8 -*-
# Spécification PyInstaller : produit le dossier dist/nck/ contenant nck(.exe) et un Python embarqué.
# Usage : pyinstaller installateur/nck.spec   (depuis la racine du dépôt)
import os, sys

racine = os.path.abspath(os.path.join(SPECPATH, ".."))
sys.path.insert(0, racine)

a = Analysis(
    [os.path.join(racine, "installateur", "lanceur.py")],
    pathex=[racine],
    binaries=[],
    # Les exemples, docs et l'extension VS Code sont copiés à la racine de dist/nck/ par construire.py
    # (PyInstaller 6 placerait les « datas » dans dist/nck/_internal/, invisible pour l'utilisateur).
    datas=[],
    hiddenimports=["nck", "nck.cli", "nck.serveur", "nck.natifs", "nck.documentation", "nck.analyse", "nck.paquets",
                   "tkinter", "tkinter.ttk", "tkinter.messagebox", "tkinter.filedialog", "tkinter.simpledialog"],
    hookspath=[],
    excludes=["pytest", "unittest", "pydoc", "doctest", "setuptools", "pip", "xml", "pyinstaller"],
    noarchive=False,
)
pyz = PYZ(a.pure)

icone = os.path.join(racine, "editeurs", "vscode", "icones", "nck.ico") if sys.platform == "win32" else None

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="nck",
    debug=False,
    strip=False,
    upx=False,
    console=True,
    icon=icone,
)
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name="nck")
