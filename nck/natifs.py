"""Fonctions natives (intégrées) du langage NCK."""

import math
import random
import sys
import time
from dataclasses import dataclass
from typing import Callable

from .erreurs import ErreurExecution, ErreurType
from .types_nck import (
    BOOLEEN, ENTIER, QUELCONQUE, REEL, RIEN, TEXTE, Type, TypeFonction, cle_de, compatible, element_de,
    est_dico, est_liste, est_numerique, est_optionnel, liste_de, optionnel_de, sans_nul, unifier, valeur_de,
)


# ---------- représentation des valeurs ----------

def vers_texte(v: object) -> str:
    if v is None:
        return "nul"
    if v is True:
        return "vrai"
    if v is False:
        return "faux"
    if isinstance(v, float):
        if v != v:
            return "NaN"
        if v in (math.inf, -math.inf):
            return "inf" if v > 0 else "-inf"
        return repr(v)
    if isinstance(v, list):
        return "[" + ", ".join(_repr_elem(x) for x in v) + "]"
    if isinstance(v, dict):
        return "{" + ", ".join(f"{_repr_elem(k)}: {_repr_elem(x)}" for k, x in v.items()) + "}"
    if isinstance(v, ObjetNck):
        if "texte" in v.classe.methodes:
            return str(v.classe.methodes["texte"](v))
        if v.classe.nom == "Erreur" or "Erreur" in v.classe.ancetres:
            return f"{v.classe.nom} : {v.champs.get('message', '')}"
        return v.classe.nom + "(" + ", ".join(f"{k}={_repr_elem(x)}" for k, x in v.champs.items()) + ")"
    if isinstance(v, ClasseNck):
        return f"<classe {v.nom}>"
    if isinstance(v, ValeurEnum):
        return f"{v.enum}.{v.nom}"
    if isinstance(v, EnumNck):
        return f"<enumeration {v.nom}>"
    if isinstance(v, ParentNck):
        return f"<parent {v.classe.nom}>"
    if isinstance(v, ModuleNck):
        return f"<module {v.nom}>"
    if isinstance(v, FonctionNck):
        return f"<fonction {v.nom}>"
    if isinstance(v, Natif):
        return f"<fonction native {v.nom}>"
    return str(v)


def _repr_elem(v: object) -> str:
    if isinstance(v, str):
        return '"' + v.replace("\\", "\\\\").replace('"', '\\"') + '"'
    return vers_texte(v)


def nom_type_valeur(v: object) -> str:
    if v is None:
        return "nul"
    if isinstance(v, bool):
        return "booleen"
    if isinstance(v, int):
        return "entier"
    if isinstance(v, float):
        return "reel"
    if isinstance(v, str):
        return "texte"
    if isinstance(v, list):
        return "liste"
    if isinstance(v, dict):
        return "dico"
    if isinstance(v, (FonctionNck, Natif)):
        return "fonction"
    if isinstance(v, ObjetNck):
        return v.classe.nom
    if isinstance(v, ClasseNck):
        return "classe"
    if isinstance(v, ValeurEnum):
        return v.enum
    if isinstance(v, EnumNck):
        return "enumeration"
    if isinstance(v, ModuleNck):
        return "module"
    return type(v).__name__


class ClasseNck:
    """Classe définie par l'utilisateur (remplie par l'interpréteur)."""

    __slots__ = ("nom", "ancetres", "champs", "types_champs", "defauts", "methodes", "construire",
                 "parent", "statiques", "constantes", "abstraites")

    def __init__(self, nom: str, ancetres: tuple[str, ...]):
        self.nom = nom
        self.ancetres = ancetres
        self.champs: list[str] = []
        self.types_champs: dict[str, object] = {}
        self.defauts: dict[str, Callable] = {}       # nom -> fonction () -> valeur
        self.methodes: dict[str, Callable] = {}      # nom -> fonction (objet, *args)
        self.construire: Callable = None             # type: ignore[assignment]
        self.parent: "ClasseNck | None" = None
        self.statiques: dict[str, object] = {}       # méthodes statiques (callables)
        self.constantes: dict[str, object] = {}      # constantes de classe
        self.abstraites: set[str] = set()            # méthodes abstraites non implémentées

    def est(self, nom: str) -> bool:
        return self.nom == nom or nom in self.ancetres


class ValeurEnum:
    """Une valeur d'énumération : `Couleur.ROUGE`. Une seule instance par valeur (comparaison par identité)."""

    __slots__ = ("enum", "nom", "indice")

    def __init__(self, enum: str, nom: str, indice: int):
        self.enum = enum
        self.nom = nom
        self.indice = indice

    def __lt__(self, autre):
        if isinstance(autre, ValeurEnum) and autre.enum == self.enum:
            return self.indice < autre.indice
        return NotImplemented

    def __repr__(self):
        return f"{self.enum}.{self.nom}"


class EnumNck:
    """Une énumération : `Couleur`, avec ses valeurs."""

    __slots__ = ("nom", "valeurs", "par_nom")

    def __init__(self, nom: str, noms: list[str]):
        self.nom = nom
        self.valeurs = [ValeurEnum(nom, n, i) for i, n in enumerate(noms)]
        self.par_nom = {v.nom: v for v in self.valeurs}


class ParentNck:
    """Proxy `parent` dans une méthode : accède aux méthodes de la classe parente pour l'objet courant."""

    __slots__ = ("objet", "classe")

    def __init__(self, objet: "ObjetNck", classe: ClasseNck):
        self.objet = objet
        self.classe = classe

    def __call__(self, *args, **kwargs):
        return self.construire(*args, **kwargs)


