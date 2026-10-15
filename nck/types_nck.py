"""Système de types de NCK."""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Type:
    nom: str
    params: tuple["Type", ...] = field(default_factory=tuple)

    def __str__(self) -> str:
        if self.params:
            return f"{self.nom}<{', '.join(map(str, self.params))}>"
        return self.nom


@dataclass(frozen=True)
class TypeFonction(Type):
    parametres: tuple[Type, ...] = field(default_factory=tuple)
    retour: Type = None  # type: ignore[assignment]

    def __str__(self) -> str:
        return f"fonction({', '.join(map(str, self.parametres))}) -> {self.retour}"


@dataclass(frozen=True)
class TypeClasse(Type):
    """Type d'une instance de classe. `ancetres` contient les noms des classes parentes (ordre croissant)."""
    ancetres: tuple[str, ...] = field(default_factory=tuple)

    def __str__(self) -> str:
        return self.nom

    def herite_de(self, nom: str) -> bool:
        return self.nom == nom or nom in self.ancetres


ENTIER = Type("entier")
REEL = Type("reel")
TEXTE = Type("texte")
BOOLEEN = Type("booleen")
RIEN = Type("rien")
NUL = Type("nul")
QUELCONQUE = Type("quelconque")
LISTE_VIDE = Type("liste", (Type("?"),))   # type d'un littéral [] : compatible avec toute liste

TYPES_SIMPLES = {
    "entier": ENTIER, "reel": REEL, "texte": TEXTE, "booleen": BOOLEEN,
    "rien": RIEN, "quelconque": QUELCONQUE,
}


def liste_de(t: Type) -> Type:
    return Type("liste", (t,))


def est_liste(t: Type) -> bool:
    return t.nom == "liste"


def element_de(t: Type) -> Type:
    if est_liste(t):
        e = t.params[0]
        return QUELCONQUE if e.nom == "?" else e
    return QUELCONQUE


def est_numerique(t: Type) -> bool:
    return t in (ENTIER, REEL)


def compatible(source: Type, cible: Type) -> bool:
    """Peut-on placer une valeur de type `source` dans un emplacement de type `cible` ?"""
    if cible == QUELCONQUE or source == QUELCONQUE:
        return True
    if source == cible:
        return True
    if source == ENTIER and cible == REEL:
        return True
    if source == NUL:
        return cible in (RIEN, NUL)
    if est_liste(source) and est_liste(cible):
        if source.params[0].nom == "?" or cible.params[0].nom == "?":
            return True
        return compatible(source.params[0], cible.params[0])
    if isinstance(source, TypeClasse) and isinstance(cible, TypeClasse):
        return source.herite_de(cible.nom)
    if isinstance(source, TypeFonction) and isinstance(cible, TypeFonction):
        if len(source.parametres) != len(cible.parametres):
            return False
        return (all(compatible(c, s) for s, c in zip(source.parametres, cible.parametres))
                and compatible(source.retour, cible.retour))
    return False


def unifier(a: Type, b: Type) -> Type:
    """Type commun de deux valeurs (pour les listes littérales, les branches, ...)."""
    if a == b:
        return a
    if isinstance(a, TypeClasse) and isinstance(b, TypeClasse):
        if a.herite_de(b.nom):
            return b
        if b.herite_de(a.nom):
            return a
    if est_numerique(a) and est_numerique(b):
        return REEL
    if est_liste(a) and est_liste(b):
        if a.params[0].nom == "?":
            return b
        if b.params[0].nom == "?":
            return a
        return liste_de(unifier(element_de(a), element_de(b)))
    return QUELCONQUE


def type_runtime(v: object) -> Type:
    """Type NCK d'une valeur Python à l'exécution."""
    if v is None:
        return NUL
    if v is True or v is False:
        return BOOLEEN
    if isinstance(v, int):
        return ENTIER
    if isinstance(v, float):
        return REEL
    if isinstance(v, str):
        return TEXTE
    if isinstance(v, list):
        return liste_de(QUELCONQUE)
    return QUELCONQUE


def valeur_compatible(v: object, t: Type) -> bool:
    """Vérifie à l'exécution qu'une valeur correspond à un type (contrôle profond pour les listes)."""
    if t == QUELCONQUE:
        return True
    if t == ENTIER:
        return isinstance(v, int) and not isinstance(v, bool)
    if t == REEL:
        return isinstance(v, (int, float)) and not isinstance(v, bool)
    if t == TEXTE:
        return isinstance(v, str)
    if t == BOOLEEN:
        return isinstance(v, bool)
    if t in (RIEN, NUL):
        return v is None
    if est_liste(t):
        if not isinstance(v, list):
            return False
        elem = element_de(t)
        if elem == QUELCONQUE:
            return True
        return all(valeur_compatible(x, elem) for x in v)
    if isinstance(t, TypeFonction):
        return callable(v)
    if isinstance(t, TypeClasse):
        classe = getattr(v, "classe", None)
        return classe is not None and (classe.nom == t.nom or t.nom in classe.ancetres)
    return True
