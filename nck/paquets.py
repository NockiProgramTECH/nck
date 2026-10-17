"""Gestion de paquets NCK, sans dépendance Python externe.

Les archives ne sont jamais exécutées. Les installations sont préparées dans un
répertoire temporaire avant de remplacer nck_modules et les métadonnées.
"""

from __future__ import annotations

import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import tempfile
from urllib.error import URLError
from urllib.parse import urljoin, urlparse
from urllib.request import urlopen
import zipfile

MANIFESTE = "paquet.json"
VERROU = "paquet.verrou.json"
INDEX = "https://github.com/NockiProgramTECH/nck-paquets/raw/refs/heads/main/index.json"
NOM = re.compile(r"[a-z][a-z0-9]*(?:-[a-z0-9]+)*\Z")
VERSION = re.compile(r"(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\Z")
MAX_ARCHIVE = 20 * 1024 * 1024
MAX_EXTRAIT = 50 * 1024 * 1024


class ErreurPaquet(Exception):
    """Erreur utilisateur présentée sans trace Python par la CLI."""


def nom_valide(nom: str) -> bool:
    return isinstance(nom, str) and NOM.fullmatch(nom) is not None


def version(v: str) -> tuple[int, int, int]:
    if not isinstance(v, str) or not VERSION.fullmatch(v):
        raise ErreurPaquet(f"version invalide : {v!r} (attendu : majeur.mineur.correctif)")
    return tuple(map(int, v.split('.')))


def accepte(v: str, contrainte: str) -> bool:
    courant = version(v)
    if contrainte == "*":
        return True
    prefixe = contrainte[:1]
    valeur = contrainte[1:] if prefixe in ("^", "~") else contrainte
    morceaux = valeur.split('.')
    if prefixe in ("^", "~") and len(morceaux) in (1, 2):
        valeur += ".0" * (3 - len(morceaux))
    minimum = version(valeur)
    if prefixe == "^":
        a, b, c = minimum
        maximum = (a + 1, 0, 0) if a else ((0, b + 1, 0) if b else (0, 0, c + 1))
    elif prefixe == "~":
        a, b, _ = minimum
        maximum = (a + 1, 0, 0) if len(morceaux) == 1 else (a, b + 1, 0)
    else:
        return courant == minimum
    return minimum <= courant < maximum


