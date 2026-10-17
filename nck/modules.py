"""Chargement des modules : résolution des chemins, cache, détection des cycles."""

import os
import re
from pathlib import Path

from .erreurs import ErreurNck, ErreurType

EXTENSION = ".nck"


def nom_module(chemin: str) -> str:
    """Nom par défaut d'un module : le nom du fichier sans extension (ex : outils/maths.nck -> maths)."""
    base = os.path.splitext(os.path.basename(chemin))[0]
    return re.sub(r"\W", "_", base)


class Module:
    def __init__(self, chemin: str):
        self.chemin = chemin
        self.nom = nom_module(chemin)
        self.source: str | None = None
        self.programme = None
        self.exports: dict = {}          # nom -> Symbole (rempli par le vérificateur)
        self.env = None                   # Env (rempli par l'interpréteur)
        self.natif: str | None = None     # nom d'un module intégré (ex. `gui`)
        self.verifie = False
        self.execute = False


class Chargeur:
    """Partagé entre le vérificateur et l'interpréteur d'un même programme."""

    def __init__(self):
        self.modules: dict[str, Module] = {}
        self.en_cours: list[str] = []     # pile des modules en cours de vérification (cycles)

    def resoudre(self, chemin: str, depuis_fichier: str, noeud) -> Module:
        from .paquets import ErreurPaquet, entree_paquet, nom_valide

        # Modules intégrés réservés : ils sont résolus avant les paquets portant le même nom.
        if chemin == "gui":
            cle = "<natif:gui>"
            if cle not in self.modules:
                module = Module(cle)
                module.nom = "gui"
                module.natif = "gui"
                self.modules[cle] = module
            return self.modules[cle]

        if depuis_fichier.startswith("<"):
            base = Path.cwd()
        else:
            base = Path(depuis_fichier).resolve().parent
        nom_paquet = None
        if nom_valide(chemin):
            nom_paquet = chemin
            candidats = [d / "nck_modules" / chemin for d in (base, *base.parents)]
            candidats.append(Path.home() / ".nck" / "paquets" / chemin)
            dossier = next((d for d in candidats if d.exists()), None)
            if dossier is None:
                raise ErreurType(f'paquet introuvable : "{chemin}" ; essayez `nck installer {chemin}`',
                                 noeud.ligne, noeud.colonne, depuis_fichier)
            try:
                cible = entree_paquet(dossier)
            except ErreurPaquet as exc:
                raise ErreurType(str(exc), noeud.ligne, noeud.colonne, depuis_fichier) from exc
        else:
            if not chemin.endswith(EXTENSION):
                raise ErreurType(f'un module doit être un fichier {EXTENSION} ou un nom de paquet (reçu : "{chemin}")',
                                 noeud.ligne, noeud.colonne, depuis_fichier)
            cible = base / chemin
        absolu = str(cible.resolve())
        if absolu in self.modules:
            return self.modules[absolu]
        if not cible.is_file():
            raise ErreurType(f'module introuvable : "{chemin}" (cherché dans {base})',
                             noeud.ligne, noeud.colonne, depuis_fichier)
        m = Module(absolu)
        if nom_paquet:
            m.nom = nom_paquet.replace('-', '_')
        try:
            m.source = cible.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            raise ErreurType(f'impossible de lire le module "{chemin}" : {exc}',
                             noeud.ligne, noeud.colonne, depuis_fichier) from exc
        self.modules[absolu] = m
        return m

    def charger_programme(self, m: Module):
        if m.programme is None:
            from .parseur import parser
            m.programme = parser(m.source or "", m.chemin)
        return m.programme