class ObjetNck:
    """Instance d'une classe NCK. Les opérateurs délèguent aux méthodes spéciales si elles existent."""

    __slots__ = ("classe", "champs")

    def __init__(self, classe: ClasseNck, champs: dict):
        self.classe = classe
        self.champs = champs

    def _methode(self, nom: str):
        return self.classe.methodes.get(nom)

    def __eq__(self, autre):
        m = self._methode("egal")
        if m is not None:
            return bool(m(self, autre))
        return self is autre

    def __ne__(self, autre):
        return not self.__eq__(autre)

    def __hash__(self):
        m = self._methode("hachage")
        return hash(m(self)) if m is not None else id(self)

    def __lt__(self, autre):
        m = self._methode("inferieur")
        if m is None:
            raise ErreurExecution(f"la classe '{self.classe.nom}' ne définit pas 'inferieur' : comparaison impossible")
        return bool(m(self, autre))

    def __gt__(self, autre):
        if isinstance(autre, ObjetNck):
            return autre.__lt__(self)
        return NotImplemented

    def __le__(self, autre):
        return self.__lt__(autre) or self.__eq__(autre)

    def __ge__(self, autre):
        return self.__gt__(autre) or self.__eq__(autre)

    def _op(self, nom: str, autre):
        m = self._methode(nom)
        if m is None:
            raise ErreurExecution(f"la classe '{self.classe.nom}' ne définit pas la méthode '{nom}'")
        return m(self, autre)

    def __add__(self, autre):
        return self._op("plus", autre)

    def __sub__(self, autre):
        return self._op("moins", autre)

    def __mul__(self, autre):
        return self._op("fois", autre)

    def __truediv__(self, autre):
        return self._op("divise", autre)

    def __mod__(self, autre):
        return self._op("modulo", autre)

    def __neg__(self):
        return self._op("oppose", None) if "oppose" in self.classe.methodes else self._op("oppose", None)


OPERATEURS_CLASSE = {"+": "plus", "-": "moins", "*": "fois", "/": "divise", "%": "modulo",
                     "==": "egal", "!=": "egal", "<": "inferieur", ">": "inferieur", "<=": "inferieur", ">=": "inferieur"}


class ModuleNck:
    """Module importé : donne accès aux déclarations de son fichier."""

    __slots__ = ("nom", "env")

    def __init__(self, nom: str, env):
        self.nom = nom
        self.env = env


class FonctionNck:
    """Fonction définie par l'utilisateur (remplie par l'interpréteur)."""

    __slots__ = ("nom", "appeler", "arite", "arite_min")

    def __init__(self, nom: str, arite: int, appeler: Callable):
        self.nom = nom
        self.arite = arite          # nombre maximum d'arguments (-1 : variable)
        self.arite_min = arite      # nombre minimum d'arguments
        self.appeler = appeler

    def __call__(self, *args):
        return self.appeler(*args)


@dataclass
class Natif:
    nom: str
    fn: Callable
    verifier: Callable            # (types_args: list[Type], erreur: Callable[[str], ErreurType]) -> Type
    attendu: Callable | None = None   # (index, types_precedents) -> type attendu de l'argument (typage des lambdas)

    def __call__(self, *args):
        return self.fn(*args)


NATIFS: dict[str, Natif] = {}


def natif(nom: str, verifier: Callable, attendu: Callable | None = None):
    def deco(fn):
        NATIFS[nom] = Natif(nom, fn, verifier, attendu)
        return fn
    return deco


# ---------- aides pour les vérificateurs ----------

def _arite(nom: str, types: list[Type], mini: int, maxi: int | None, erreur):
    n = len(types)
    if n < mini or (maxi is not None and n > maxi):
        if maxi == mini:
            attendu = f"{mini} argument(s)"
        elif maxi is None:
            attendu = f"au moins {mini} argument(s)"
        else:
            attendu = f"entre {mini} et {maxi} arguments"
        raise erreur(f"'{nom}' attend {attendu}, mais {n} fourni(s)")


def _exiger(nom: str, t: Type, attendu: Type | tuple[Type, ...], position: int, erreur):
    attendus = attendu if isinstance(attendu, tuple) else (attendu,)
    if t == QUELCONQUE or any(compatible(t, a) for a in attendus):
        return
    noms = " ou ".join(str(a) for a in attendus)
    raise erreur(f"argument {position} de '{nom}' : {noms} attendu, mais {t} fourni")


def _exiger_liste(nom: str, t: Type, position: int, erreur):
    if t != QUELCONQUE and not est_liste(t):
        raise erreur(f"argument {position} de '{nom}' : liste attendue, mais {t} fournie")


def simple(nom: str, params: list[Type | tuple[Type, ...]], retour: Type):
    def verifier(types, erreur):
        _arite(nom, types, len(params), len(params), erreur)
        for i, (t, p) in enumerate(zip(types, params), 1):
            _exiger(nom, t, p, i, erreur)
        return retour
    return verifier


# ---------- entrées / sorties ----------

def _v_ecrire(types, erreur):
    return RIEN


@natif("ecrire", _v_ecrire)
def _ecrire(*args):
    sys.stdout.write(" ".join(vers_texte(a) for a in args) + "\n")
    return None


def _v_lire(types, erreur):
    _arite("lire", types, 0, 1, erreur)
    if types:
        _exiger("lire", types[0], TEXTE, 1, erreur)
    return TEXTE