def lire_json(chemin: Path) -> dict:
    try:
        objet = json.loads(chemin.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ErreurPaquet(f"impossible de lire {chemin} : {exc}") from exc
    if not isinstance(objet, dict):
        raise ErreurPaquet(f"{chemin} doit contenir un objet JSON")
    return objet


def valider_manifeste(objet: dict) -> dict:
    if not nom_valide(objet.get("nom")):
        raise ErreurPaquet("nom de paquet invalide (exemple : maths-plus)")
    version(objet.get("version"))
    if not isinstance(objet.get("description", ""), str):
        raise ErreurPaquet("description doit être un texte")
    entree = objet.get("point_entree", "module.nck")
    chemin_sur(entree)
    if not entree.endswith(".nck"):
        raise ErreurPaquet("point_entree doit désigner un fichier .nck")
    deps = objet.get("dependances", {})
    if not isinstance(deps, dict):
        raise ErreurPaquet("dependances doit être un objet JSON")
    for nom, contrainte in deps.items():
        if not nom_valide(nom) or not isinstance(contrainte, str):
            raise ErreurPaquet("dépendance invalide : nom et contrainte de version attendus")
        accepte("0.0.0", contrainte)
    return {**objet, "point_entree": entree, "dependances": deps}


def chemin_sur(chemin: str) -> PurePosixPath:
    if (not isinstance(chemin, str) or not chemin or "\\" in chemin or ":" in chemin
            or "\x00" in chemin or chemin.startswith("/")
            or any(p in ("", ".", "..") for p in chemin.split('/'))):
        raise ErreurPaquet(f"chemin de paquet interdit : {chemin!r}")
    for segment in chemin.split('/'):
        reserve = segment.split('.')[0].upper()
        if (segment.endswith(('.', ' ')) or any(ord(c) < 32 or c in '<>"|?*' for c in segment)
                or reserve in {'CON', 'PRN', 'AUX', 'NUL', *(f'COM{i}' for i in range(1, 10)),
                               *(f'LPT{i}' for i in range(1, 10))}):
            raise ErreurPaquet(f"chemin de paquet non portable : {chemin!r}")
    return PurePosixPath(chemin)


def projet(depuis: Path | None = None) -> Path:
    base = (depuis or Path.cwd()).resolve()
    for dossier in (base, *base.parents):
        if (dossier / MANIFESTE).is_file():
            return dossier
    raise ErreurPaquet("aucun paquet.json trouvé ; lancez `nck init` dans votre projet")


def initialiser(nom: str | None = None) -> Path:
    racine = Path.cwd()
    chemin = racine / MANIFESTE
    if chemin.exists():
        raise ErreurPaquet("paquet.json existe déjà ; aucun fichier n'a été modifié")
    nom = nom or racine.name.lower().replace('_', '-')
    manifeste = valider_manifeste({"nom": nom, "version": "0.1.0", "description": "",
                                  "point_entree": "module.nck", "dependances": {}})
    with chemin.open('x', encoding='utf-8') as f:
        f.write(json.dumps(manifeste, ensure_ascii=False, indent=2) + '\n')
    entree = racine / "module.nck"
    if not entree.exists():
        entree.write_text('// Point d’entrée du paquet NCK.\n', encoding='utf-8')
    return chemin


def entree_paquet(dossier: Path) -> Path:
    manifeste = valider_manifeste(lire_json(dossier / MANIFESTE))
    entree = dossier / manifeste['point_entree']
    if not entree.resolve().is_relative_to(dossier.resolve()) or not entree.is_file():
        raise ErreurPaquet(f"point d'entrée introuvable ou hors du paquet : {entree}")
    return entree


def _adresse(valeur: str, base: str | None = None) -> str:
    # Sous Windows, C:\\... est un chemin, pas un schéma d'URL « c ».
    if (not base or urlparse(base).scheme == 'file') and Path(valeur).is_absolute():
        return Path(valeur).resolve().as_uri()
    if urlparse(valeur).scheme:
        return valeur
    if base and urlparse(base).scheme in ('https', 'file'):
        return urljoin(base, valeur)
    return Path(valeur).resolve().as_uri()


def _telecharger(adresse: str, limite: int, local: bool) -> bytes:
    scheme = urlparse(adresse).scheme
    if scheme != 'https' and not (local and scheme == 'file'):
        raise ErreurPaquet("les téléchargements exigent HTTPS (ou un fichier pour un index local)")
    try:
        with urlopen(adresse, timeout=30) as reponse:
            final = urlparse(reponse.geturl()).scheme
            if final != 'https' and not (local and final == 'file'):
                raise ErreurPaquet("redirection vers une adresse non sécurisée")
            contenu = reponse.read(limite + 1)
    except (OSError, URLError, ValueError) as exc:
        raise ErreurPaquet(f"téléchargement impossible : {adresse} : {exc}") from exc
    if len(contenu) > limite:
        raise ErreurPaquet(f"téléchargement trop volumineux : {adresse}")
    return contenu


def _extraire(contenu: bytes, destination: Path) -> dict:
    try:
        with zipfile.ZipFile(io.BytesIO(contenu)) as archive:
            infos = archive.infolist()
            if len(infos) > 5000 or sum(i.file_size for i in infos) > MAX_EXTRAIT:
                raise ErreurPaquet("archive trop volumineuse après décompression")
            vus = set()
            for info in infos:
                # ZipInfo normalise les antislashs sur Windows et tronque les NUL.
                # Contrôler le nom original avant toute normalisation par Python.
                brut = info.orig_filename
                nom = brut[:-1] if brut.endswith('/') else brut
                relatif = chemin_sur(nom)
                cle = nom.casefold()
                if cle in vus:
                    raise ErreurPaquet(f"entrée dupliquée dans l'archive : {nom}")
                vus.add(cle)
                mode = info.external_attr >> 16
                if stat.S_ISLNK(mode) or (stat.S_IFMT(mode) not in (0, stat.S_IFREG, stat.S_IFDIR)):
                    raise ErreurPaquet("liens et fichiers spéciaux interdits dans un paquet")
                if not info.is_dir() and relatif.suffix.lower() not in ('.nck', '.json', '.md', '.txt') and relatif.name not in ('LICENSE', 'LICENCE'):
                    raise ErreurPaquet(f"fichier non portable interdit : {nom} (paquets 100 % NCK)")
                cible = destination.joinpath(*relatif.parts)
                if info.is_dir():
                    cible.mkdir(parents=True, exist_ok=True)
                else:
                    cible.parent.mkdir(parents=True, exist_ok=True)
                    cible.write_bytes(archive.read(info))
    except (zipfile.BadZipFile, RuntimeError, NotImplementedError, OSError) as exc:
        raise ErreurPaquet(f"archive ZIP invalide : {exc}") from exc
    manifeste = valider_manifeste(lire_json(destination / MANIFESTE))
    entree_paquet(destination)
    return manifeste


class Registre:
    def __init__(self, adresse: str | None):
        self.adresse = _adresse(adresse or os.environ.get('NCK_INDEX', INDEX))
        self.local = urlparse(self.adresse).scheme == 'file'
        self.index = None

    def versions(self, nom: str) -> dict:
        if self.index is None:
            try:
                self.index = json.loads(_telecharger(self.adresse, 5 * 1024 * 1024, self.local))
            except (ValueError, UnicodeError) as exc:
                raise ErreurPaquet(f"index JSON invalide : {exc}") from exc
            if not isinstance(self.index, dict):
                raise ErreurPaquet("l'index doit contenir un objet JSON")
        paquet = self.index.get(nom, {})
        if not isinstance(paquet, dict) or not isinstance(paquet.get('versions', {}), dict):
            raise ErreurPaquet(f"entrée d'index invalide : {nom}")
        resultat = {}
        for v, source in paquet.get('versions', {}).items():
            version(v)
            if not isinstance(source, dict) or not isinstance(source.get('url'), str):
                raise ErreurPaquet(f"source invalide : {nom}@{v}")
            adresse = _adresse(source['url'], self.adresse)
            if urlparse(adresse).scheme != 'https' and not (self.local and urlparse(adresse).scheme == 'file'):
                raise ErreurPaquet("l'index distant doit référencer des archives HTTPS")
            resultat[v] = {**source, 'url': adresse}
        return resultat


def _source_valide(source: dict) -> None:
    if (not isinstance(source, dict) or not isinstance(source.get('url'), str)
            or not isinstance(source.get('sha256'), str)
            or not re.fullmatch(r'[0-9a-f]{64}', source['sha256'])):
        raise ErreurPaquet("source de paquet invalide : url et sha256 (64 caractères minuscules) requis")


def _resoudre(deps: dict, verrou: dict, registre: Registre, temporaire: Path) -> dict:
    cache = {}
    essais = 0

    def charger(nom, v, source):
        _source_valide(source)
        cle = (nom, v, source['url'], source['sha256'])
        if cle not in cache:
            contenu = _telecharger(source['url'], MAX_ARCHIVE,
                                   registre.local or urlparse(source['url']).scheme == 'file')
            if hashlib.sha256(contenu).hexdigest() != source['sha256']:
                raise ErreurPaquet(f"SHA-256 incorrect pour {nom}@{v}")
            dossier = temporaire / f'archive-{len(cache)}'
            dossier.mkdir()
            manifeste = _extraire(contenu, dossier)
            if manifeste['nom'] != nom or manifeste['version'] != v:
                raise ErreurPaquet(f"identité du paquet différente de l'index : {nom}@{v}")
            cache[cle] = {'version': v, 'url': source['url'], 'sha256': source['sha256'],
                          'dependances': manifeste['dependances'], '_dossier': dossier}
        return cache[cle]

    def chercher(contraintes, choix):
        nonlocal essais
        essais += 1
        if len(contraintes) > 200 or essais > 10000:
            raise ErreurPaquet("graphe de dépendances trop complexe (limite : 200 paquets, 10000 essais)")
        if any(not all(accepte(choix[n]['version'], c) for c in cs)
               for n, cs in contraintes.items() if n in choix):
            return None
        restant = next((n for n in contraintes if n not in choix), None)
        if restant is None:
            return choix
        cs = contraintes[restant]
        pin = verrou.get(restant)
        candidats = []
        if isinstance(pin, dict) and all(accepte(pin.get('version'), c) for c in cs):
            candidats.append((pin['version'], pin))
        # On ne consulte l'index que si le verrou ne suffit pas.
        def possibilites():
            yield from candidats
            versions = registre.versions(restant)
            for v in sorted(versions, key=version, reverse=True):
                if all(accepte(v, c) for c in cs) and not any(v == p[0] for p in candidats):
                    yield v, versions[v]
        for v, source in possibilites():
            paquet = charger(restant, v, source)
            nouvelles = {n: list(valeurs) for n, valeurs in contraintes.items()}
            for nom, contrainte in paquet['dependances'].items():
                nouvelles.setdefault(nom, []).append(contrainte)
            resultat = chercher(nouvelles, {**choix, restant: paquet})
            if resultat is not None:
                return resultat
        return None

    resultat = chercher({n: [c] for n, c in deps.items()}, {})
    if resultat is None:
        raise ErreurPaquet("dépendances incompatibles ou paquet/version introuvable ; vérifiez les contraintes et l'index")
    return resultat


def _enregistrer(racine: Path, manifeste: dict, choix: dict, travail: Path) -> None:
    modules = travail / 'modules'
    modules.mkdir()
    for nom, paquet in choix.items():
        shutil.copytree(paquet['_dossier'], modules / nom)
    verrou = {'format': 1, 'paquets': {nom: {k: v for k, v in p.items() if not k.startswith('_')}
                                     for nom, p in sorted(choix.items())}}
    fichiers = {MANIFESTE: manifeste, VERROU: verrou}
    avant = {nom: (racine / nom).read_bytes() if (racine / nom).exists() else None for nom in fichiers}
    cible = racine / 'nck_modules'
    sauvegarde = travail / 'anciens-modules'
    deplace = False
    installe = False
    try:
        if cible.exists() or cible.is_symlink():
            cible.rename(sauvegarde)
            deplace = True
        modules.rename(cible)
        installe = True
        for nom, objet in fichiers.items():
            nouveau = travail / nom
            nouveau.write_text(json.dumps(objet, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
            os.replace(nouveau, racine / nom)
    except OSError:
        if installe:
            shutil.rmtree(cible)
        if deplace:
            sauvegarde.rename(cible)
        for nom, contenu in avant.items():
            if contenu is None:
                (racine / nom).unlink(missing_ok=True)
            else:
                (racine / nom).write_bytes(contenu)
        raise


def installer(specification: str | None = None, index: str | None = None, retirer: str | None = None) -> dict:
    racine = projet()
    manifeste = valider_manifeste(lire_json(racine / MANIFESTE))
    deps = manifeste['dependances'].copy()
    ajout = None
    if specification is not None:
        ajout, separateur, contrainte = specification.partition('@')
        if not nom_valide(ajout):
            raise ErreurPaquet("nom de paquet invalide")
        contrainte = contrainte if separateur else '*'
        accepte('0.0.0', contrainte)
        deps[ajout] = contrainte
    if retirer:
        if retirer not in deps:
            raise ErreurPaquet(f"{retirer} n'est pas une dépendance directe du projet")
        del deps[retirer]
    ancien = lire_json(racine / VERROU) if (racine / VERROU).exists() else {'format': 1, 'paquets': {}}
    if ancien.get('format') != 1 or not isinstance(ancien.get('paquets'), dict):
        raise ErreurPaquet("format de paquet.verrou.json invalide ou non pris en charge")
    with tempfile.TemporaryDirectory(prefix='.nck-install-', dir=racine) as temp:
        travail = Path(temp)
        choix = _resoudre(deps, ancien['paquets'], Registre(index), travail)
        if ajout and '@' not in specification:
            deps[ajout] = '^' + choix[ajout]['version']
        manifeste['dependances'] = deps
        _enregistrer(racine, manifeste, choix, travail)
    return {nom: p['version'] for nom, p in sorted(choix.items())}


def lister() -> list[str]:
    racine = projet()
    manifeste = valider_manifeste(lire_json(racine / MANIFESTE))
    lignes = []
    modules = racine / 'nck_modules'
    noms = set(manifeste['dependances'])
    if modules.is_dir():
        noms.update(p.name for p in modules.iterdir() if p.is_dir() and nom_valide(p.name))
    for nom in sorted(noms):
        dossier = modules / nom
        if dossier.is_dir():
            m = valider_manifeste(lire_json(dossier / MANIFESTE))
            etiquette = 'directe' if nom in manifeste['dependances'] else 'transitive'
            lignes.append(f"{nom}@{m['version']} ({etiquette})")
        else:
            lignes.append(f"{nom} : non installé — lancez `nck installer`")
    return lignes
