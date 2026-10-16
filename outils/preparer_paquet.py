"""Prépare un ZIP NCK reproductible et son index, sans publier ni exécuter le paquet.

    python outils/preparer_paquet.py exemples/paquets/maths-plus --sortie registre-local
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import stat
import sys
import tempfile
from urllib.parse import urlparse
import zipfile

RACINE = Path(__file__).resolve().parents[1]
if str(RACINE) not in sys.path:
    sys.path.insert(0, str(RACINE))

from nck.erreurs import ErreurNck
from nck.paquets import (ErreurPaquet, MANIFESTE, MAX_ARCHIVE, MAX_EXTRAIT, Registre,
                         _extraire, _source_valide, lire_json, nom_valide, valider_manifeste)
from nck.parseur import parser

IGNORES = {'.git', '.gitignore', '.gitattributes', '.editorconfig', '.DS_Store',
           '.venv', 'venv', '__pycache__', '.pytest_cache', 'nck_modules',
           'build', 'dist', '.vscode', 'paquet.verrou.json'}


def construire_archive(dossier: Path) -> tuple[dict, bytes]:
    dossier = dossier.resolve()
    manifeste = valider_manifeste(lire_json(dossier / MANIFESTE))
    contenu = io.BytesIO()
    taille = 0
    nombre = 0
    with zipfile.ZipFile(contenu, 'w', compression=zipfile.ZIP_STORED) as archive:
        for base, dossiers, fichiers in os.walk(dossier, followlinks=False):
            for nom in sorted([*dossiers, *fichiers]):
                chemin = Path(base) / nom
                if nom in IGNORES or nom.startswith('.nck-install-'):
                    continue
                if chemin.is_symlink():
                    raise ErreurPaquet(f"lien symbolique interdit : {chemin}")
                if nom in dossiers:
                    continue
                if not chemin.is_file():
                    raise ErreurPaquet(f"fichier spécial interdit : {chemin}")
                taille += chemin.stat().st_size
                nombre += 1
                if taille > MAX_EXTRAIT or nombre > 5000:
                    raise ErreurPaquet("paquet trop volumineux (50 Mio / 5000 fichiers maximum)")
                donnees = chemin.read_bytes()
                relatif = chemin.relative_to(dossier).as_posix()
                if chemin.suffix.lower() == '.nck':
                    try:
                        parser(donnees.decode('utf-8'), relatif)
                    except (ErreurNck, UnicodeError) as exc:
                        raise ErreurPaquet(f"source NCK invalide : {relatif} : {exc}") from exc
                info = zipfile.ZipInfo(relatif, date_time=(1980, 1, 1, 0, 0, 0))
                info.create_system = 3
                info.external_attr = (stat.S_IFREG | 0o644) << 16
                archive.writestr(info, donnees)
            dossiers[:] = sorted(n for n in dossiers if n not in IGNORES and not n.startswith('.nck-install-'))
    resultat = contenu.getvalue()
    if len(resultat) > MAX_ARCHIVE:
        raise ErreurPaquet("archive trop volumineuse (20 Mio maximum)")
    # Réutilise exactement les contrôles appliqués à l'installation.
    with tempfile.TemporaryDirectory(prefix='nck-valider-') as temp:
        _extraire(resultat, Path(temp))
    return manifeste, resultat


def preparer(dossier: Path, sortie: Path, url_base: str | None = None) -> tuple[Path, Path]:
    dossier = dossier.resolve()
    sortie = sortie.resolve()
    if sortie == dossier or sortie.is_relative_to(dossier):
        raise ErreurPaquet("le dossier de sortie doit être hors du paquet source")
    if url_base is not None:
        url = urlparse(url_base)
        if url.scheme != 'https' or not url.netloc or url.query or url.fragment or url.username or url.password:
            raise ErreurPaquet("--url-base doit être une URL HTTPS sans identifiants, requête ni fragment")
    manifeste, contenu = construire_archive(dossier)
    nom, version = manifeste['nom'], manifeste['version']
    nom_archive = f'{nom}-{version}.zip'
    source = {'url': url_base.rstrip('/') + '/' + nom_archive if url_base else nom_archive,
              'sha256': hashlib.sha256(contenu).hexdigest()}
    index = sortie / 'index.json'
    catalogue = lire_json(index) if index.exists() else {}
    registre = Registre(str(index))
    registre.index = catalogue
    for paquet in catalogue:
        if not nom_valide(paquet):
            raise ErreurPaquet(f"nom invalide dans l'index existant : {paquet}")
        for entree in registre.versions(paquet).values():
            _source_valide(entree)
    entree = catalogue.setdefault(nom, {'versions': {}})
    versions = entree.setdefault('versions', {})
    if version in versions and versions[version] != source:
        raise ErreurPaquet(f"{nom}@{version} existe déjà avec un autre contenu ou une autre URL ; augmentez la version")
    cible = sortie / nom_archive
    if cible.exists() and cible.read_bytes() != contenu:
        raise ErreurPaquet(f"archive {nom_archive} déjà présente avec un autre contenu ; augmentez la version")
    versions[version] = source
    sortie.mkdir(parents=True, exist_ok=True)
    # Un index n'est visible qu'une fois son archive complète en place.
    with tempfile.TemporaryDirectory(prefix='.nck-preparer-', dir=sortie) as temp:
        travail = Path(temp)
        (travail / nom_archive).write_bytes(contenu)
        (travail / 'index.json').write_text(
            json.dumps(catalogue, indent=2, ensure_ascii=False, sort_keys=True) + '\n', encoding='utf-8')
        os.replace(travail / nom_archive, cible)
        os.replace(travail / 'index.json', index)
    return cible, index


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('dossier', type=Path, help='racine du paquet (contenant paquet.json)')
    ap.add_argument('--sortie', type=Path, default=Path('registre-local'), help='dossier du ZIP et de index.json')
    ap.add_argument('--url-base', help='URL HTTPS du futur emplacement des ZIP (aucun téléversement)')
    args = ap.parse_args(argv)
    try:
        archive, index = preparer(args.dossier, args.sortie, args.url_base)
    except (ErreurPaquet, OSError) as exc:
        print(f'Erreur : {exc}', file=sys.stderr)
        return 1
    print(f'Archive : {archive}\nIndex : {index}\nAucun fichier publié en ligne.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