@natif("lire", _v_lire)
def _lire(invite: str = ""):
    try:
        sys.stdout.flush()
        return input(invite)
    except EOFError:
        return ""


# ---------- conversions ----------

@natif("texte", simple("texte", [QUELCONQUE], TEXTE))
def _texte(v):
    return vers_texte(v)


@natif("entier", simple("entier", [QUELCONQUE], ENTIER))
def _entier(v):
    if isinstance(v, bool):
        return 1 if v else 0
    if isinstance(v, int):
        return v
    if isinstance(v, float):
        if v != v or v in (math.inf, -math.inf):
            raise ErreurExecution(f"impossible de convertir {vers_texte(v)} en entier")
        return int(v)
    if isinstance(v, str):
        s = v.strip()
        try:
            return int(s)
        except ValueError:
            try:
                return int(float(s))
            except ValueError:
                raise ErreurExecution(f"impossible de convertir le texte {v!r} en entier") from None
    raise ErreurExecution(f"impossible de convertir une valeur de type {nom_type_valeur(v)} en entier")


@natif("reel", simple("reel", [QUELCONQUE], REEL))
def _reel(v):
    if isinstance(v, bool):
        return 1.0 if v else 0.0
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, str):
        try:
            return float(v.strip().replace(",", "."))
        except ValueError:
            raise ErreurExecution(f"impossible de convertir le texte {v!r} en reel") from None
    raise ErreurExecution(f"impossible de convertir une valeur de type {nom_type_valeur(v)} en reel")


@natif("booleen", simple("booleen", [QUELCONQUE], BOOLEEN))
def _booleen(v):
    if isinstance(v, str):
        if v.strip().lower() in ("vrai", "true", "1", "oui"):
            return True
        if v.strip().lower() in ("faux", "false", "0", "non", ""):
            return False
        raise ErreurExecution(f"impossible de convertir le texte {v!r} en booleen")
    return bool(v)


@natif("type_de", simple("type_de", [QUELCONQUE], TEXTE))
def _type_de(v):
    return nom_type_valeur(v)


def _v_est_un(types, erreur):
    _arite("est_un", types, 2, 2, erreur)
    if types[1] != QUELCONQUE and types[1].nom != "classe":
        raise erreur(f"argument 2 de 'est_un' : une classe attendue (ex : est_un(x, Personne)), mais {types[1]} fourni")
    return BOOLEEN


@natif("est_un", _v_est_un)
def _est_un(v, classe):
    if not isinstance(classe, ClasseNck):
        raise ErreurExecution(f"'est_un' attend une classe en 2e argument, mais {nom_type_valeur(classe)} fourni")
    return isinstance(v, ObjetNck) and v.classe.est(classe.nom)


# ---------- listes et textes ----------

def _v_longueur(types, erreur):
    _arite("longueur", types, 1, 1, erreur)
    t = types[0]
    if t != QUELCONQUE and t != TEXTE and not est_liste(t) and not est_dico(t):
        raise erreur(f"'longueur' attend une liste, un dico ou un texte, mais {t} fourni")
    return ENTIER


@natif("longueur", _v_longueur)
def _longueur(v):
    if isinstance(v, (str, list, dict)):
        return len(v)
    raise ErreurExecution(f"'longueur' attend une liste, un dico ou un texte, mais {nom_type_valeur(v)} fourni")


def _v_intervalle(types, erreur):
    _arite("intervalle", types, 1, 3, erreur)
    for i, t in enumerate(types, 1):
        _exiger("intervalle", t, ENTIER, i, erreur)
    return liste_de(ENTIER)


@natif("intervalle", _v_intervalle)
def _intervalle(*args):
    try:
        return list(range(*args))
    except ValueError:
        raise ErreurExecution("le pas d'un intervalle ne peut pas être 0") from None


def _v_ajouter(types, erreur):
    _arite("ajouter", types, 2, 2, erreur)
    _exiger_liste("ajouter", types[0], 1, erreur)
    if est_liste(types[0]):
        elem = element_de(types[0])
        if not compatible(types[1], elem):
            raise erreur(f"impossible d'ajouter un {types[1]} dans une {types[0]}")
    return RIEN


@natif("ajouter", _v_ajouter)
def _ajouter(l, v):
    if not isinstance(l, list):
        raise ErreurExecution(f"'ajouter' attend une liste, mais {nom_type_valeur(l)} fourni")
    l.append(v)
    return None


def _v_retirer(types, erreur):
    _arite("retirer", types, 1, 2, erreur)
    if est_dico(types[0]):
        _arite("retirer", types, 2, 2, erreur)
        _exiger("retirer", types[1], cle_de(types[0]), 2, erreur)
        return valeur_de(types[0])
    _exiger_liste("retirer", types[0], 1, erreur)
    if len(types) == 2:
        _exiger("retirer", types[1], ENTIER, 2, erreur)
    return element_de(types[0])


@natif("retirer", _v_retirer)
def _retirer(l, i=-1):
    if isinstance(l, dict):
        try:
            return l.pop(i)
        except KeyError:
            raise ErreurExecution(f"clé {_repr_elem(i)} introuvable dans le dictionnaire") from None
    if not isinstance(l, list):
        raise ErreurExecution(f"'retirer' attend une liste, mais {nom_type_valeur(l)} fourni")
    if not l:
        raise ErreurExecution("impossible de retirer un élément d'une liste vide")
    try:
        return l.pop(i)
    except IndexError:
        raise ErreurExecution(f"index {i} hors limites (taille {len(l)})") from None


