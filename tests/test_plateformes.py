"""Politique des releases : Linux/Windows ; arrêt explicite sur macOS."""

import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

RACINE = Path(__file__).resolve().parents[1]


def test_cibles_release_linux_et_windows():
    workflow = (RACINE / '.github/workflows/release.yml').read_text(encoding='utf-8')
    cibles = [ligne.strip() for ligne in workflow.splitlines() if '- { os:' in ligne]
    assert len(cibles) == 3
    assert any('nom: linux-x64' in ligne for ligne in cibles)
    assert any('nom: linux-arm64' in ligne for ligne in cibles)
    assert any('nom: windows-x64' in ligne for ligne in cibles)
    assert not any('macos-' in ligne for ligne in cibles)
    assert 'installateur/verifier_autonome.py' in workflow
    assert 'installateur\\windows\\nck.iss' in workflow


def test_ci_sans_runner_macos():
    workflow = (RACINE / '.github/workflows/tests.yml').read_text(encoding='utf-8')
    assert 'os: [ubuntu-latest, windows-latest]' in workflow
    assert 'macos-latest' not in workflow


@pytest.mark.skipif(sys.platform == 'win32', reason='test du script POSIX sur un hôte POSIX')
def test_installeur_macos_arrete_avant_reseau_et_modifications(tmp_path):
    shell = shutil.which('sh')
    if shell is None:
        pytest.skip('shell POSIX absent')
    binaires = tmp_path / 'bin'
    binaires.mkdir()
    uname = binaires / 'uname'
    uname.write_text('#!/bin/sh\nprintf "Darwin\\n"\n', encoding='utf-8')
    uname.chmod(0o755)
    prefix = tmp_path / 'installation-existante'
    prefix.mkdir()
    temoin = prefix / 'a-conserver'
    temoin.write_text('installation intacte', encoding='utf-8')
    marqueur = tmp_path / 'reseau-appele'
    curl = binaires / 'curl'
    curl.write_text('#!/bin/sh\n: > "$MARQUEUR_RESEAU"\nexit 99\n', encoding='utf-8')
    curl.chmod(0o755)
    env = {**os.environ, 'PATH': str(binaires), 'HOME': str(tmp_path),
           'NCK_PREFIX': str(prefix), 'MARQUEUR_RESEAU': str(marqueur)}
    resultat = subprocess.run([shell, str(RACINE / 'installateur/installer.sh')],
                              capture_output=True, text=True, encoding='utf-8', env=env, timeout=10)
    assert resultat.returncode == 1
    assert 'releases macOS sont reportées' in resultat.stderr
    assert 'sources' in resultat.stderr
    assert temoin.read_text(encoding='utf-8') == 'installation intacte'
    assert not marqueur.exists()
    assert not (tmp_path / '.local').exists()


def test_documentation_publie_uniquement_depuis_main():
    workflow = (RACINE / '.github/workflows/docs.yml').read_text(encoding='utf-8')
    assert "group: pages-${{ github.ref }}" in workflow
    assert "publier:\n    if: github.ref == 'refs/heads/main'" in workflow
    for action in ('configure-pages@v5', 'upload-pages-artifact@v3'):
        assert f"uses: actions/{action}\n        if: github.ref == 'refs/heads/main'" in workflow
