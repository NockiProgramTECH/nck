"""Construit l'exécutable autonome avec PyInstaller, puis l'archive de distribution.

    python installateur/construire.py            → dist/nck/  +  dist/nck-<version>-<os>-<arch>.zip|.tar.gz

Prérequis : pip install pyinstaller
"""
import os
import platform
import shutil
import subprocess
import sys
import tarfile
import zipfile

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RACINE)
from nck import __version__  # noqa: E402


def main() -> int:
    os.chdir(RACINE)
    for d in ("build", os.path.join("dist", "nck")):
        shutil.rmtree(d, ignore_errors=True)
    r = subprocess.run([sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", "installateur/nck.spec"])
    if r.returncode != 0:
        return r.returncode
    dossier = os.path.join("dist", "nck")
    # Fichiers visibles à côté de l'exécutable (utilisés par nck.iss, installer.sh et l'utilisateur).
    for source, cible in (("exemples", "exemples"), ("docs", "docs"),
                          (os.path.join("editeurs", "vscode"), os.path.join("editeurs", "vscode"))):
        shutil.copytree(source, os.path.join(dossier, cible), dirs_exist_ok=True,
                        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    for f in ("LICENSE", "README.md", "CHANGELOG.md"):
        shutil.copy(f, dossier)
    systeme = {"Windows": "windows", "Darwin": "macos", "Linux": "linux"}.get(platform.system(), platform.system().lower())
    arch = {"AMD64": "x64", "x86_64": "x64", "arm64": "arm64", "aarch64": "arm64"}.get(platform.machine(), platform.machine())
    base = f"nck-{__version__}-{systeme}-{arch}"
    if systeme == "windows":
        archive = os.path.join("dist", base + ".zip")
        with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as z:
            for rep, _, fichiers in os.walk(dossier):
                for f in fichiers:
                    chemin = os.path.join(rep, f)
                    z.write(chemin, os.path.relpath(chemin, "dist"))
    else:
        archive = os.path.join("dist", base + ".tar.gz")
        with tarfile.open(archive, "w:gz") as t:
            t.add(dossier, arcname="nck")
    taille = sum(os.path.getsize(os.path.join(r, f)) for r, _, fs in os.walk(dossier) for f in fs) / 1e6
    print(f"\n✓ {dossier}/ ({taille:.1f} Mo)  →  {archive} ({os.path.getsize(archive) / 1e6:.1f} Mo)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