def _v_inserer(types, erreur):
    _arite("inserer", types, 3, 3, erreur)
    _exiger_liste("inserer", types[0], 1, erreur)
    _exiger("inserer", types[1], ENTIER, 2, erreur)
    if est_liste(types[0]) and not compatible(types[2], element_de(types[0])):
        raise erreur(f"impossible d'insérer un {types[2]} dans une {types[0]}")
    return RIEN


@natif("inserer", _v_inserer)
def _inserer(l, i, v):
    l.insert(i, v)
    return None


def _v_contient(types, erreur):
    _arite("contient", types, 2, 2, erreur)
    t = types[0]
    if t == TEXTE:
        _exiger("contient", types[1], TEXTE, 2, erreur)
    elif est_dico(t):
        _exiger("contient", types[1], cle_de(t), 2, erreur)
    elif t != QUELCONQUE and not est_liste(t):
        raise erreur(f"'contient' attend une liste, un dico ou un texte, mais {t} fourni")
    return BOOLEEN


@natif("contient", _v_contient)
def _contient(c, v):
    try:
        return v in c
    except TypeError:
        return False


# ---------- dictionnaires ----------

def _v_dico1(nom, resultat):
    def verifier(types, erreur):
        _arite(nom, types, 1, 1, erreur)
        t = types[0]
        if t != QUELCONQUE and not est_dico(t):
            raise erreur(f"'{nom}' attend un dico, mais {t} fourni")
        return resultat(t)
    return verifier


@natif("cles", _v_dico1("cles", lambda t: liste_de(cle_de(t))))
def _cles(d):
    if not isinstance(d, dict):
        raise ErreurExecution(f"'cles' attend un dico, mais {nom_type_valeur(d)} fourni")
    return list(d.keys())


@natif("valeurs", _v_dico1("valeurs", lambda t: liste_de(valeur_de(t))))
def _valeurs(d):
    if not isinstance(d, dict):
        raise ErreurExecution(f"'valeurs' attend un dico, mais {nom_type_valeur(d)} fourni")
    return list(d.values())


def _v_obtenir(types, erreur):
    _arite("obtenir", types, 2, 3, erreur)
    t = types[0]
    if t != QUELCONQUE and not est_dico(t):
        raise erreur(f"'obtenir' attend un dico, mais {t} fourni")
    _exiger("obtenir", types[1], cle_de(t), 2, erreur)
    if len(types) == 3:
        if not compatible(types[2], valeur_de(t)):
            raise erreur(f"argument 3 de 'obtenir' : {valeur_de(t)} attendu, mais {types[2]} fourni")
        return valeur_de(t)
    return optionnel_de(valeur_de(t))   # nul si la clé est absente


@natif("obtenir", _v_obtenir)
def _obtenir(d, k, defaut=None):
    if not isinstance(d, dict):
        raise ErreurExecution(f"'obtenir' attend un dico, mais {nom_type_valeur(d)} fourni")
    return d.get(k, defaut)


def _v_fusionner(types, erreur):
    _arite("fusionner", types, 2, 2, erreur)
    for i, t in enumerate(types, 1):
        if t != QUELCONQUE and not est_dico(t):
            raise erreur(f"argument {i} de 'fusionner' : dico attendu, mais {t} fourni")
    return unifier(types[0], types[1]) if est_dico(types[0]) and est_dico(types[1]) else QUELCONQUE


@natif("fusionner", _v_fusionner)
def _fusionner(a, b):
    r = dict(a)
    r.update(b)
    return r


def _v_position(types, erreur):
    _arite("position", types, 2, 2, erreur)
    t = types[0]
    if t == TEXTE:
        _exiger("position", types[1], TEXTE, 2, erreur)
    elif t != QUELCONQUE and not est_liste(t):
        raise erreur(f"'position' attend une liste ou un texte, mais {t} fourni")
    return ENTIER


@natif("position", _v_position)
def _position(c, v):
    if isinstance(c, str):
        return c.find(v)
    try:
        return c.index(v)
    except ValueError:
        return -1


def _v_liste_meme(types, erreur, nom, dico_ok=False):
    _arite(nom, types, 1, 1, erreur)
    if dico_ok and est_dico(types[0]):
        return types[0]
    _exiger_liste(nom, types[0], 1, erreur)
    return types[0] if est_liste(types[0]) else liste_de(QUELCONQUE)


# ----- fonctions d'ordre supérieur sur les listes (acceptent des fonctions anonymes) -----

def _attendu_element(index: int, types: list[Type]):
    """Pour `f(liste, fonction)` : la fonction attendue reçoit un élément de la liste."""
    if index == 1 and types and est_liste(types[0]):
        return TypeFonction("fonction", (), (element_de(types[0]),), QUELCONQUE)
    if index == 1:
        return TypeFonction("fonction", (), (QUELCONQUE,), QUELCONQUE)
    return None


def _attendu_reduire(index: int, types: list[Type]):
    if index == 1 and types:
        elem = element_de(types[0]) if est_liste(types[0]) else QUELCONQUE
        return TypeFonction("fonction", (), (QUELCONQUE, elem), QUELCONQUE)
    return None


