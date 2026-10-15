"""NCK — un langage de programmation simple, typé et en français.

Utilisation rapide :

    from nck import executer_source
    executer_source('ecrire("Bonjour !")')
"""

from .erreurs import ErreurExecution, ErreurLexicale, ErreurNck, ErreurSyntaxe, ErreurType
from .interpreteur import Interpreteur
from .lexeur import lexer
from .parseur import parser
from .modules import Chargeur
from .verificateur import Verificateur, verifier

__version__ = "0.6.0"
__all__ = [
    "__version__", "executer_source", "compiler_source", "lexer", "parser", "verifier", "Interpreteur",
    "ErreurNck", "ErreurLexicale", "ErreurSyntaxe", "ErreurType", "ErreurExecution",
]


def compiler_source(source: str, fichier: str = "<entrée>", chargeur: Chargeur | None = None):
    """Analyse et vérifie les types d'un programme NCK sans l'exécuter. Retourne l'AST annoté."""
    prog = parser(source, fichier)
    Verificateur(fichier, chargeur=chargeur).verifier_programme(prog)
    return prog


def executer_source(source: str, fichier: str = "<entrée>") -> None:
    """Analyse, vérifie puis exécute un programme NCK."""
    chargeur = Chargeur()
    prog = compiler_source(source, fichier, chargeur)
    Interpreteur(fichier, chargeur=chargeur).executer(prog)
