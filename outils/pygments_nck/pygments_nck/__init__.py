"""Lexer Pygments pour NCK (utilisé par le site de documentation MkDocs)."""
from pygments.lexer import RegexLexer, words, bygroups
from pygments.token import (Comment, Keyword, Name, Number, Operator, Punctuation, String, Text, Whitespace)

MOTS_CLES = (
    "variable", "constante", "fonction", "classe", "enumeration", "herite", "statique", "abstraite",
    "retourner", "si", "sinon", "alors", "selon", "cas", "tantque", "pour", "dans", "fin", "arreter",
    "continuer", "essayer", "attraper", "enfin", "lever", "importer", "depuis", "comme",
)
TYPES = ("entier", "reel", "texte", "booleen", "liste", "dico", "rien", "quelconque", "module", "Erreur")
CONSTANTES = ("vrai", "faux", "nul", "soi", "parent")


class NckLexer(RegexLexer):
    name = "NCK"
    aliases = ["nck"]
    filenames = ["*.nck"]

    tokens = {
        "root": [
            (r"\s+", Whitespace),
            (r"//.*?$", Comment.Single),
            (r"#.*?$", Comment.Single),
            (r'f?"""', String, "texte_long"),
            (r'f"', String, "texte_f"),
            (r'"', String, "texte"),
            (r"'(?:\\.|[^'\\])*'", String),
            (r"@[A-Za-z_][\w]*", Name.Decorator),
            (words(MOTS_CLES, suffix=r"\b"), Keyword),
            (words(CONSTANTES, suffix=r"\b"), Keyword.Constant),
            (words(("et", "ou", "non"), suffix=r"\b"), Operator.Word),
            (words(TYPES, suffix=r"\b"), Keyword.Type),
            (r"\d+\.\d+", Number.Float),
            (r"\d+", Number.Integer),
            (r"([A-Za-z_]\w*)(\s*)(\()", bygroups(Name.Function, Whitespace, Punctuation)),
            (r"[A-Z][\w]*", Name.Class),
            (r"[A-Za-z_]\w*", Name),
            (r"\.\.|\?\?|==|!=|<=|>=|->|\.\.\.|[-+*/%=<>!?]", Operator),
            (r"[()\[\]{}:,.;]", Punctuation),
        ],
        "texte": [(r'\\.', String.Escape), (r'"', String, "#pop"), (r'[^"\\]+', String)],
        "texte_f": [(r'\\.', String.Escape), (r"\{[^}]*\}", String.Interpol), (r'"', String, "#pop"), (r'[^"\\{]+', String)],
        "texte_long": [(r'"""', String, "#pop"), (r'[^"]+', String), (r'"', String)],
    }