def _v_ordre_sup(nom: str, types, erreur, retour_bool: bool = False):
    _arite(nom, types, 2, 2, erreur)
    _exiger_liste(nom, types[0], 1, erreur)
    elem = element_de(types[0]) if est_liste(types[0]) else QUELCONQUE
    tf = types[1]
    if tf == QUELCONQUE:
        return elem, QUELCONQUE
    if not isinstance(tf, TypeFonction):
        raise erreur(f"argument 2 de '{nom}' : une fonction attendue, mais {tf} fourni")
    if tf.minimum > 1 or (tf.maximum is not None and tf.maximum < 1):
        raise erreur(f"argument 2 de '{nom}' : la fonction doit accepter 1 paramètre (un élément), mais : {tf}")
    if tf.fixes and not compatible(elem, tf.fixes[0]):
        raise erreur(f"argument 2 de '{nom}' : la fonction attend un {tf.fixes[0]}, mais les éléments sont des {elem}")
    if retour_bool and tf.retour not in (BOOLEEN, QUELCONQUE):
        raise erreur(f"argument 2 de '{nom}' : la fonction doit retourner un booleen, mais retourne un {tf.retour}")
    return elem, tf.retour


def _appeler(f, *args):
    return f.appeler(*args) if isinstance(f, FonctionNck) else f(*args)


def _v_appliquer(types, erreur):
    elem, retour = _v_ordre_sup("appliquer", types, erreur)
    if retour == RIEN:
        raise erreur("argument 2 de 'appliquer' : la fonction doit retourner une valeur (utilisez 'chaque' pour un simple parcours)")
    return liste_de(retour)


@natif("appliquer", _v_appliquer, _attendu_element)
def _appliquer(l, f):
    return [_appeler(f, x) for x in l]


@natif("filtrer", lambda t, e: liste_de(_v_ordre_sup("filtrer", t, e, True)[0]), _attendu_element)
def _filtrer(l, f):
    return [x for x in l if _appeler(f, x)]


@natif("chaque", lambda t, e: (_v_ordre_sup("chaque", t, e), RIEN)[1], _attendu_element)
def _chaque(l, f):
    for x in l:
        _appeler(f, x)


@natif("trouver", lambda t, e: optionnel_de(_v_ordre_sup("trouver", t, e, True)[0]), _attendu_element)
def _trouver(l, f):
    for x in l:
        if _appeler(f, x):
            return x
    return None


@natif("tous", lambda t, e: (_v_ordre_sup("tous", t, e, True), BOOLEEN)[1], _attendu_element)
def _tous(l, f):
    return all(_appeler(f, x) for x in l)


@natif("au_moins_un", lambda t, e: (_v_ordre_sup("au_moins_un", t, e, True), BOOLEEN)[1], _attendu_element)
def _au_moins_un(l, f):
    return any(_appeler(f, x) for x in l)


def _v_reduire(types, erreur):
    _arite("reduire", types, 3, 3, erreur)
    _exiger_liste("reduire", types[0], 1, erreur)
    elem = element_de(types[0]) if est_liste(types[0]) else QUELCONQUE
    tf, init = types[1], types[2]
    if tf == QUELCONQUE:
        return init
    if not isinstance(tf, TypeFonction) or len(tf.fixes) != 2:
        raise erreur(f"argument 2 de 'reduire' : une fonction (accumulateur, element) attendue, mais {tf} fourni")
    if not compatible(elem, tf.fixes[1]):
        raise erreur(f"argument 2 de 'reduire' : le 2e paramètre de la fonction doit accepter un {elem}")
    if not compatible(init, tf.fixes[0]) or not compatible(tf.retour, tf.fixes[0]):
        raise erreur(f"'reduire' : la valeur initiale ({init}), le 1er paramètre ({tf.fixes[0]}) et le retour ({tf.retour}) de la fonction doivent avoir le même type")
    return tf.retour


@natif("reduire", _v_reduire, _attendu_reduire)
def _reduire(l, f, init):
    acc = init
    for x in l:
        acc = _appeler(f, acc, x)
    return acc


@natif("trier", lambda t, e: _v_liste_meme(t, e, "trier"))
def _trier(l):
    try:
        return sorted(l)
    except TypeError:
        raise ErreurExecution("impossible de trier une liste contenant des types différents") from None


@natif("inverser", lambda t, e: _v_liste_meme(t, e, "inverser"))
def _inverser(l):
    return l[::-1]


@natif("copier", lambda t, e: _v_liste_meme(t, e, "copier", dico_ok=True))
def _copier(l):
    return dict(l) if isinstance(l, dict) else list(l)


def _v_tranche(types, erreur):
    _arite("tranche", types, 2, 3, erreur)
    t = types[0]
    if t != QUELCONQUE and t != TEXTE and not est_liste(t):
        raise erreur(f"'tranche' attend une liste ou un texte, mais {t} fourni")
    for i, a in enumerate(types[1:], 2):
        _exiger("tranche", a, ENTIER, i, erreur)
    return t


@natif("tranche", _v_tranche)
def _tranche(c, debut, fin=None):
    return c[debut:fin]


def _v_somme(types, erreur):
    _arite("somme", types, 1, 1, erreur)
    _exiger_liste("somme", types[0], 1, erreur)
    e = element_de(types[0])
    if e != QUELCONQUE and not est_numerique(e):
        raise erreur(f"'somme' attend une liste de nombres, mais {types[0]} fournie")
    return e if est_numerique(e) else QUELCONQUE


@natif("somme", _v_somme)
def _somme(l):
    return sum(l)


