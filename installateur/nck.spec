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
    datas=[
        (os.path.join(racine, "exemples"), "exemples"),
        (os.path.join(racine, "docs"), "docs"),
        (os.path.join(racine, "editeurs", "vscode"), os.path.join("editeurs", "vscode")),
        (os.path.join(racine, "LICENSE"), "."),
    ],
    hiddenimports=["nck", "nck.cli", "nck.serveur", "nck.natifs", "nck.documentation", "nck.analyse",
                   "tkinter", "tkinter.ttk", "tkinter.messagebox", "tkinter.filedialog", "tkinter.simpledialog"],
    hookspath=[],
    excludes=["pytest", "unittest", "pydoc", "doctest", "setuptools", "pip", "email", "http", "xml", "pyinstaller"],
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
