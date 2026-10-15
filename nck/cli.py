"""Ligne de commande : `nck fichier.nck`, `nck verifier fichier.nck`, `nck` (mode interactif)."""

import argparse
import os
import sys

from . import __version__, compiler_source, executer_source
from .erreurs import ErreurNck, ErreurSyntaxe
from .interpreteur import Interpreteur
from .natifs import vers_texte
from .parseur import parser as parser_nck
from .verificateur import Verificateur

EXTENSION = ".nck"


def lire_fichier(chemin: str) -> str:
    if not chemin.endswith(EXTENSION):
        print(f"Erreur : le fichier doit avoir l'extension {EXTENSION} (reçu : {chemin})", file=sys.stderr)
        sys.exit(2)
    try:
        with open(chemin, encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        print(f"Erreur : fichier introuvable : {chemin}", file=sys.stderr)
        sys.exit(2)


def afficher_erreur(e: ErreurNck, source: str, chemin: str | None = None) -> None:
    if chemin is not None and e.fichier != chemin and os.path.exists(e.fichier):
        with open(e.fichier, encoding="utf-8") as f:
            source = f.read()
    print(e.formater(source), file=sys.stderr)


def commande_executer(chemin: str) -> int:
    source = lire_fichier(chemin)
    try:
        executer_source(source, chemin)
    except ErreurNck as e:
        afficher_erreur(e, source, chemin)
        return 1
    except KeyboardInterrupt:
        print("\nInterrompu.", file=sys.stderr)
        return 130
    except SystemExit as e:
        return int(e.code or 0)
    return 0


def commande_verifier(chemin: str) -> int:
    source = lire_fichier(chemin)
    try:
        compiler_source(source, chemin)
    except ErreurNck as e:
        afficher_erreur(e, source, chemin)
        return 1
    print(f"✓ {chemin} : aucune erreur")
    return 0


def repl() -> int:
    print(f"NCK {__version__} — mode interactif. Tapez 'quitter()' ou Ctrl-D pour sortir.")
    verif = Verificateur("<repl>", mode_repl=True)
    interp = Interpreteur("<repl>")
    tampon: list[str] = []
    while True:
        try:
            ligne = input("... " if tampon else "nck> ")
        except EOFError:
            print()
            return 0
        except KeyboardInterrupt:
            print()
            tampon = []
            continue
        tampon.append(ligne)
        source = "\n".join(tampon)
        if not source.strip():
            tampon = []
            continue
        try:
            prog = parser_nck(source, "<repl>")
        except ErreurSyntaxe as e:
            # Bloc incomplet : on attend la suite.
            if "'fin' attendu" in e.message or "la fin du fichier" in e.message:
                continue
            afficher_erreur(e, source)
            tampon = []
            continue
        except ErreurNck as e:
            afficher_erreur(e, source)
            tampon = []
            continue
        tampon = []
        try:
            # On conserve la portée du vérificateur d'une ligne à l'autre.
            verif.pre_declarer_fonctions(prog.instructions)
            for instr in prog.instructions:
                verif.instruction(instr)
            # Affiche la valeur d'une expression seule (ex : `1 + 2`).
            from .arbre import Appel, ExprInstr
            if len(prog.instructions) == 1 and isinstance(prog.instructions[0], ExprInstr):
                fn = interp.expression(prog.instructions[0].expr)
                valeur = fn(interp.global_env)
                if valeur is not None or not isinstance(prog.instructions[0].expr, Appel):
                    print(vers_texte(valeur))
            else:
                interp.compiler_instructions(prog.instructions)(interp.global_env)
        except ErreurNck as e:
            afficher_erreur(e, source)
        except SystemExit as e:
            return int(e.code or 0)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="nck",
        description="NCK — langage de programmation simple, typé et en français.",
    )
    ap.add_argument("--version", action="version", version=f"nck {__version__}")
    sous = ap.add_subparsers(dest="commande")
    p_exec = sous.add_parser("executer", help="exécute un fichier .nck (commande par défaut)")
    p_exec.add_argument("fichier")
    p_verif = sous.add_parser("verifier", help="vérifie la syntaxe et les types sans exécuter")
    p_verif.add_argument("fichier")
    sous.add_parser("repl", help="mode interactif")

    args = argv if argv is not None else sys.argv[1:]
    # Raccourci : `nck fichier.nck`
    if args and args[0] not in ("executer", "verifier", "repl", "-h", "--help", "--version"):
        args = ["executer", *args]
    ns = ap.parse_args(args)

    if ns.commande == "executer":
        return commande_executer(ns.fichier)
    if ns.commande == "verifier":
        return commande_verifier(ns.fichier)
    return repl()


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