def _v_minmax(nom):
    def verifier(types, erreur):
        _arite(nom, types, 1, None, erreur)
        if len(types) == 1:
            _exiger_liste(nom, types[0], 1, erreur)
            return element_de(types[0])
        t = types[0]
        for i, a in enumerate(types, 1):
            _exiger(nom, a, (ENTIER, REEL, TEXTE), i, erreur)
            t = unifier(t, a)
        return t
    return verifier


@natif("minimum", _v_minmax("minimum"))
def _minimum(*args):
    valeurs = args[0] if len(args) == 1 else args
    if not valeurs:
        raise ErreurExecution("'minimum' d'une liste vide")
    return min(valeurs)


@natif("maximum", _v_minmax("maximum"))
def _maximum(*args):
    valeurs = args[0] if len(args) == 1 else args
    if not valeurs:
        raise ErreurExecution("'maximum' d'une liste vide")
    return max(valeurs)


# ---------- textes ----------

@natif("majuscule", simple("majuscule", [TEXTE], TEXTE))
def _majuscule(s):
    return s.upper()


@natif("minuscule", simple("minuscule", [TEXTE], TEXTE))
def _minuscule(s):
    return s.lower()


@natif("nettoyer", simple("nettoyer", [TEXTE], TEXTE))
def _nettoyer(s):
    return s.strip()


@natif("remplacer", simple("remplacer", [TEXTE, TEXTE, TEXTE], TEXTE))
def _remplacer(s, ancien, nouveau):
    return s.replace(ancien, nouveau)


def _v_decouper(types, erreur):
    _arite("decouper", types, 1, 2, erreur)
    _exiger("decouper", types[0], TEXTE, 1, erreur)
    if len(types) == 2:
        _exiger("decouper", types[1], TEXTE, 2, erreur)
    return liste_de(TEXTE)


@natif("decouper", _v_decouper)
def _decouper(s, sep=None):
    return s.split(sep) if sep is None or sep != "" else list(s)


def _v_joindre(types, erreur):
    _arite("joindre", types, 1, 2, erreur)
    _exiger_liste("joindre", types[0], 1, erreur)
    if len(types) == 2:
        _exiger("joindre", types[1], TEXTE, 2, erreur)
    return TEXTE


@natif("joindre", _v_joindre)
def _joindre(l, sep=""):
    return sep.join(vers_texte(x) for x in l)


@natif("commence_par", simple("commence_par", [TEXTE, TEXTE], BOOLEEN))
def _commence_par(s, p):
    return s.startswith(p)


@natif("termine_par", simple("termine_par", [TEXTE, TEXTE], BOOLEEN))
def _termine_par(s, p):
    return s.endswith(p)


@natif("caractere", simple("caractere", [ENTIER], TEXTE))
def _caractere(n):
    return chr(n)


@natif("code", simple("code", [TEXTE], ENTIER))
def _code(s):
    if len(s) != 1:
        raise ErreurExecution("'code' attend un texte d'un seul caractère")
    return ord(s)


# ---------- mathématiques ----------

def _v_num1(nom, retour=None):
    def verifier(types, erreur):
        _arite(nom, types, 1, 1, erreur)
        _exiger(nom, types[0], REEL, 1, erreur)
        return retour or (types[0] if types[0] in (ENTIER, REEL) else REEL)
    return verifier


@natif("absolu", _v_num1("absolu"))
def _absolu(x):
    return abs(x)


@natif("racine", _v_num1("racine", REEL))
def _racine(x):
    if x < 0:
        raise ErreurExecution("racine carrée d'un nombre négatif")
    return math.sqrt(x)


def _v_puissance(types, erreur):
    _arite("puissance", types, 2, 2, erreur)
    _exiger("puissance", types[0], REEL, 1, erreur)
    _exiger("puissance", types[1], REEL, 2, erreur)
    return ENTIER if types[0] == ENTIER and types[1] == ENTIER else REEL


@natif("puissance", _v_puissance)
def _puissance(a, b):
    if isinstance(a, int) and isinstance(b, int) and b < 0:
        return float(a) ** b
    return a ** b


def _v_arrondir(types, erreur):
    _arite("arrondir", types, 1, 2, erreur)
    _exiger("arrondir", types[0], REEL, 1, erreur)
    if len(types) == 2:
        _exiger("arrondir", types[1], ENTIER, 2, erreur)
        return REEL
    return ENTIER


@natif("arrondir", _v_arrondir)
def _arrondir(x, n=None):
    return round(x) if n is None else round(x, n)


@natif("plancher", _v_num1("plancher", ENTIER))
def _plancher(x):
    return math.floor(x)


@natif("plafond", _v_num1("plafond", ENTIER))
def _plafond(x):
    return math.ceil(x)


def _v_div_entiere(types, erreur):
    _arite("division_entiere", types, 2, 2, erreur)
    _exiger("division_entiere", types[0], ENTIER, 1, erreur)
    _exiger("division_entiere", types[1], ENTIER, 2, erreur)
    return ENTIER


@natif("division_entiere", _v_div_entiere)
def _division_entiere(a, b):
    if b == 0:
        raise ErreurExecution("division par zéro")
    q = abs(a) // abs(b)
    return q if (a >= 0) == (b >= 0) else -q


def _v_aleatoire(types, erreur):
    _arite("aleatoire", types, 0, 2, erreur)
    for i, t in enumerate(types, 1):
        _exiger("aleatoire", t, ENTIER, i, erreur)
    return REEL if not types else ENTIER


