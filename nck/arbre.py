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
class ListeLit(Noeud):
    elements: list["Expr"]


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


Expr = Litteral | ListeLit | Identifiant | Unaire | Binaire | Logique | Appel | Index | Membre


# ---------- Instructions ----------

@dataclass
class DeclVariable(Noeud):
    nom: str
    type_annot: Optional[TypeAnnot]
    valeur: Optional[Expr]
    constante: bool = False


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


@dataclass
class Parametre(Noeud):
    nom: str
    type_annot: TypeAnnot


@dataclass
class DeclFonction(Noeud):
    nom: str
    parametres: list[Parametre]
    type_retour: TypeAnnot
    corps: Bloc


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
class Retourner(Noeud):
    valeur: Optional[Expr]


@dataclass
class Arreter(Noeud):
    pass


@dataclass
class Continuer(Noeud):
    pass


Instr = (DeclVariable | Affectation | ExprInstr | Bloc | Si | TantQue | Pour
         | DeclFonction | DeclClasse | Essayer | Lever | Retourner | Arreter | Continuer)


@dataclass
class Programme(Noeud):
    instructions: list[Instr]
