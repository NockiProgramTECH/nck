"""Analyseur lexical : transforme le texte source en liste de jetons."""

from dataclasses import dataclass
from .erreurs import ErreurLexicale

MOTS_CLES = {
    "variable", "constante", "fonction", "retourner",
    "si", "sinon", "tantque", "pour", "dans", "fin",
    "arreter", "continuer", "classe", "herite", "essayer", "attraper", "enfin", "lever", "importer", "depuis", "comme", "selon", "cas", "statique", "abstraite", "parent",
    "et", "ou", "non",
    "vrai", "faux", "nul",
}

# Opérateurs classés du plus long au plus court pour l'analyse gloutonne.
OPERATEURS = [
    "...", "..", "??", "->", "==", "!=", "<=", ">=", "+=", "-=", "*=", "/=",
    "+", "-", "*", "/", "%", "=", "<", ">",
    "(", ")", "[", "]", "{", "}", ",", ":", ";", ".", "@", "?",
]


@dataclass
class Jeton:
    genre: str          # 'nombre', 'texte', 'ident', 'motcle', 'op', 'nl', 'fin_fichier'
    valeur: object
    ligne: int
    colonne: int

    def __repr__(self) -> str:  # pragma: no cover - debug
        return f"Jeton({self.genre}, {self.valeur!r}, {self.ligne}:{self.colonne})"


ECHAPPEMENTS = {"n": "\n", "t": "\t", "r": "\r", "\\": "\\", '"': '"', "'": "'", "0": "\0"}


def lexer(source: str, fichier: str = "<entrée>") -> list[Jeton]:
    jetons: list[Jeton] = []
    i, n = 0, len(source)
    ligne, debut_ligne = 1, 0

    def col() -> int:
        return i - debut_ligne + 1

    while i < n:
        c = source[i]

        # Espaces
        if c in " \t\r":
            i += 1
            continue

        # Fin de ligne
        if c == "\n":
            jetons.append(Jeton("nl", "\n", ligne, col()))
            i += 1
            ligne += 1
            debut_ligne = i
            continue

        # Commentaires // ... et /* ... */ et # ...
        if c == "#" or source.startswith("//", i):
            while i < n and source[i] != "\n":
                i += 1
            continue
        if source.startswith("/*", i):
            l0, c0 = ligne, col()
            i += 2
            while i < n and not source.startswith("*/", i):
                if source[i] == "\n":
                    ligne += 1
                    debut_ligne = i + 1
                i += 1
            if i >= n:
                raise ErreurLexicale("commentaire /* non fermé", l0, c0, fichier)
            i += 2
            continue

        # Nombres
        if c.isdigit():
            l0, c0 = ligne, col()
            j = i
            while j < n and (source[j].isdigit() or source[j] == "_"):
                j += 1
            est_reel = False
            if j < n and source[j] == "." and j + 1 < n and source[j + 1].isdigit():
                est_reel = True
                j += 1
                while j < n and (source[j].isdigit() or source[j] == "_"):
                    j += 1
            if j < n and source[j] in "eE":
                k = j + 1
                if k < n and source[k] in "+-":
                    k += 1
                if k < n and source[k].isdigit():
                    est_reel = True
                    j = k
                    while j < n and source[j].isdigit():
                        j += 1
            brut = source[i:j].replace("_", "")
            jetons.append(Jeton("nombre", float(brut) if est_reel else int(brut), l0, c0))
            i = j
            continue

        # Textes formatés : f"Bonjour {nom}"
        if c == "f" and i + 1 < n and source[i + 1] in "\"'":
            l0, c0 = ligne, col()
            quote = source[i + 1]
            i += 2
            parties: list = []          # str (texte brut) ou tuple (code, ligne, colonne)
            courant: list[str] = []
            while True:
                if i >= n or source[i] == "\n":
                    raise ErreurLexicale("texte formaté non fermé", l0, c0, fichier)
                ch = source[i]
                if ch == quote:
                    i += 1
                    break
                if ch == "\\":
                    i += 1
                    if i >= n:
                        raise ErreurLexicale("texte formaté non fermé", l0, c0, fichier)
                    courant.append(ECHAPPEMENTS.get(source[i], "\\" + source[i]))
                    i += 1
                    continue
                if ch == "{":
                    if source.startswith("{{", i):
                        courant.append("{")
                        i += 2
                        continue
                    if courant:
                        parties.append("".join(courant))
                        courant = []
                    lc, cc = ligne, col() + 1
                    i += 1
                    debut, prof = i, 1
                    while i < n and source[i] != "\n":
                        if source[i] in "\"'":           # saute les textes imbriqués
                            q = source[i]
                            i += 1
                            while i < n and source[i] not in (q, "\n"):
                                i += 1
                        elif source[i] == "{":
                            prof += 1
                        elif source[i] == "}":
                            prof -= 1
                            if prof == 0:
                                break
                        i += 1
                    if i >= n or source[i] != "}":
                        raise ErreurLexicale("'}' manquant dans le texte formaté", lc, cc - 1, fichier)
                    code = source[debut:i]
                    if not code.strip():
                        raise ErreurLexicale("expression vide entre { } dans le texte formaté", lc, cc - 1, fichier)
                    parties.append((code, lc, cc))
                    i += 1
                    continue
                if ch == "}":
                    if source.startswith("}}", i):
                        courant.append("}")
                        i += 2
                        continue
                    raise ErreurLexicale("'}' seul dans un texte formaté : écrivez '}}' pour un '}' littéral", ligne, col(), fichier)
                courant.append(ch)
                i += 1
            if courant:
                parties.append("".join(courant))
            jetons.append(Jeton("ftexte", parties, l0, c0))
            continue

        # Identifiants et mots-clés
        if c.isalpha() or c == "_":
            l0, c0 = ligne, col()
            j = i
            while j < n and (source[j].isalnum() or source[j] == "_"):
                j += 1
            mot = source[i:j]
            jetons.append(Jeton("motcle" if mot in MOTS_CLES else "ident", mot, l0, c0))
            i = j
            continue

        # Chaînes de caractères
        if c in "\"'":
            l0, c0 = ligne, col()
            quote = c
            i += 1
            morceaux: list[str] = []
            while True:
                if i >= n or source[i] == "\n":
                    raise ErreurLexicale("chaîne de caractères non fermée", l0, c0, fichier)
                ch = source[i]
                if ch == quote:
                    i += 1
                    break
                if ch == "\\":
                    i += 1
                    if i >= n:
                        raise ErreurLexicale("chaîne de caractères non fermée", l0, c0, fichier)
                    e = source[i]
                    morceaux.append(ECHAPPEMENTS.get(e, "\\" + e))
                    i += 1
                    continue
                morceaux.append(ch)
                i += 1
            jetons.append(Jeton("texte", "".join(morceaux), l0, c0))
            continue

        # Opérateurs et ponctuation
        for op in OPERATEURS:
            if source.startswith(op, i):
                jetons.append(Jeton("op", op, ligne, col()))
                i += len(op)
                break
        else:
            raise ErreurLexicale(f"caractère inattendu {c!r}", ligne, col(), fichier)

    jetons.append(Jeton("fin_fichier", None, ligne, col()))
    return jetons
