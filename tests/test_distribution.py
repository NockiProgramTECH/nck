"""Préparation des paquets, diagnostics et scénario utilisé par la release CI."""

import json
import os
from pathlib import Path
import shutil
import sys
import zipfile

import pytest

from installateur import construire, verifier_autonome
from nck import paquets as p
from outils import preparer_paquet as outil

RACINE = Path(__file__).resolve().parents[1]


@pytest.fixture
def source(tmp_path):
    dossier = tmp_path / 'source'
    shutil.copytree(RACINE / 'exemples/paquets/maths-plus', dossier)
    return dossier


def test_archive_reproductible_et_installable(source, tmp_path, monkeypatch, capsys):
    sortie = tmp_path / 'registre'
    archive, index = outil.preparer(source, sortie)
    avant = archive.read_bytes(), index.read_bytes()
    # Les dates, droits et fichiers générés ne doivent pas changer l'archive.
    os.utime(source / 'module.nck', (1700000000, 1700000000))
    (source / 'nck_modules/dechet').mkdir(parents=True)
    (source / 'nck_modules/dechet/code.py').write_text('erreur')
    (source / '.git').mkdir()
    (source / '.git/config').write_text('ne pas distribuer')
    outil.preparer(source, sortie)
    assert (archive.read_bytes(), index.read_bytes()) == avant
    with zipfile.ZipFile(archive) as z:
        assert sorted(z.namelist()) == ['README.md', 'module.nck', 'paquet.json']
        assert all(info.date_time == (1980, 1, 1, 0, 0, 0) for info in z.infolist())
    projet = tmp_path / 'projet'
    projet.mkdir()
    monkeypatch.chdir(projet)
    p.initialiser()
    assert p.installer('maths-plus', str(index)) == {'maths-plus': '1.0.0'}
    assert outil.main([str(source), '--sortie', str(sortie)]) == 0
    assert 'Aucun fichier publié en ligne' in capsys.readouterr().out


def test_preparation_ne_remplace_pas_version(source, tmp_path):
    sortie = tmp_path / 'registre'
    archive, index = outil.preparer(source, sortie)
    avant = archive.read_bytes(), index.read_bytes()
    (source / 'module.nck').write_text('constante X = 2\n')
    with pytest.raises(p.ErreurPaquet, match='augmentez la version'):
        outil.preparer(source, sortie)
    assert (archive.read_bytes(), index.read_bytes()) == avant


def test_index_fusionne_et_url_https(source, tmp_path):
    sortie = tmp_path / 'registre'
    _, index = outil.preparer(source, sortie, 'https://exemple.org/paquets/')
    catalogue = p.lire_json(index)
    assert catalogue['maths-plus']['versions']['1.0.0']['url'] == 'https://exemple.org/paquets/maths-plus-1.0.0.zip'
    m = p.lire_json(source / p.MANIFESTE)
    m['version'] = '1.1.0'
    (source / p.MANIFESTE).write_text(json.dumps(m))
    outil.preparer(source, sortie, 'https://exemple.org/paquets/')
    assert set(p.lire_json(index)['maths-plus']['versions']) == {'1.0.0', '1.1.0'}


@pytest.mark.parametrize('url', ['http://example.org', 'file:///tmp', 'https://',
                                  'https://exemple.org/a?b=1', 'https://exemple.org/#f',
                                  'https://user:secret@exemple.org'])
def test_url_publication_invalide(source, tmp_path, url):
    with pytest.raises(p.ErreurPaquet, match='URL HTTPS'):
        outil.preparer(source, tmp_path / 'sortie', url)


def test_sortie_dans_source_refusee(source):
    with pytest.raises(p.ErreurPaquet, match='hors du paquet source'):
        outil.preparer(source, source / 'sortie')


def test_python_et_syntaxe_invalides_refuses(source, tmp_path):
    (source / 'script.py').write_text('raise Exception("ne jamais executer")')
    with pytest.raises(p.ErreurPaquet, match='100 % NCK'):
        outil.preparer(source, tmp_path / 'registre')
    (source / 'script.py').unlink()
    (source / 'module.nck').write_text('variable =\n')
    with pytest.raises(p.ErreurPaquet, match='source NCK invalide'):
        outil.preparer(source, tmp_path / 'registre')
    assert not (tmp_path / 'registre').exists()


def test_liens_source_refuses(source, tmp_path):
    lien = source / 'lien.nck'
    try:
        lien.symlink_to(source / 'module.nck')
    except OSError:
        pytest.skip('création de liens symboliques non autorisée sur cette plateforme')
    with pytest.raises(p.ErreurPaquet, match='lien symbolique interdit'):
        outil.preparer(source, tmp_path / 'registre')


def test_index_invalide_preserve(source, tmp_path):
    sortie = tmp_path / 'registre'
    sortie.mkdir()
    index = sortie / 'index.json'
    index.write_text('{"maths-plus": {"versions": []}}')
    with pytest.raises(p.ErreurPaquet, match="entrée d'index invalide"):
        outil.preparer(source, sortie)
    assert index.read_text() == '{"maths-plus": {"versions": []}}'
    assert not list(sortie.glob('*.zip'))


def test_preparation_cli_erreur(source, tmp_path, capsys):
    assert outil.main([str(source), '--sortie', str(source / 'sortie')]) == 1
    assert 'hors du paquet source' in capsys.readouterr().err


def test_preflight_epargne_anciens_artefacts(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(construire, 'RACINE', str(tmp_path))
    monkeypatch.setattr(construire, 'bibliotheque_python', lambda: None)
    (tmp_path / 'build').mkdir()
    temoin = tmp_path / 'build/ancien'
    temoin.write_text('conserver')
    assert construire.main() == 1
    assert temoin.read_text() == 'conserver'
    assert 'bibliothèque partagée' in capsys.readouterr().err


def test_preflight_pyinstaller_absent(monkeypatch, capsys):
    def absent():
        raise ImportError('PyInstaller')
    monkeypatch.setattr(construire, 'bibliotheque_python', absent)
    assert not construire.verifier_prerequis()
    assert 'pip install pyinstaller' in capsys.readouterr().err


def test_preflight_bibliotheque_presente(tmp_path, monkeypatch):
    bibliotheque = tmp_path / 'libpython.so'
    bibliotheque.write_bytes(b'exemple')
    monkeypatch.setattr(construire, 'bibliotheque_python', lambda: str(bibliotheque))
    assert construire.verifier_prerequis()


def test_scenario_release_sur_moteur_source(tmp_path, capsys):
    distribution = tmp_path / 'distribution'
    shutil.copytree(RACINE / 'exemples/paquets', distribution / 'exemples/paquets')
    # Lanceur source explicite pour tester le scénario même sans PyInstaller/libpython.
    lanceur = (f'import sys; sys.path.insert(0, {str(RACINE)!r}); '
               'from nck.cli import main; sys.exit(main())')
    verifier_autonome.verifier([sys.executable, '-c', lanceur], distribution, autonome=False)
    assert 'Validation réussie' in capsys.readouterr().out


def test_validation_distribution_incomplete(tmp_path):
    with pytest.raises(verifier_autonome.ErreurValidation, match='exemple de paquet manquant'):
        verifier_autonome.verifier(['absent'], tmp_path)


def test_validation_executable_absent(tmp_path, capsys):
    assert verifier_autonome.main([str(tmp_path / 'absent')]) == 1
    assert 'exécutable introuvable' in capsys.readouterr().err
