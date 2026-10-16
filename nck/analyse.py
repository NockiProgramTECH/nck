"""Analyse d'un fichier pour l'éditeur : diagnostics, autocomplétion, survol, aide à la signature, définition.

Tout est calculé à partir des enregistrements laissés par le vérificateur de types.
Les positions reçues et renvoyées sont en base 1 (ligne, colonne), comme les erreurs NCK.
"""

import re

from .documentation import METHODES_PAR_TYPE, MOTS_CLES_DOC, NATIFS_DOC, TYPES_DOC
from .erreurs import ErreurNck
from .lexeur import MOTS_CLES
from .modules import Chargeur
from .natifs import NATIFS
from .parseur import parser
from .types_nck import TypeClasse, TypeEnum, TypeFonction, TypeModule
from .verificateur import TYPE_META_CLASSE, Verificateur

IDENT = r"[A-Za-z_][A-Za-z0-9_]*"
TYPES_SIMPLES = ["entier", "reel", "texte", "booleen", "liste", "dico", "fonction", "quelconque", "rien"]

# Genres de symboles -> genre d'élément de complétion (noms VS Code)
GENRE_COMPLETION = {
    "variable": "Variable", "constante": "Constant", "paramètre": "Variable", "fonction": "Function",
    "classe": "Class", "module": "Module", "natif": "Function", "champ": "Field", "méthode": "Method",
    "soi": "Variable", "parent": "Variable", "statique": "Method", "motcle": "Keyword", "type": "TypeParameter",
}


def _bloc_code(texte: str) -> str:
    return f"```nck\n{texte}\n```"


def _parametres_de(signature: str) -> list[str]:
    """Découpe 'f(a: entier, b: liste<texte> = …) -> T' en ['a: entier', 'b: liste<texte> = …']."""
    debut = signature.find("(")
    if debut < 0:
        return []
    prof, fin = 0, -1
    for i in range(debut, len(signature)):
        c = signature[i]
        if c in "(<[":
            prof += 1
        elif c in ")>]":
            prof -= 1
            if prof == 0:
                fin = i
                break
    if fin < 0:
        return []
    interieur = signature[debut + 1:fin]
    params, courant, prof = [], "", 0
    for c in interieur:
        if c in "(<[":
            prof += 1
        elif c in ")>]":
            prof -= 1
        if c == "," and prof == 0:
            params.append(courant.strip())
            courant = ""
        else:
            courant += c
    if courant.strip():
        params.append(courant.strip())
    return params


