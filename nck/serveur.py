"""Serveur d'analyse pour les éditeurs (`nck serveur`).

Protocole volontairement simple : une requête JSON par ligne sur l'entrée standard,
une réponse JSON par ligne sur la sortie standard.

    -> {"id": 1, "methode": "analyser",  "fichier": "...", "texte": "..."}
    <- {"id": 1, "resultat": {"diagnostics": [...]}}

Méthodes : analyser, completer, survoler, signature, definition, fermer.
Positions : `ligne` et `colonne` en base 1 (le client VS Code convertit).
"""

import json
import sys
import traceback

from .analyse import Analyse


class Serveur:
    def __init__(self):
        self.cache: dict[str, Analyse] = {}
        self.textes: dict[str, str] = {}

    def analyse(self, fichier: str, texte: str | None, ligne_curseur: int | None = None) -> Analyse:
        if texte is not None:
            self.textes[fichier] = texte
        texte = self.textes.get(fichier, "")
        a = self.cache.get(fichier)
        if a is None or a.source != texte:
            a = Analyse(texte, fichier)
            self.cache[fichier] = a
        if a.erreur is not None and ligne_curseur is not None:
            # pendant la frappe, une analyse tolérante centrée sur la ligne du curseur donne de meilleurs symboles
            return Analyse(texte, fichier, ligne_curseur)
        return a

    def traiter(self, req: dict):
        methode = req.get("methode")
        fichier = req.get("fichier", "<éditeur>")
        texte = req.get("texte")
        ligne = req.get("ligne")
        colonne = req.get("colonne")
        if methode == "analyser":
            return {"diagnostics": self.analyse(fichier, texte).diagnostics()}
        if methode == "completer":
            return {"items": self.analyse(fichier, texte, ligne).completions(ligne, colonne)}
        if methode == "survoler":
            return {"survol": self.analyse(fichier, texte, ligne).survol(ligne, colonne)}
        if methode == "signature":
            return {"signature": self.analyse(fichier, texte, ligne).signature(ligne, colonne)}
        if methode == "definition":
            return {"definition": self.analyse(fichier, texte, ligne).definition(ligne, colonne)}
        if methode == "fermer":
            self.cache.pop(fichier, None)
            self.textes.pop(fichier, None)
            return {}
        raise ValueError(f"méthode inconnue : {methode}")

    def boucle(self, entree=None, sortie=None) -> None:
        entree = entree or sys.stdin
        sortie = sortie or sys.stdout
        for ligne in entree:
            ligne = ligne.strip()
            if not ligne:
                continue
            try:
                req = json.loads(ligne)
            except json.JSONDecodeError:
                continue
            reponse = {"id": req.get("id")}
            try:
                reponse["resultat"] = self.traiter(req)
            except Exception as e:  # le serveur ne doit jamais mourir sur une requête
                reponse["erreur"] = f"{type(e).__name__}: {e}"
                reponse["trace"] = traceback.format_exc()
            sortie.write(json.dumps(reponse, ensure_ascii=False) + "\n")
            sortie.flush()


def main() -> int:
    Serveur().boucle()
    return 0
