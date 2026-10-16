"""Système de types de NCK."""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Type:
    nom: str
    params: tuple["Type", ...] = field(default_factory=tuple)

    def __str__(self) -> str:
        if self.nom == "optionnel" and len(self.params) == 1:
            return f"{self.params[0]}?"
        if self.params:
            return f"{self.nom}<{', '.join(map(str, self.params))}>"
        return self.nom


@dataclass(frozen=True)
class TypeFonction(Type):
    parametres: tuple[Type, ...] = field(default_factory=tuple)
    retour: Type = None  # type: ignore[assignment]
    obligatoires: int = -1      # nombre de paramètres sans valeur par défaut (-1 : tous)
    variadique: bool = False    # le dernier paramètre est `...args` (liste des arguments restants)

    @property
    def fixes(self) -> tuple["Type", ...]:
        return self.parametres[:-1] if self.variadique else self.parametres

    @property
    def minimum(self) -> int:
        n = len(self.fixes)
        return n if self.obligatoires < 0 else min(self.obligatoires, n)

    @property
    def maximum(self) -> int | None:
        return None if self.variadique else len(self.parametres)

    def __str__(self) -> str:
        params = [str(p) + ("?" if i >= self.minimum else "") for i, p in enumerate(self.fixes)]
        if self.variadique:
            params.append("..." + str(self.parametres[-1]))
        return f"fonction({', '.join(params)}) -> {self.retour}"


@dataclass(frozen=True)
class TypeClasse(Type):
    """Type d'une instance de classe. `ancetres` contient les noms des classes parentes (ordre croissant)."""
    ancetres: tuple[str, ...] = field(default_factory=tuple)

    def __str__(self) -> str:
        return self.nom

    def herite_de(self, nom: str) -> bool:
        return self.nom == nom or nom in self.ancetres


@dataclass(frozen=True)
class TypeEnum(Type):
    """Type d'une valeur d'énumération (`Couleur.ROUGE`). `valeurs` : noms dans l'ordre."""
    valeurs: tuple[str, ...] = field(default_factory=tuple)

    def __str__(self) -> str:
        return self.nom


@dataclass(frozen=True)
class TypeModule(Type):
    """Type d'un module importé (`importer "x.nck"`). `chemin` est le chemin absolu du fichier."""
    chemin: str = ""

    def __str__(self) -> str:
        return f"module({self.nom})"


ENTIER = Type("entier")
REEL = Type("reel")
TEXTE = Type("texte")
BOOLEEN = Type("booleen")
RIEN = Type("rien")
NUL = Type("nul")
QUELCONQUE = Type("quelconque")
LISTE_VIDE = Type("liste", (Type("?"),))   # type d'un littéral [] : compatible avec toute liste
DICO_VIDE = Type("dico", (Type("?"), Type("?")))   # type d'un littéral {}
TYPES_CLES = (ENTIER, TEXTE, BOOLEEN)      # types autorisés comme clés de dictionnaire

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


def dico_de(k: Type, v: Type) -> Type:
    return Type("dico", (k, v))


def est_dico(t: Type) -> bool:
    return t.nom == "dico"


def cle_de(t: Type) -> Type:
    if est_dico(t):
        k = t.params[0]
        return QUELCONQUE if k.nom == "?" else k
    return QUELCONQUE


def valeur_de(t: Type) -> Type:
    if est_dico(t):
        v = t.params[1]
        return QUELCONQUE if v.nom == "?" else v
    return QUELCONQUE


def est_numerique(t: Type) -> bool:
    return t in (ENTIER, REEL)


def optionnel_de(t: Type) -> Type:
    """`T?` : une valeur de type T ou nul."""
    return t if est_optionnel(t) or t in (QUELCONQUE, NUL) else Type("optionnel", (t,))


def est_optionnel(t: Type) -> bool:
    return t.nom == "optionnel" and not isinstance(t, (TypeFonction, TypeClasse))


def sans_nul(t: Type) -> Type:
    return t.params[0] if est_optionnel(t) else t


def compatible(source: Type, cible: Type) -> bool:
    """Peut-on placer une valeur de type `source` dans un emplacement de type `cible` ?"""
    if cible == QUELCONQUE or source == QUELCONQUE:
        return True
    if source == cible:
        return True
    if est_optionnel(cible):
        return source == NUL or compatible(sans_nul(source), cible.params[0])
    if est_optionnel(source):
        return False
    if source == ENTIER and cible == REEL:
        return True
    if source == NUL:
        return cible in (RIEN, NUL)
    if est_liste(source) and est_liste(cible):
        if source.params[0].nom == "?" or cible.params[0].nom == "?":
            return True
        return compatible(source.params[0], cible.params[0])
    if est_dico(source) and est_dico(cible):
        if source == DICO_VIDE or cible == DICO_VIDE:
            return True
        return (compatible(source.params[0], cible.params[0]) and compatible(source.params[1], cible.params[1]))
    if isinstance(source, TypeClasse) and isinstance(cible, TypeClasse):
        return source.herite_de(cible.nom)
    if isinstance(source, TypeFonction) and isinstance(cible, TypeFonction):
        # la source doit accepter tous les appels valides pour la cible
        n = len(cible.fixes)
        if source.minimum > cible.minimum:
            return False
        if source.maximum is not None and (cible.maximum is None or source.maximum < n):
            return False
        return (all(compatible(c, s) for s, c in zip(source.fixes[:n], cible.fixes))
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
    if est_dico(a) and est_dico(b):
        if a == DICO_VIDE:
            return b
        if b == DICO_VIDE:
            return a
        return dico_de(unifier(cle_de(a), cle_de(b)), unifier(valeur_de(a), valeur_de(b)))
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
    if isinstance(v, dict):
        return dico_de(QUELCONQUE, QUELCONQUE)
    return QUELCONQUE


def valeur_compatible(v: object, t: Type) -> bool:
    """Vérifie à l'exécution qu'une valeur correspond à un type (contrôle profond pour les listes)."""
    if t == QUELCONQUE:
        return True
    if est_optionnel(t):
        return v is None or valeur_compatible(v, t.params[0])
    if isinstance(t, TypeEnum):
        return getattr(v, "enum", None) == t.nom and type(v).__name__ == "ValeurEnum"
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
    if est_dico(t):
        if not isinstance(v, dict):
            return False
        k, val = cle_de(t), valeur_de(t)
        if k == QUELCONQUE and val == QUELCONQUE:
            return True
        return all(valeur_compatible(a, k) and valeur_compatible(b, val) for a, b in v.items())
    if isinstance(t, TypeFonction):
        return callable(v)
    if isinstance(t, TypeClasse):
        classe = getattr(v, "classe", None)
        return classe is not None and (classe.nom == t.nom or t.nom in classe.ancetres)
    return True