class Analyse:
    def __init__(self, source: str, fichier: str = "<éditeur>", ligne_curseur: int | None = None):
        self.source = source
        self.fichier = fichier
        self.lignes = source.splitlines()
        self.erreur: ErreurNck | None = None
        self.verif = self._analyser(source)
        if self.erreur is not None:
            # Analyse tolérante : on neutralise la ligne en cours de frappe puis les lignes fautives
            # (jusqu'à 5 fois) pour garder un maximum de symboles. Les diagnostics restent ceux de la 1re passe.
            erreur_initiale = self.erreur
            lignes = list(self.lignes)
            meilleur = self.verif
            a_essayer = [ligne_curseur] if ligne_curseur else []
            for _ in range(5):
                e = self.erreur
                if not a_essayer:
                    if e is None or e.fichier != fichier:
                        break
                    a_essayer.append(e.ligne)
                num = a_essayer.pop(0)
                if not 0 < num <= len(lignes) or not lignes[num - 1].strip():
                    continue
                if lignes[num - 1].rstrip().endswith(":"):
                    break   # ligne ouvrant un bloc : on ne peut pas la supprimer sans casser la structure
                lignes[num - 1] = ""
                self.erreur = None
                v = self._analyser("\n".join(lignes))
                if len(v.enregistrements) >= len(meilleur.enregistrements):
                    meilleur = v
                if self.erreur is None:
                    break
            self.verif = meilleur
            self.erreur = erreur_initiale

    def _analyser(self, source: str) -> Verificateur:
        verif = Verificateur(self.fichier, chargeur=Chargeur())
        try:
            prog = parser(source, self.fichier)
            verif.verifier_programme(prog)
        except ErreurNck as e:
            self.erreur = e
        except RecursionError:
            self.erreur = None
        return verif

    # ----- diagnostics -----

    def diagnostics(self) -> list[dict]:
        if self.erreur is None:
            return []
        e = self.erreur
        if e.fichier != self.fichier:
            # erreur dans un module importé : on la signale sur la ligne 1 du fichier courant
            return [{"ligne": 1, "colonne": 1, "longueur": 1, "message": f"{e.nom} dans {e.fichier}:{e.ligne} : {e.message}",
                     "gravite": "erreur"}]
        longueur = 1
        if 0 < e.ligne <= len(self.lignes):
            m = re.match(IDENT, self.lignes[e.ligne - 1][e.colonne - 1:]) if e.colonne > 0 else None
            if m:
                longueur = len(m.group(0))
        return [{"ligne": e.ligne, "colonne": max(e.colonne, 1), "longueur": longueur,
                 "message": f"{e.nom} : {e.message}", "gravite": "erreur"}]

    # ----- aides -----

    def mot_a(self, ligne: int, colonne: int) -> tuple[str, int] | None:
        """Identifiant sous le curseur et sa colonne de début."""
        if not 0 < ligne <= len(self.lignes):
            return None
        texte = self.lignes[ligne - 1]
        for m in re.finditer(IDENT, texte):
            if m.start() < colonne <= m.end() or m.start() == colonne - 1:
                return m.group(0), m.start() + 1
        return None

    def enregistrement_a(self, ligne: int, colonne: int) -> dict | None:
        meilleur = None
        for e in self.verif.enregistrements:
            if e["ligne"] == ligne and e["colonne"] <= colonne <= e["colonne"] + e["longueur"]:
                if meilleur is None or e["declaration"]:
                    meilleur = e
        return meilleur

    def symbole_visible(self, nom: str, ligne: int) -> dict | None:
        """Dernière déclaration de `nom` visible à la ligne donnée (portée approximative)."""
        candidats = [e for e in self.verif.enregistrements
                     if e["declaration"] and e["nom"] == nom and self._dans_portee(e, ligne)]
        if not candidats:
            return None
        # on préfère la déclaration la plus proche au-dessus, sinon une fonction/classe hissée
        avant = [e for e in candidats if e["ligne"] <= ligne]
        return max(avant, key=lambda e: e["ligne"]) if avant else candidats[0]

    @staticmethod
    def _dans_portee(e: dict, ligne: int) -> bool:
        p = e["portee"]
        return p is None or p[0] <= ligne <= p[1]

    def classe_a(self, ligne: int) -> TypeClasse | None:
        for e in self.verif.enregistrements:
            if e["classe"] is not None and e["portee"] and e["portee"][0] <= ligne <= e["portee"][1]:
                return e["classe"]
        return None

    def description(self, sym, nom: str) -> str:
        if sym is None:
            return nom
        if sym.genre == "natif" and nom in NATIFS_DOC:
            sig, desc = NATIFS_DOC[nom]
            return _bloc_code(sig) + "\n\n" + desc
        if sym.genre == "classe" and nom in self.verif.classes:
            info = self.verif.classes[nom]
            lignes = [_bloc_code(info.signature())]
            if info.methodes:
                lignes.append("Méthodes : " + ", ".join(f"`{m}`" for m in info.methodes))
            if info.statiques:
                lignes.append("Statiques : " + ", ".join(f"`{nom}.{m}()`" for m in info.statiques))
            if info.constantes:
                lignes.append("Constantes : " + ", ".join(f"`{nom}.{m}`" for m in info.constantes))
            return "\n\n".join(lignes)
        return _bloc_code(sym.description)

    # ----- survol -----

    def survol(self, ligne: int, colonne: int) -> dict | None:
        e = self.enregistrement_a(ligne, colonne)
        if e is not None:
            return {"contenu": self.description(e["symbole"], e["nom"]), "ligne": e["ligne"],
                    "colonne": e["colonne"], "longueur": e["longueur"]}
        mot = self.mot_a(ligne, colonne)
        if mot is None:
            return None
        nom, debut = mot
        if nom in MOTS_CLES_DOC:
            return {"contenu": f"**{nom}** (mot-clé)\n\n{MOTS_CLES_DOC[nom]}", "ligne": ligne, "colonne": debut, "longueur": len(nom)}
        if nom in TYPES_DOC:
            return {"contenu": f"**{nom}** (type)\n\n{TYPES_DOC[nom]}", "ligne": ligne, "colonne": debut, "longueur": len(nom)}
        if nom in NATIFS_DOC:
            sig, desc = NATIFS_DOC[nom]
            return {"contenu": _bloc_code(sig) + "\n\n" + desc, "ligne": ligne, "colonne": debut, "longueur": len(nom)}
        d = self.symbole_visible(nom, ligne)
        if d is not None:
            return {"contenu": self.description(d["symbole"], nom), "ligne": ligne, "colonne": debut, "longueur": len(nom)}
        return None

    # ----- définition -----

    def definition(self, ligne: int, colonne: int) -> dict | None:
        e = self.enregistrement_a(ligne, colonne)
        sym = e["symbole"] if e else None
        if sym is None:
            mot = self.mot_a(ligne, colonne)
            if mot is None:
                return None
            d = self.symbole_visible(mot[0], ligne)
            sym = d["symbole"] if d else None
        if sym is None or sym.position == (0, 0) or sym.genre == "natif":
            return None
        return {"fichier": sym.fichier or self.fichier, "ligne": sym.position[0], "colonne": sym.position[1]}

    # ----- complétion -----

    def completions(self, ligne: int, colonne: int) -> list[dict]:
        texte = self.lignes[ligne - 1][:colonne - 1] if 0 < ligne <= len(self.lignes) else ""
        m = re.search(rf"({IDENT})\s*\.\s*({IDENT})?$", texte)
        if m:
            return self._completions_membres(m.group(1), ligne)
        if re.search(r'(importer|depuis)\s+"[^"]*$', texte):
            return []
        return self._completions_generales(ligne)

    def _item(self, nom: str, genre: str, detail: str = "", doc: str = "", insertion: str | None = None) -> dict:
        return {"nom": nom, "genre": GENRE_COMPLETION.get(genre, "Text"), "detail": detail, "doc": doc,
                "insertion": insertion if insertion is not None else nom}

    def _completions_membres(self, base: str, ligne: int) -> list[dict]:
        t = None
        items: list[dict] = []
        prive_ok = base in ("soi", "parent")
        if base == "soi":
            t = self.classe_a(ligne)
        elif base == "parent":
            t = self.classe_a(ligne)
            info = self.verif.classes.get(t.nom) if isinstance(t, TypeClasse) else None
            t = info.parent.type if info is not None and info.parent is not None else None
        elif base in self.verif.classes:
            # `Classe.` : méthodes statiques et constantes
            info = self.verif.classes[base]
            for n, tc in info.constantes.items():
                items.append(self._item(n, "constante", str(tc), info.descriptions.get(n, "")))
            for n, tm in info.statiques.items():
                items.append(self._item(n, "fonction", str(tm), info.descriptions.get(n, ""),
                                        insertion=n + ("()" if not tm.parametres else "(")))
            return items
        elif base in self.verif.enums:
            te = self.verif.enums[base]
            for i, v in enumerate(te.valeurs):
                items.append(self._item(v, "constante", base, f"{base}.{v} (valeur {i} de l'énumération)"))
            items.append(self._item("valeurs", "champ", f"liste<{base}>", "Toutes les valeurs de l'énumération, dans l'ordre."))
            return items
        else:
            d = self.symbole_visible(base, ligne)
            if d is not None and d["symbole"] is not None:
                t = d["symbole"].type
        if isinstance(t, TypeEnum):
            items.append(self._item("nom", "champ", "texte", "Nom de la valeur (ex : \"ROUGE\")."))
            items.append(self._item("indice", "champ", "entier", "Position de la valeur dans l'énumération (0, 1, 2…)."))
            return items
        if t is not None and not isinstance(t, (TypeClasse, TypeModule)) and t.nom in METHODES_PAR_TYPE:
            # notation méthode sur les valeurs de base : liste.ajouter(x), texte.majuscule()…
            for n in METHODES_PAR_TYPE[t.nom]:
                sig, doc = NATIFS_DOC.get(n, (n + "(...)", ""))
                # signature sans le premier paramètre (la valeur elle-même)
                interieur = sig[sig.index("(") + 1:sig.rindex(")")]
                reste = interieur.split(", ", 1)[1] if ", " in interieur else ""
                retour = sig[sig.rindex(")") + 1:]
                items.append(self._item(n, "méthode", f"({reste}){retour}", doc, insertion=n + ("()" if not reste else "(")))
            return items
        if isinstance(t, TypeClasse) and t.nom in self.verif.classes:
            info = self.verif.classes[t.nom]
            for n, tc in info.champs.items():
                if n.startswith("_") and not prive_ok:
                    continue
                items.append(self._item(n, "champ", str(tc), info.descriptions.get(n, "")))
            for n, tm in info.methodes.items():
                if n.startswith("_") and not prive_ok:
                    continue
                items.append(self._item(n, "méthode", str(tm), info.descriptions.get(n, ""),
                                        insertion=n + ("()" if not tm.parametres else "(")))
        elif isinstance(t, TypeModule):
            mod = self.verif.chargeur.modules.get(t.chemin)
            if mod is not None:
                for n, sym in sorted(mod.exports.items()):
                    items.append(self._item(n, sym.genre, str(sym.type) if sym.genre != "classe" else "classe", sym.description))
        return items

    def _completions_generales(self, ligne: int) -> list[dict]:
        items: list[dict] = []
        vus: set[str] = set()
        # symboles utilisateur visibles (déclarations locales avant la ligne + hissées)
        for e in sorted(self.verif.enregistrements, key=lambda e: -e["ligne"]):
            if not e["declaration"] or e["nom"] in vus or e["symbole"] is None:
                continue
            sym = e["symbole"]
            if not self._dans_portee(e, ligne):
                continue
            if e["ligne"] > ligne and sym.genre not in ("fonction", "classe"):
                continue
            vus.add(e["nom"])
            detail = str(sym.type) if sym.genre not in ("classe", "module") else sym.genre
            ins = e["nom"]
            if isinstance(sym.type, TypeFonction):
                ins = e["nom"] + ("()" if not sym.type.parametres else "(")
            elif sym.genre == "classe":
                ins = e["nom"] + "("
            items.append(self._item(e["nom"], sym.genre, detail, self.description(sym, e["nom"]), ins))
        for nom in NATIFS:
            if nom in vus:
                continue
            sig, desc = NATIFS_DOC.get(nom, (nom + "(...)", ""))
            sans_param = "()" in sig.split("->")[0]
            items.append(self._item(nom, "natif", sig, desc, nom + ("()" if sans_param else "(")))
        items.append(self._item("Erreur", "classe", "classe Erreur(message: texte)", TYPES_DOC["Erreur"], "Erreur("))
        for mot in sorted(MOTS_CLES):
            items.append(self._item(mot, "motcle", "mot-clé", MOTS_CLES_DOC.get(mot, "")))
        items.append(self._item("soi", "soi", "objet courant", MOTS_CLES_DOC["soi"]))
        for t in TYPES_SIMPLES:
            items.append(self._item(t, "type", "type", TYPES_DOC.get(t, "")))
        return items

    # ----- aide à la signature -----

    def signature(self, ligne: int, colonne: int) -> dict | None:
        if not 0 < ligne <= len(self.lignes):
            return None
        texte = self.lignes[ligne - 1][:colonne - 1]
        # remonte jusqu'à la parenthèse ouvrante non fermée, en comptant les virgules de niveau 0
        prof, virgules, i = 0, 0, len(texte) - 1
        dans_texte = None
        while i >= 0:
            c = texte[i]
            if dans_texte:
                if c == dans_texte and (i == 0 or texte[i - 1] != "\\"):
                    dans_texte = None
            elif c in "\"'":
                dans_texte = c
            elif c in ")]}":
                prof += 1
            elif c in "([{":
                if prof == 0:
                    if c != "(":
                        return None
                    break
                prof -= 1
            elif c == "," and prof == 0:
                virgules += 1
            i -= 1
        if i < 0:
            return None
        avant = texte[:i].rstrip()
        m = re.search(rf"(?:({IDENT})\s*\.\s*)?({IDENT})$", avant)
        if not m:
            return None
        base, nom = m.group(1), m.group(2)
        sig = self._signature_de(base, nom, ligne)
        if sig is None:
            return None
        label, doc = sig
        params = _parametres_de(label)
        return {"label": label, "doc": doc, "parametres": params, "actif": min(virgules, max(len(params) - 1, 0))}

    def _signature_de(self, base: str | None, nom: str, ligne: int) -> tuple[str, str] | None:
        if base is not None:
            t = self.classe_a(ligne) if base == "soi" else None
            if t is None:
                d = self.symbole_visible(base, ligne)
                t = d["symbole"].type if d and d["symbole"] else None
            if isinstance(t, TypeClasse) and t.nom in self.verif.classes:
                info = self.verif.classes[t.nom]
                if nom in info.methodes:
                    return info.descriptions[nom], ""
                return None
            if isinstance(t, TypeModule):
                mod = self.verif.chargeur.modules.get(t.chemin)
                sym = mod.exports.get(nom) if mod else None
                if sym is not None:
                    return self._signature_symbole(sym, nom)
            return None
        d = self.symbole_visible(nom, ligne)
        if d is not None and d["symbole"] is not None:
            return self._signature_symbole(d["symbole"], nom)
        if nom in NATIFS_DOC:
            return NATIFS_DOC[nom]
        if nom == "Erreur":
            return "Erreur(message: texte)", TYPES_DOC["Erreur"]
        return None

    def _signature_symbole(self, sym, nom: str) -> tuple[str, str] | None:
        if sym.genre == "natif":
            return NATIFS_DOC.get(nom)
        if sym.genre == "classe" and nom in self.verif.classes:
            return self.verif.classes[nom].signature(), "constructeur"
        if isinstance(sym.type, TypeFonction):
            return sym.description, ""
        return None