@natif("aleatoire", _v_aleatoire)
def _aleatoire(a=None, b=None):
    if a is None:
        return random.random()
    if b is None:
        return random.randint(0, a)
    return random.randint(a, b)


@natif("horloge", simple("horloge", [], REEL))
def _horloge():
    return time.perf_counter()


@natif("attendre", simple("attendre", [REEL], RIEN))
def _attendre(s):
    time.sleep(s)
    return None


@natif("quitter", lambda t, e: (_arite("quitter", t, 0, 1, e), RIEN)[1])
def _quitter(code=0):
    raise SystemExit(code)


@natif("verifier", lambda t, e: (_arite("verifier", t, 1, 2, e), RIEN)[1])
def _verifier(cond, message="assertion échouée"):
    if not cond:
        raise ErreurExecution(vers_texte(message))
    return None


# =====================================================================
# Bibliothèque standard : fichiers, JSON, date/heure, système, texte
# =====================================================================

import datetime as _dt
import json as _json
import os as _os

ARGUMENTS: list[str] = []   # rempli par la ligne de commande (nck fichier.nck arg1 arg2 ...)


def _erreur_fichier(exc: OSError, chemin: str) -> ErreurExecution:
    if isinstance(exc, FileNotFoundError):
        return ErreurExecution(f"fichier introuvable : \"{chemin}\"")
    if isinstance(exc, PermissionError):
        return ErreurExecution(f"accès refusé : \"{chemin}\"")
    if isinstance(exc, IsADirectoryError):
        return ErreurExecution(f"\"{chemin}\" est un dossier, pas un fichier")
    if isinstance(exc, FileExistsError):
        return ErreurExecution(f"\"{chemin}\" existe déjà")
    return ErreurExecution(f"erreur sur \"{chemin}\" : {exc.strerror or exc}")


# ---------- fichiers ----------

@natif("lire_fichier", simple("lire_fichier", [TEXTE], TEXTE))
def _lire_fichier(chemin):
    try:
        with open(chemin, encoding="utf-8") as f:
            return f.read()
    except OSError as e:
        raise _erreur_fichier(e, chemin) from None
    except UnicodeDecodeError:
        raise ErreurExecution(f"\"{chemin}\" n'est pas un fichier texte UTF-8") from None


@natif("lire_lignes", simple("lire_lignes", [TEXTE], liste_de(TEXTE)))
def _lire_lignes(chemin):
    return _lire_fichier(chemin).splitlines()


@natif("ecrire_fichier", simple("ecrire_fichier", [TEXTE, TEXTE], RIEN))
def _ecrire_fichier(chemin, contenu):
    try:
        with open(chemin, "w", encoding="utf-8") as f:
            f.write(contenu)
    except OSError as e:
        raise _erreur_fichier(e, chemin) from None
    return None


@natif("ajouter_fichier", simple("ajouter_fichier", [TEXTE, TEXTE], RIEN))
def _ajouter_fichier(chemin, contenu):
    try:
        with open(chemin, "a", encoding="utf-8") as f:
            f.write(contenu)
    except OSError as e:
        raise _erreur_fichier(e, chemin) from None
    return None


@natif("fichier_existe", simple("fichier_existe", [TEXTE], BOOLEEN))
def _fichier_existe(chemin):
    return _os.path.isfile(chemin)


@natif("dossier_existe", simple("dossier_existe", [TEXTE], BOOLEEN))
def _dossier_existe(chemin):
    return _os.path.isdir(chemin)


@natif("supprimer_fichier", simple("supprimer_fichier", [TEXTE], RIEN))
def _supprimer_fichier(chemin):
    try:
        _os.remove(chemin)
    except OSError as e:
        raise _erreur_fichier(e, chemin) from None
    return None


@natif("creer_dossier", simple("creer_dossier", [TEXTE], RIEN))
def _creer_dossier(chemin):
    try:
        _os.makedirs(chemin, exist_ok=True)
    except OSError as e:
        raise _erreur_fichier(e, chemin) from None
    return None


def _v_lister_dossier(types, erreur):
    _arite("lister_dossier", types, 0, 1, erreur)
    if types:
        _exiger("lister_dossier", types[0], TEXTE, 1, erreur)
    return liste_de(TEXTE)


@natif("lister_dossier", _v_lister_dossier)
def _lister_dossier(chemin="."):
    try:
        return sorted(_os.listdir(chemin))
    except OSError as e:
        raise _erreur_fichier(e, chemin) from None


@natif("joindre_chemin", lambda t, e: (_arite("joindre_chemin", t, 1, None, e),
                                        [_exiger("joindre_chemin", x, TEXTE, i, e) for i, x in enumerate(t, 1)], TEXTE)[2])
def _joindre_chemin(*morceaux):
    return _os.path.join(*morceaux)


# ---------- JSON ----------

def _vers_python_json(v, chemin="valeur"):
    if v is None or isinstance(v, (bool, int, float, str)):
        return v
    if isinstance(v, list):
        return [_vers_python_json(x, f"{chemin}[{i}]") for i, x in enumerate(v)]
    if isinstance(v, dict):
        return {str(k) if not isinstance(k, str) else k: _vers_python_json(x, f"{chemin}[{_repr_elem(k)}]") for k, x in v.items()}
    if isinstance(v, ObjetNck):
        return {k: _vers_python_json(x, f"{chemin}.{k}") for k, x in v.champs.items()}
    raise ErreurExecution(f"impossible de convertir {chemin} ({nom_type_valeur(v)}) en JSON")


