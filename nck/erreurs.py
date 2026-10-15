"""Erreurs du langage NCK, toutes avec position (ligne, colonne)."""


class ErreurNck(Exception):
    """Classe de base de toutes les erreurs NCK."""

    nom = "Erreur"

    def __init__(self, message: str, ligne: int = 0, colonne: int = 0, fichier: str = "<entrée>"):
        super().__init__(message)
        self.message = message
        self.ligne = ligne
        self.colonne = colonne
        self.fichier = fichier

    def formater(self, source: str | None = None) -> str:
        tete = f"{self.nom} : {self.message}"
        pos = f"  --> {self.fichier}:{self.ligne}:{self.colonne}"
        lignes = [tete, pos]
        if source is not None and self.ligne > 0:
            lignes_src = source.splitlines()
            if self.ligne - 1 < len(lignes_src):
                texte = lignes_src[self.ligne - 1]
                lignes.append(f"   |")
                lignes.append(f"{self.ligne:>3}| {texte}")
                lignes.append(f"   | {' ' * max(self.colonne - 1, 0)}^")
        return "\n".join(lignes)


class ErreurSyntaxe(ErreurNck):
    nom = "Erreur de syntaxe"


class ErreurLexicale(ErreurSyntaxe):
    nom = "Erreur lexicale"


class ErreurType(ErreurNck):
    nom = "Erreur de type"


class ErreurExecution(ErreurNck):
    nom = "Erreur d'exécution"
