"""Arbre syntaxique abstrait (AST) du langage NCK."""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Noeud:
    ligne: int = field(default=0, kw_only=True)
    colonne: int = field(default=0, kw_only=True)


# ---------- Types (annotations) ----------

@dataclass
class TypeAnnot(Noeud):
    nom: str                                   # entier, reel, texte, booleen, liste, rien, quelconque
    params: list["TypeAnnot"] = field(default_factory=list)   # liste<entier>


# ---------- Expressions ----------

@dataclass
class Litteral(Noeud):
    valeur: object


@dataclass
class TexteFormate(Noeud):
    parties: list["str | Expr"]


@dataclass
class ListeLit(Noeud):
    elements: list["Expr"]


@dataclass
class DicoLit(Noeud):
    entrees: list[tuple["Expr", "Expr"]]


@dataclass
class Identifiant(Noeud):
    nom: str


@dataclass
class Unaire(Noeud):
    op: str                 # '-', 'non'
    operande: "Expr"


@dataclass
class Binaire(Noeud):
    op: str
    gauche: "Expr"
    droite: "Expr"


@dataclass
class Logique(Noeud):
    op: str                 # 'et', 'ou'
    gauche: "Expr"
    droite: "Expr"


@dataclass
class Appel(Noeud):
    cible: "Expr"
    arguments: list["Expr"]
    nommes: list[tuple[str, "Expr"]] = field(default_factory=list)   # Personne(nom = "Awa")


@dataclass
class Membre(Noeud):
    objet: "Expr"
    nom: str


@dataclass
class Index(Noeud):
    cible: "Expr"
    index: "Expr"


Expr = Litteral | TexteFormate | ListeLit | DicoLit | Identifiant | Unaire | Binaire | Logique | Appel | Index | Membre


# ---------- Instructions ----------

@dataclass
class DeclVariable(Noeud):
    nom: str
    type_annot: Optional[TypeAnnot]
    valeur: Optional[Expr]
    constante: bool = False


@dataclass
class DeclMultiple(Noeud):
    """`variable a, b = 1, 2` ou `variable a, b = liste` (déstructuration)."""
    noms: list[str]
    valeurs: list[Expr]            # autant que de noms, ou une seule (liste à déstructurer)
    constante: bool = False
    positions: list[tuple[int, int]] = field(default_factory=list)


@dataclass
class AffectationMultiple(Noeud):
    """`a, b = b, a` ou `a, b = liste`."""
    cibles: list[Expr]
    valeurs: list[Expr]


@dataclass
class DeclEnum(Noeud):
    """`enumeration Couleur: ROUGE, VERT, BLEU fin`."""
    nom: str
    valeurs: list[str]
    positions: list[tuple[int, int]] = field(default_factory=list)


@dataclass
class Conditionnelle(Noeud):
    """`si condition alors a sinon b` (expression)."""
    condition: Expr
    alors: Expr
    sinon: Expr


@dataclass
class Affectation(Noeud):
    cible: Expr             # Identifiant ou Index
    valeur: Expr
    op: str = "="           # '=', '+=', '-=', '*=', '/='


@dataclass
class ExprInstr(Noeud):
    expr: Expr


@dataclass
class Bloc(Noeud):
    instructions: list["Instr"]


@dataclass
class Si(Noeud):
    condition: Expr
    alors: Bloc
    sinon: Optional["Bloc | Si"]


@dataclass
class TantQue(Noeud):
    condition: Expr
    corps: Bloc


@dataclass
class Pour(Noeud):
    variable: str
    iterable: Expr
    corps: Bloc
    variable2: Optional[str] = None     # pour i, x dans liste / pour cle, valeur dans dico


@dataclass
class Cas(Noeud):
    valeurs: list[Expr]
    corps: Bloc


@dataclass
class Selon(Noeud):
    sujet: Expr
    cas: list[Cas]
    sinon: Optional[Bloc]


@dataclass
class Parametre(Noeud):
    nom: str
    type_annot: Optional[TypeAnnot]     # None : type déduit du contexte (fonction anonyme)
    defaut: Optional[Expr] = None
    variadique: bool = False            # ...args


@dataclass
class FonctionAnonyme(Noeud):
    """`fonction(x: entier) -> entier: retourner x * 2` ou `fonction(x): x * 2` ou forme bloc … fin."""
    parametres: list[Parametre]
    type_retour: Optional[TypeAnnot]   # None : déduit
    corps: Optional["Bloc"]            # forme bloc / instruction courte
    expression: Optional["Expr"] = None  # forme courte `fonction(x): x * 2`


@dataclass
class Etalement(Noeud):
    """`...liste` dans un appel : étale les éléments comme arguments."""
    valeur: "Expr"


@dataclass
class DeclFonction(Noeud):
    nom: str
    parametres: list[Parametre]
    type_retour: TypeAnnot
    corps: Optional[Bloc]               # None pour une méthode abstraite
    decorateurs: list[Expr] = field(default_factory=list)
    statique: bool = False
    abstraite: bool = False


@dataclass
class Champ(Noeud):
    nom: str
    type_annot: TypeAnnot
    defaut: Optional[Expr]


@dataclass
class DeclClasse(Noeud):
    nom: str
    parent: Optional[str]
    champs: list[Champ]
    methodes: list[DeclFonction]
    constantes: list[DeclVariable] = field(default_factory=list)   # constante MAX = 10 (accès Classe.MAX)


@dataclass
class Attraper(Noeud):
    variable: str
    type_annot: Optional[TypeAnnot]      # par défaut : Erreur
    corps: Bloc


@dataclass
class Essayer(Noeud):
    corps: Bloc
    clauses: list[Attraper]
    enfin: Optional[Bloc]


@dataclass
class Lever(Noeud):
    valeur: Expr


@dataclass
class Importer(Noeud):
    chemin: str
    alias: Optional[str]            # importer "x.nck" comme m
    noms: Optional[list[str]]       # depuis "x.nck" importer a, b


@dataclass
class Retourner(Noeud):
    valeur: Optional[Expr]


@dataclass
class Arreter(Noeud):
    pass


@dataclass
class Continuer(Noeud):
    pass


Instr = (DeclVariable | Affectation | ExprInstr | Bloc | Si | TantQue | Pour
         | DeclFonction | DeclClasse | Essayer | Lever | Importer | Selon | Retourner | Arreter | Continuer)


@dataclass
class Programme(Noeud):
    instructions: list[Instr]