def _v_vers_json(types, erreur):
    _arite("vers_json", types, 1, 2, erreur)
    if len(types) == 2:
        _exiger("vers_json", types[1], BOOLEEN, 2, erreur)
    return TEXTE


@natif("vers_json", _v_vers_json)
def _vers_json(v, joli=False):
    return _json.dumps(_vers_python_json(v), ensure_ascii=False, indent=2 if joli else None)


@natif("depuis_json", simple("depuis_json", [TEXTE], QUELCONQUE))
def _depuis_json(texte):
    try:
        return _json.loads(texte)
    except _json.JSONDecodeError as e:
        raise ErreurExecution(f"JSON invalide : {e.msg} (ligne {e.lineno}, colonne {e.colno})") from None


# ---------- date et heure ----------

@natif("maintenant", simple("maintenant", [], REEL))
def _maintenant():
    return time.time()


def _v_date(types, erreur):
    _arite("date", types, 0, 1, erreur)
    if types:
        _exiger("date", types[0], REEL, 1, erreur)
    from .types_nck import dico_de
    return dico_de(TEXTE, ENTIER)


@natif("date", _v_date)
def _date(horodatage=None):
    d = _dt.datetime.now() if horodatage is None else _dt.datetime.fromtimestamp(horodatage)
    return {"annee": d.year, "mois": d.month, "jour": d.day, "heure": d.hour,
            "minute": d.minute, "seconde": d.second, "jour_semaine": d.isoweekday()}


_FORMATS = {"AAAA": "%Y", "AA": "%y", "MM": "%m", "JJ": "%d", "hh": "%H", "mm": "%M", "ss": "%S"}


def _v_formater_date(types, erreur):
    _arite("formater_date", types, 0, 2, erreur)
    if len(types) >= 1:
        _exiger("formater_date", types[0], TEXTE, 1, erreur)
    if len(types) == 2:
        _exiger("formater_date", types[1], REEL, 2, erreur)
    return TEXTE


@natif("formater_date", _v_formater_date)
def _formater_date(format="JJ/MM/AAAA hh:mm:ss", horodatage=None):
    """Format lisible : AAAA (année), MM (mois), JJ (jour), hh, mm, ss."""
    d = _dt.datetime.now() if horodatage is None else _dt.datetime.fromtimestamp(horodatage)
    fmt = format.replace("%", "%%")
    for cle, val in _FORMATS.items():
        fmt = fmt.replace(cle, val)
    return d.strftime(fmt)


@natif("creer_date", lambda t, e: (_arite("creer_date", t, 3, 6, e),
                                   [_exiger("creer_date", x, ENTIER, i, e) for i, x in enumerate(t, 1)], REEL)[2])
def _creer_date(annee, mois, jour, heure=0, minute=0, seconde=0):
    try:
        return _dt.datetime(annee, mois, jour, heure, minute, seconde).timestamp()
    except ValueError as e:
        raise ErreurExecution(f"date invalide : {e}") from None


# ---------- système ----------

@natif("arguments", simple("arguments", [], liste_de(TEXTE)))
def _arguments():
    return list(ARGUMENTS)


def _v_variable_env(types, erreur):
    _arite("variable_env", types, 1, 2, erreur)
    for i, t in enumerate(types, 1):
        _exiger("variable_env", t, TEXTE, i, erreur)
    return TEXTE


@natif("variable_env", _v_variable_env)
def _variable_env(nom, defaut=""):
    return _os.environ.get(nom, defaut)


@natif("dossier_courant", simple("dossier_courant", [], TEXTE))
def _dossier_courant():
    return _os.getcwd()


@natif("ecrire_erreur", _v_ecrire)
def _ecrire_erreur(*args):
    sys.stderr.write(" ".join(vers_texte(a) for a in args) + "\n")
    return None


# ---------- texte (suite) ----------

def _v_formater(types, erreur):
    _arite("formater", types, 1, None, erreur)
    _exiger("formater", types[0], TEXTE, 1, erreur)
    return TEXTE


@natif("formater", _v_formater)
def _formater(modele, *valeurs):
    """formater("{} a {} ans", nom, age) ; {0}, {1} pour choisir l'ordre."""
    morceaux = modele.split("{}")
    if len(morceaux) - 1 > len(valeurs):
        raise ErreurExecution(f"'formater' : {len(morceaux) - 1} emplacement(s) {{}} mais {len(valeurs)} valeur(s)")
    resultat = morceaux[0]
    for i, m in enumerate(morceaux[1:]):
        resultat += vers_texte(valeurs[i]) + m
    for i, v in enumerate(valeurs):
        resultat = resultat.replace("{" + str(i) + "}", vers_texte(v))
    return resultat


@natif("est_nombre", simple("est_nombre", [TEXTE], BOOLEEN))
def _est_nombre(t):
    try:
        float(t.strip().replace(",", "."))
        return True
    except ValueError:
        return False


@natif("est_entier", simple("est_entier", [TEXTE], BOOLEEN))
def _est_entier(t):
    t = t.strip()
    return t[1:].isdigit() if t[:1] in "+-" else t.isdigit()


@natif("remplir_gauche", simple("remplir_gauche", [TEXTE, ENTIER, TEXTE], TEXTE))
def _remplir_gauche(t, n, c):
    return t.rjust(n, c[:1] or " ")


@natif("remplir_droite", simple("remplir_droite", [TEXTE, ENTIER, TEXTE], TEXTE))
def _remplir_droite(t, n, c):
    return t.ljust(n, c[:1] or " ")
