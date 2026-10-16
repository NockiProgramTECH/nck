"""Tests du gestionnaire : registre local réel, réseau simulé, imports et CLI."""

import hashlib
import io
import json
from pathlib import Path
import shutil
import stat
import zipfile

import pytest

from nck import ErreurType, compiler_source, executer_source
from nck.cli import main
from nck import paquets as p


def ecrire_json(chemin, objet):
    chemin.parent.mkdir(parents=True, exist_ok=True)
    chemin.write_text(json.dumps(objet), encoding='utf-8')


def manifeste(nom='demo', v='1.0.0', deps=None, entree='module.nck'):
    return {'nom': nom, 'version': v, 'point_entree': entree, 'dependances': deps or {}}


@pytest.fixture
def projet(tmp_path, monkeypatch):
    racine = tmp_path / 'projet'
    racine.mkdir()
    monkeypatch.chdir(racine)
    # Ne jamais consulter les paquets du compte qui lance les tests.
    monkeypatch.setattr(Path, 'home', classmethod(lambda cls: tmp_path / 'maison'))
    p.initialiser()
    return racine


@pytest.fixture
def registre(tmp_path):
    dossier = tmp_path / 'registre'
    dossier.mkdir()
    index = dossier / 'index.json'
    catalogue = {}

    def ajouter(nom='demo', v='1.0.0', deps=None, fichiers=None, entree='module.nck'):
        archive = dossier / f'{nom}-{v}.zip'
        with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as z:
            z.writestr('paquet.json', json.dumps(manifeste(nom, v, deps, entree)))
            z.writestr(entree, 'fonction doubler(n: entier) -> entier: retourner n * 2\n')
            for chemin, texte in (fichiers or {}).items():
                z.writestr(chemin, texte)
        catalogue.setdefault(nom, {'versions': {}})['versions'][v] = {
            'url': archive.name, 'sha256': hashlib.sha256(archive.read_bytes()).hexdigest()}
        ecrire_json(index, catalogue)
        return archive

    ajouter.index = index
    ajouter.catalogue = catalogue
    return ajouter


@pytest.mark.parametrize('v,c,attendu', [
    ('1.2.3', '*', True), ('1.2.3', '1.2.3', True), ('1.2.4', '1.2.3', False),
    ('1.9.0', '^1.2', True), ('2.0.0', '^1.2', False), ('1.1.9', '^1.2', False),
    ('1.0.0', '^1', True), ('0.2.5', '^0.2', True), ('0.3.0', '^0.2', False),
    ('0.0.4', '^0.0.3', False), ('0.0.3', '^0.0.3', True),
    ('1.2.9', '~1.2', True), ('1.3.0', '~1.2', False), ('1.9.0', '~1', True),
])
def test_contraintes(v, c, attendu):
    assert p.accepte(v, c) == attendu


@pytest.mark.parametrize('contrainte', ['', 'latest', '>=1.0', '^', '1.0', '01.2.3', '1.0.0-beta', 'v1.2.3'])
def test_contraintes_invalides(contrainte):
    with pytest.raises(p.ErreurPaquet):
        p.accepte('1.0.0', contrainte)


def test_init_non_destructif(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / 'module.nck').write_text('ecrire(42)', encoding='utf-8')
    p.initialiser('mon-projet')
    assert p.lire_json(tmp_path / 'paquet.json')['nom'] == 'mon-projet'
    assert (tmp_path / 'module.nck').read_text() == 'ecrire(42)'
    with pytest.raises(p.ErreurPaquet, match='existe déjà'):
        p.initialiser('autre')


