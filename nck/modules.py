"""Chargement des modules : résolution des chemins, cache, détection des cycles."""

import os
import re

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
        self.verifie = False
        self.execute = False


class Chargeur:
    """Partagé entre le vérificateur et l'interpréteur d'un même programme."""

    def __init__(self):
        self.modules: dict[str, Module] = {}
        self.en_cours: list[str] = []     # pile des modules en cours de vérification (cycles)

    def resoudre(self, chemin: str, depuis_fichier: str, noeud) -> Module:
        if not chemin.endswith(EXTENSION):
            raise ErreurType(f"un module doit être un fichier {EXTENSION} (reçu : \"{chemin}\")",
                             noeud.ligne, noeud.colonne, depuis_fichier)
        if depuis_fichier.startswith("<"):          # <entrée>, <repl>, <test> : pas de fichier réel
            base = os.getcwd()
        else:
            base = os.path.dirname(os.path.abspath(depuis_fichier))
        absolu = os.path.normpath(os.path.join(base, chemin))
        if absolu in self.modules:
            return self.modules[absolu]
        if not os.path.exists(absolu):
            raise ErreurType(f"module introuvable : \"{chemin}\" (cherché dans {base})",
                             noeud.ligne, noeud.colonne, depuis_fichier)
        m = Module(absolu)
        with open(absolu, encoding="utf-8") as f:
            m.source = f.read()
        self.modules[absolu] = m
        return m

    def charger_programme(self, m: Module):
        if m.programme is None:
            from .parseur import parser
            m.programme = parser(m.source or "", m.chemin)
        return m.programme
