"""Fonctions natives (intégrées) du langage NCK."""

import math
import random
import sys
import time
from dataclasses import dataclass
from typing import Callable

from .erreurs import ErreurExecution, ErreurType
from .types_nck import (
    BOOLEEN, ENTIER, QUELCONQUE, REEL, RIEN, TEXTE, Type, compatible, element_de,
    est_liste, est_numerique, liste_de, unifier,
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
    if isinstance(v, ObjetNck):
        if "texte" in v.classe.methodes:
            return str(v.classe.methodes["texte"](v))
        if v.classe.nom == "Erreur" or "Erreur" in v.classe.ancetres:
            return f"{v.classe.nom} : {v.champs.get('message', '')}"
        return v.classe.nom + "(" + ", ".join(f"{k}={_repr_elem(x)}" for k, x in v.champs.items()) + ")"
    if isinstance(v, ClasseNck):
        return f"<classe {v.nom}>"
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
    if isinstance(v, (FonctionNck, Natif)):
        return "fonction"
    if isinstance(v, ObjetNck):
        return v.classe.nom
    if isinstance(v, ClasseNck):
        return "classe"
    return type(v).__name__


class ClasseNck:
    """Classe définie par l'utilisateur (remplie par l'interpréteur)."""

    __slots__ = ("nom", "ancetres", "champs", "types_champs", "defauts", "methodes", "construire")

    def __init__(self, nom: str, ancetres: tuple[str, ...]):
        self.nom = nom
        self.ancetres = ancetres
        self.champs: list[str] = []
        self.types_champs: dict[str, object] = {}
        self.defauts: dict[str, Callable] = {}       # nom -> fonction () -> valeur
        self.methodes: dict[str, Callable] = {}      # nom -> fonction (objet, *args)
        self.construire: Callable = None             # type: ignore[assignment]

    def __call__(self, *args, **kwargs):
        return self.construire(*args, **kwargs)


class ObjetNck:
    """Instance d'une classe NCK."""

    __slots__ = ("classe", "champs")

    def __init__(self, classe: ClasseNck, champs: dict):
        self.classe = classe
        self.champs = champs


class FonctionNck:
    """Fonction définie par l'utilisateur (remplie par l'interpréteur)."""

    __slots__ = ("nom", "appeler", "arite")

    def __init__(self, nom: str, arite: int, appeler: Callable):
        self.nom = nom
        self.arite = arite
        self.appeler = appeler

    def __call__(self, *args):
        return self.appeler(*args)


@dataclass
class Natif:
    nom: str
    fn: Callable
    verifier: Callable            # (types_args: list[Type], erreur: Callable[[str], ErreurType]) -> Type

    def __call__(self, *args):
        return self.fn(*args)


NATIFS: dict[str, Natif] = {}


def natif(nom: str, verifier: Callable):
    def deco(fn):
        NATIFS[nom] = Natif(nom, fn, verifier)
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


# ---------- listes et textes ----------

def _v_longueur(types, erreur):
    _arite("longueur", types, 1, 1, erreur)
    t = types[0]
    if t != QUELCONQUE and t != TEXTE and not est_liste(t):
        raise erreur(f"'longueur' attend une liste ou un texte, mais {t} fourni")
    return ENTIER


@natif("longueur", _v_longueur)
def _longueur(v):
    if isinstance(v, (str, list)):
        return len(v)
    raise ErreurExecution(f"'longueur' attend une liste ou un texte, mais {nom_type_valeur(v)} fourni")


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
    _exiger_liste("retirer", types[0], 1, erreur)
    if len(types) == 2:
        _exiger("retirer", types[1], ENTIER, 2, erreur)
    return element_de(types[0])


@natif("retirer", _v_retirer)
def _retirer(l, i=-1):
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
    elif t != QUELCONQUE and not est_liste(t):
        raise erreur(f"'contient' attend une liste ou un texte, mais {t} fourni")
    return BOOLEEN


@natif("contient", _v_contient)
def _contient(c, v):
    return v in c


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


def _v_liste_meme(types, erreur, nom):
    _arite(nom, types, 1, 1, erreur)
    _exiger_liste(nom, types[0], 1, erreur)
    return types[0] if est_liste(types[0]) else liste_de(QUELCONQUE)


@natif("trier", lambda t, e: _v_liste_meme(t, e, "trier"))
def _trier(l):
    try:
        return sorted(l)
    except TypeError:
        raise ErreurExecution("impossible de trier une liste contenant des types différents") from None


@natif("inverser", lambda t, e: _v_liste_meme(t, e, "inverser"))
def _inverser(l):
    return l[::-1]


@natif("copier", lambda t, e: _v_liste_meme(t, e, "copier"))
def _copier(l):
    return list(l)


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