def test_init_nom_invalide(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with pytest.raises(p.ErreurPaquet, match='nom de paquet invalide'):
        p.initialiser('../intrus')
    assert not (tmp_path / 'paquet.json').exists()


def test_installation_import_et_verrou(projet, registre, capsys, monkeypatch):
    registre('maths-plus', '1.2.0', entree='src/maths.nck',
             fichiers={'src/outils.nck': 'constante X = 3\n'})
    assert main(['installer', 'maths-plus', '--index', str(registre.index)]) == 0
    capsys.readouterr()
    assert p.lire_json(projet / p.MANIFESTE)['dependances'] == {'maths-plus': '^1.2.0'}
    assert p.lire_json(projet / p.VERROU)['paquets']['maths-plus']['version'] == '1.2.0'
    sous = projet / 'src'
    sous.mkdir()
    monkeypatch.chdir(sous)
    source = 'importer "maths-plus"\necrire(maths_plus.doubler(21))\n'
    compiler_source(source, str(sous / 'main.nck'))
    executer_source(source, str(sous / 'main.nck'))
    assert capsys.readouterr().out == '42\n'
    assert p.lister() == ['maths-plus@1.2.0 (directe)']


def test_dependances_transitives_et_imports_relatifs(projet, registre, capsys):
    registre('base', fichiers={'module.nck.bak.txt': 'note'})
    archive = registre('haut', deps={'base': '^1'}, fichiers={
        'util.nck': 'depuis "base" importer doubler\nfonction quadrupler(x: entier) -> entier: retourner doubler(doubler(x))\n'})
    # Le point d'entrée peut importer un fichier relatif au paquet.
    with zipfile.ZipFile(archive, 'w') as z:
        z.writestr('paquet.json', json.dumps(manifeste('haut', deps={'base': '^1'})))
        z.writestr('module.nck', 'depuis "util.nck" importer quadrupler\n')
        z.writestr('util.nck', 'depuis "base" importer doubler\nfonction quadrupler(x: entier) -> entier: retourner doubler(doubler(x))\n')
    registre.catalogue['haut']['versions']['1.0.0']['sha256'] = hashlib.sha256(archive.read_bytes()).hexdigest()
    ecrire_json(registre.index, registre.catalogue)
    assert p.installer('haut', str(registre.index)) == {'base': '1.0.0', 'haut': '1.0.0'}
    executer_source('depuis "haut" importer quadrupler\necrire(quadrupler(4))', str(projet / 'main.nck'))
    assert capsys.readouterr().out == '16\n'
    assert p.lister() == ['base@1.0.0 (transitive)', 'haut@1.0.0 (directe)']


def test_verrou_reproductible_sans_index(projet, registre, monkeypatch):
    registre('demo', '1.0.0')
    p.installer('demo', str(registre.index))
    avant = (projet / p.VERROU).read_bytes()
    registre('demo', '1.1.0')
    registre.index.unlink()
    shutil.rmtree(projet / 'nck_modules')
    monkeypatch.setenv('NCK_INDEX', str(registre.index))
    assert p.installer() == {'demo': '1.0.0'}
    assert (projet / p.VERROU).read_bytes() == avant


def test_nouvelle_contrainte_remplace_pin(projet, registre):
    registre('demo', '1.0.0')
    p.installer('demo', str(registre.index))
    registre('demo', '2.0.0')
    assert p.installer('demo@^2', str(registre.index)) == {'demo': '2.0.0'}


def test_resolution_reessaie_version_anterieure(projet, registre):
    registre('base', '1.0.0')
    registre('base', '2.0.0')
    registre('haut', '2.0.0', deps={'base': '^2'})
    registre('haut', '1.0.0', deps={'base': '^1'})
    m = p.lire_json(projet / p.MANIFESTE)
    m['dependances'] = {'haut': '*', 'base': '^1'}
    ecrire_json(projet / p.MANIFESTE, m)
    assert p.installer(index=str(registre.index)) == {'base': '1.0.0', 'haut': '1.0.0'}


def test_conflit_preserve_installation(projet, registre):
    registre('base', '1.0.0')
    p.installer('base', str(registre.index))
    avant = {n: (projet / n).read_bytes() for n in (p.MANIFESTE, p.VERROU)}
    registre('haut', deps={'base': '^2'})
    with pytest.raises(p.ErreurPaquet, match='incompatibles'):
        p.installer('haut', str(registre.index))
    assert all((projet / n).read_bytes() == contenu for n, contenu in avant.items())
    assert (projet / 'nck_modules/base/module.nck').is_file()
    assert not list(projet.glob('.nck-install-*'))


def test_desinstallation_elague_transitives(projet, registre):
    registre('base')
    registre('haut', deps={'base': '^1'})
    p.installer('haut', str(registre.index))
    assert p.installer(retirer='haut') == {}
    assert not list((projet / 'nck_modules').iterdir())
    assert p.lire_json(projet / p.MANIFESTE)['dependances'] == {}
    with pytest.raises(p.ErreurPaquet, match='dépendance directe'):
        p.installer(retirer='base')


def test_desinstaller_conserve_partage(projet, registre):
    registre('base')
    registre('haut', deps={'base': '^1'})
    registre('autre', deps={'base': '^1'})
    p.installer('haut', str(registre.index))
    p.installer('autre', str(registre.index))
    assert p.installer(retirer='haut') == {'autre': '1.0.0', 'base': '1.0.0'}


def test_sha_incorrect_pas_de_modifications(projet, registre):
    archive = registre()
    archive.write_bytes(b'archive alteree')
    with pytest.raises(p.ErreurPaquet, match='SHA-256 incorrect'):
        p.installer('demo', str(registre.index))
    assert not (projet / 'nck_modules').exists()
    assert not (projet / p.VERROU).exists()
    assert p.lire_json(projet / p.MANIFESTE)['dependances'] == {}


@pytest.mark.parametrize('chemin', ['../intrus.nck', '/intrus.nck', 'a/../../intrus.nck',
                                     'a\\intrus.nck', 'C:/intrus.nck', 'a//intrus.nck', 'module.nck\x00cache'])
def test_zip_traversee_interdite(tmp_path, chemin):
    contenu = io.BytesIO()
    with zipfile.ZipFile(contenu, 'w') as z:
        # Ne pas laisser ZipInfo normaliser la fixture sur l'hôte Windows.
        info = zipfile.ZipInfo('nom-provisoire')
        info.filename = info.orig_filename = chemin
        z.writestr(info, 'ecrire(1)')
    with pytest.raises(p.ErreurPaquet, match='chemin de paquet interdit'):
        p._extraire(contenu.getvalue(), tmp_path / 'extraction')
    assert not (tmp_path / 'intrus.nck').exists()


def test_zip_symlink_interdit(tmp_path):
    contenu = io.BytesIO()
    with zipfile.ZipFile(contenu, 'w') as z:
        lien = zipfile.ZipInfo('module.nck')
        lien.create_system = 3
        lien.external_attr = (stat.S_IFLNK | 0o777) << 16
        z.writestr(lien, '/etc/passwd')
    with pytest.raises(p.ErreurPaquet, match='liens'):
        p._extraire(contenu.getvalue(), tmp_path)


def test_zip_python_interdit(projet, registre):
    registre(fichiers={'code.py': 'print("pas execute")'})
    with pytest.raises(p.ErreurPaquet, match='100 % NCK'):
        p.installer('demo', str(registre.index))


def test_zip_invalide_et_limites(tmp_path, monkeypatch):
    with pytest.raises(p.ErreurPaquet, match='ZIP invalide'):
        p._extraire(b'pas un zip', tmp_path)
    contenu = io.BytesIO()
    with zipfile.ZipFile(contenu, 'w') as z:
        z.writestr('module.nck', 'x' * 30)
    monkeypatch.setattr(p, 'MAX_EXTRAIT', 20)
    with pytest.raises(p.ErreurPaquet, match='volumineuse'):
        p._extraire(contenu.getvalue(), tmp_path)


def test_archive_identite_et_entree(projet, registre):
    archive = registre()
    with zipfile.ZipFile(archive, 'w') as z:
        z.writestr('paquet.json', json.dumps(manifeste('intrus')))
        z.writestr('module.nck', '')
    registre.catalogue['demo']['versions']['1.0.0']['sha256'] = hashlib.sha256(archive.read_bytes()).hexdigest()
    ecrire_json(registre.index, registre.catalogue)
    with pytest.raises(p.ErreurPaquet, match='identité'):
        p.installer('demo', str(registre.index))


@pytest.mark.parametrize('entree', ['../main.nck', 'main.py', '/main.nck'])
def test_point_entree_interdit(entree):
    with pytest.raises(p.ErreurPaquet):
        p.valider_manifeste(manifeste(entree=entree))


def test_rollback_si_ecriture_echoue(projet, registre, monkeypatch):
    registre()
    p.installer('demo', str(registre.index))
    avant = (projet / p.MANIFESTE).read_bytes(), (projet / p.VERROU).read_bytes()
    registre('autre')
    vrai_replace = p.os.replace

    def echouer(source, cible):
        if Path(cible).name == p.VERROU:
            raise OSError('disque indisponible')
        return vrai_replace(source, cible)

    monkeypatch.setattr(p.os, 'replace', echouer)
    with pytest.raises(OSError, match='disque indisponible'):
        p.installer('autre', str(registre.index))
    assert ((projet / p.MANIFESTE).read_bytes(), (projet / p.VERROU).read_bytes()) == avant
    assert sorted(c.name for c in (projet / 'nck_modules').iterdir()) == ['demo']


def test_cli_erreurs_propres(projet, registre, capsys):
    assert main(['installer', 'Absent']) == 1
    assert 'nom de paquet invalide' in capsys.readouterr().err
    (projet / p.MANIFESTE).write_text('[]')
    assert main(['paquets']) == 1
    assert 'objet JSON' in capsys.readouterr().err
    (projet / p.MANIFESTE).unlink()
    assert main(['installer']) == 1
    assert 'nck init' in capsys.readouterr().err


def test_liste_absents_et_cli(projet, registre, capsys):
    registre()
    assert main(['paquets']) == 0
    assert 'Aucun paquet' in capsys.readouterr().out
    assert main(['installer', 'demo', '--index', str(registre.index)]) == 0
    assert main(['desinstaller', 'demo']) == 0
    m = p.lire_json(projet / p.MANIFESTE)
    m['dependances'] = {'absent': '^1'}
    ecrire_json(projet / p.MANIFESTE, m)
    assert 'non installé' in p.lister()[0]


def test_paquet_introuvable_suggestion(projet):
    with pytest.raises(ErreurType, match='nck installer absent'):
        compiler_source('importer "absent"', str(projet / 'main.nck'))


def test_import_global_et_priorite_locale(projet, tmp_path, capsys):
    global_dir = Path.home() / '.nck/paquets/demo'
    ecrire_json(global_dir / p.MANIFESTE, manifeste())
    (global_dir / 'module.nck').write_text('constante X = 1\n')
    executer_source('importer "demo"\necrire(demo.X)', str(projet / 'main.nck'))
    assert capsys.readouterr().out == '1\n'
    local = projet / 'nck_modules/demo'
    ecrire_json(local / p.MANIFESTE, manifeste())
    (local / 'module.nck').write_text('constante X = 2\n')
    executer_source('importer "demo"\necrire(demo.X)', str(projet / 'main.nck'))
    assert capsys.readouterr().out == '2\n'
    (local / 'module.nck').unlink()
    with pytest.raises(ErreurType, match="point d'entrée introuvable"):
        compiler_source('importer "demo"', str(projet / 'main.nck'))


def test_import_paquet_une_seule_execution(projet, registre, capsys):
    registre()
    p.installer('demo', str(registre.index))
    module = projet / 'nck_modules/demo/module.nck'
    module.write_text('ecrire("charge")\nconstante X = 42\n')
    executer_source('importer "demo" comme a\nimporter "demo" comme b\necrire(a.X, b.X)', str(projet / 'main.nck'))
    assert capsys.readouterr().out == 'charge\n42 42\n'


def test_index_invalide(projet, registre):
    registre.index.write_text('[]')
    with pytest.raises(p.ErreurPaquet, match='index doit contenir'):
        p.installer('demo', str(registre.index))


def test_telechargement_https_et_taille(tmp_path):
    with pytest.raises(p.ErreurPaquet, match='HTTPS'):
        p._telecharger('http://example.invalid/archive.zip', 10, False)
    chemin = tmp_path / 'gros'
    chemin.write_bytes(b'12345')
    with pytest.raises(p.ErreurPaquet, match='volumineux'):
        p._telecharger(chemin.as_uri(), 4, True)
    with pytest.raises(p.ErreurPaquet, match='HTTPS'):
        p._telecharger(chemin.as_uri(), 10, False)


def test_registre_https_simule(projet, registre, monkeypatch, capsys):
    archive = registre('demo')
    catalogue = {'demo': {'versions': {'1.0.0': {
        'url': './demo.zip', 'sha256': hashlib.sha256(archive.read_bytes()).hexdigest()}}}}
    reponses = {'https://registre.example/index.json': json.dumps(catalogue).encode(),
                'https://registre.example/demo.zip': archive.read_bytes()}
    appels = []

    class Reponse(io.BytesIO):
        def __init__(self, adresse):
            super().__init__(reponses[adresse])
            self.adresse = adresse

        def geturl(self):
            return self.adresse

    def ouvrir(adresse, timeout):
        assert timeout == 30
        appels.append(adresse)
        return Reponse(adresse)

    monkeypatch.setattr(p, 'urlopen', ouvrir)
    monkeypatch.setenv('NCK_INDEX', 'https://registre.example/index.json')
    assert p.installer('demo') == {'demo': '1.0.0'}
    assert appels == list(reponses)
    executer_source('importer "demo"\necrire(demo.doubler(8))', str(projet / 'main.nck'))
    assert capsys.readouterr().out == '16\n'


def test_index_distant_ne_peut_lire_fichier_local(monkeypatch):
    monkeypatch.setattr(p, '_telecharger', lambda *a: json.dumps({
        'demo': {'versions': {'1.0.0': {'url': 'file:///etc/passwd', 'sha256': '0' * 64}}}
    }).encode())
    with pytest.raises(p.ErreurPaquet, match='archives HTTPS'):
        p.Registre('https://registre.example/index.json').versions('demo')


def test_redirection_insecurisee_refusee(monkeypatch):
    class Reponse(io.BytesIO):
        def geturl(self):
            return 'http://insecure.example/archive.zip'

    monkeypatch.setattr(p, 'urlopen', lambda *a, **kw: Reponse(b'contenu'))
    with pytest.raises(p.ErreurPaquet, match='redirection'):
        p._telecharger('https://registre.example/archive.zip', 100, False)


def test_erreur_reseau_presente_sans_trace(projet, monkeypatch, capsys):
    def echouer(*args, **kw):
        raise p.URLError('indisponible')

    monkeypatch.setattr(p, 'urlopen', echouer)
    assert main(['installer', 'demo', '--index', 'https://registre.example/index.json']) == 1
    sortie = capsys.readouterr().err
    assert 'téléchargement impossible' in sortie
    assert 'Traceback' not in sortie


@pytest.mark.parametrize('chemin', ['CON.nck', 'a/NUL', 'a./module.nck', 'a /module.nck', 'a?.nck'])
def test_chemins_non_portables(chemin):
    with pytest.raises(p.ErreurPaquet, match='non portable'):
        p.chemin_sur(chemin)


def test_zip_doublons_refuses(tmp_path):
    contenu = io.BytesIO()
    with zipfile.ZipFile(contenu, 'w') as z:
        z.writestr('module.nck', '')
        z.writestr('MODULE.nck', '')
    with pytest.raises(p.ErreurPaquet, match='dupliquée'):
        p._extraire(contenu.getvalue(), tmp_path)


@pytest.mark.parametrize('changement', [
    {'description': []}, {'dependances': []}, {'dependances': {'../intrus': '*'}},
    {'dependances': {'base': 12}}, {'point_entree': 'module.py'},
])
def test_manifeste_invalide(changement):
    with pytest.raises(p.ErreurPaquet):
        p.valider_manifeste({**manifeste(), **changement})


def test_verrou_invalide(projet):
    ecrire_json(projet / p.VERROU, {'format': 99, 'paquets': {}})
    with pytest.raises(p.ErreurPaquet, match='format de paquet.verrou.json'):
        p.installer()


def test_exemple_du_depot_installe(projet, tmp_path, capsys):
    exemple = Path(__file__).resolve().parents[1] / 'exemples/paquets/maths-plus'
    archive = Path(shutil.make_archive(str(tmp_path / 'maths-plus'), 'zip', root_dir=exemple))
    index = tmp_path / 'index.json'
    ecrire_json(index, {'maths-plus': {'versions': {'1.0.0': {
        'url': archive.name, 'sha256': hashlib.sha256(archive.read_bytes()).hexdigest()}}}})
    p.installer('maths-plus', str(index))
    executer_source('importer "maths-plus" comme maths\necrire(maths.carre(5), maths.cube(3))',
                    str(projet / 'main.nck'))
    assert capsys.readouterr().out == '25 27\n'


def test_init_cli(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    assert main(['init', '--nom', 'projet-cli']) == 0
    assert 'Projet créé' in capsys.readouterr().out
    assert main(['init', '--nom', 'autre']) == 1
    assert 'existe déjà' in capsys.readouterr().err


def test_dependances_cycliques_resolution_finie(projet, registre):
    registre('base', deps={'haut': '^1'})
    registre('haut', deps={'base': '^1'})
    assert p.installer('base', str(registre.index)) == {'base': '1.0.0', 'haut': '1.0.0'}


def test_adresses_locales_et_relatives(tmp_path):
    assert p._adresse(str(tmp_path / 'index.json')) == (tmp_path / 'index.json').as_uri()
    assert p._adresse('./archive.zip', (tmp_path / 'index.json').as_uri()) == (tmp_path / 'archive.zip').as_uri()
    assert p._adresse('/archives/demo.zip', 'https://exemple.org/nck/index.json') == 'https://exemple.org/archives/demo.zip'


@pytest.mark.parametrize('ordre', [False, True])
def test_cache_partage_import_fichier_et_nom_paquet(projet, registre, capsys, ordre):
    registre('maths-plus')
    p.installer('maths-plus', str(registre.index))
    entree = projet / 'nck_modules/maths-plus/module.nck'
    entree.write_text('ecrire("charge")\nconstante X = 42\n')
    imports = ['importer "nck_modules/maths-plus/module.nck"', 'importer "maths-plus"']
    if ordre:
        imports.reverse()
    executer_source('\n'.join(imports) + '\necrire(module.X, maths_plus.X)', str(projet / 'main.nck'))
    assert capsys.readouterr().out == 'charge\n42 42\n'


def test_zip_nom_original_verifie_apres_normalisation_windows(tmp_path, monkeypatch):
    contenu = io.BytesIO()
    with zipfile.ZipFile(contenu, 'w') as z:
        info = zipfile.ZipInfo('nom-provisoire')
        info.filename = info.orig_filename = 'a\\intrus.nck'
        z.writestr(info, 'ecrire(1)')
    initialiser = zipfile.ZipInfo.__init__

    def simuler_windows(self, filename='NoName', date_time=(1980, 1, 1, 0, 0, 0)):
        initialiser(self, filename, date_time)
        self.filename = self.filename.replace('\\', '/')

    monkeypatch.setattr(zipfile.ZipInfo, '__init__', simuler_windows)
    with pytest.raises(p.ErreurPaquet, match='chemin de paquet interdit'):
        p._extraire(contenu.getvalue(), tmp_path / 'extraction')
    assert not (tmp_path / 'extraction').exists()
