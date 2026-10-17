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


def erreur_interne(exc: BaseException) -> int:
    """Une exception Python inattendue : message NCK propre, trace complète seulement avec NCK_DEBUG=1."""
    import traceback
    if os.environ.get("NCK_DEBUG"):
        traceback.print_exc()
    nom = type(exc).__name__
    detail = str(exc)
    if isinstance(exc, OverflowError):
        msg = "nombre trop grand pour un reel (dépassement de capacité)"
    elif isinstance(exc, MemoryError):
        msg = "mémoire insuffisante"
    elif isinstance(exc, RecursionError):
        msg = "récursion trop profonde (pile épuisée)"
    else:
        msg = f"erreur interne de NCK ({nom}{' : ' + detail if detail else ''})"
    print(f"Erreur : {msg}", file=sys.stderr)
    if not isinstance(exc, (OverflowError, MemoryError, RecursionError)):
        print("  Ceci est un bogue de NCK, pas de votre programme. Relancez avec NCK_DEBUG=1 pour la trace complète.",
              file=sys.stderr)
    return 2


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
    except Exception as exc:  # noqa: BLE001
        return erreur_interne(exc)
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


BANNIERE = """\
  _   _  ____ _  __
 | \\ | |/ ___| |/ /   NCK {version} — langage de programmation simple, typé et en français
 |  \\| | |   | ' /    {ou}
 | |\\  | |___| . \\    nck fichier.nck        exécuter un programme
 |_| \\_|\\____|_|\\_\\   nck verifier f.nck     vérifier sans exécuter
                      nck repl               mode interactif    |  nck --help : toutes les commandes
"""


def banniere() -> str:
    import shutil
    exe = shutil.which("nck") or sys.argv[0]
    return BANNIERE.format(version=__version__, ou=f"installé : {exe}")


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


def _sortie_utf8() -> None:
    """Sortie en UTF-8 partout (Windows utilise cp1252 par défaut quand la sortie est redirigée)."""
    for flux in (sys.stdout, sys.stderr):
        try:
            if flux and (flux.encoding or "").lower().replace("-", "") != "utf8":
                flux.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass


def main(argv: list[str] | None = None) -> int:
    _sortie_utf8()
    ap = argparse.ArgumentParser(
        prog="nck",
        description="NCK — langage de programmation simple, typé et en français.",
    )
    ap.add_argument("--version", action="version", version=f"nck {__version__}")
    sous = ap.add_subparsers(dest="commande")
    p_exec = sous.add_parser("executer", help="exécute un fichier .nck (commande par défaut)")
    p_exec.add_argument("fichier")
    p_exec.add_argument("arguments", nargs=argparse.REMAINDER, help="arguments passés au programme (arguments())")
    p_verif = sous.add_parser("verifier", help="vérifie la syntaxe et les types sans exécuter")
    p_verif.add_argument("fichier")
    sous.add_parser("repl", help="mode interactif")
    sous.add_parser("serveur", help="serveur d'analyse pour les éditeurs (autocomplétion, survol, erreurs)")
    sous.add_parser("info", help="affiche la version et l'emplacement de NCK")

    p_init = sous.add_parser("init", help="crée un projet NCK (paquet.json)")
    p_init.add_argument("--nom", help="nom du projet (exemple : maths-plus)")
    p_install = sous.add_parser("installer", help="installe un paquet ou les dépendances du projet")
    p_install.add_argument("paquet", nargs="?", help="nom ou nom@version (exemple : maths-plus@^1.2)")
    p_install.add_argument("--index", help="URL HTTPS ou chemin d'un index JSON local")
    p_remove = sous.add_parser("desinstaller", help="retire une dépendance directe et les paquets inutilisés")
    p_remove.add_argument("paquet")
    p_remove.add_argument("--index", help="URL HTTPS ou chemin d'un index JSON local")
    sous.add_parser("paquets", help="liste les dépendances installées")

    args = argv if argv is not None else sys.argv[1:]
    if not args:
        print(banniere())
        return repl()
    # Raccourci : `nck fichier.nck`
    commandes = ("executer", "verifier", "repl", "serveur", "info", "init", "installer",
                 "desinstaller", "paquets", "-h", "--help", "--version")
    if args and args[0] not in commandes:
        args = ["executer", *args]
    ns = ap.parse_args(args)

    if ns.commande in ("init", "installer", "desinstaller", "paquets"):
        from .paquets import ErreurPaquet, initialiser, installer, lister
        try:
            if ns.commande == "init":
                print(f"Projet créé : {initialiser(ns.nom)}")
            elif ns.commande == "paquets":
                print("\n".join(lister()) or "Aucun paquet installé.")
            else:
                choix = installer(ns.paquet if ns.commande == "installer" else None, ns.index,
                                  ns.paquet if ns.commande == "desinstaller" else None)
                print("Dépendances installées : " + (", ".join(f"{n}@{v}" for n, v in choix.items()) or "aucune"))
            return 0
        except (ErreurPaquet, OSError) as exc:
            print(f"Erreur : {exc}", file=sys.stderr)
            return 1
    if ns.commande == "executer":
        from . import natifs
        natifs.ARGUMENTS[:] = ns.arguments
        return commande_executer(ns.fichier)
    if ns.commande == "verifier":
        return commande_verifier(ns.fichier)
    if ns.commande == "serveur":
        from .serveur import main as serveur_main
        return serveur_main()
    if ns.commande == "info":
        print(banniere())
        print(f"Python : {sys.version.split()[0]}  ({sys.executable})")
        print(f"Paquet : {os.path.dirname(os.path.abspath(__file__))}")
        print(f"Autonome (sans Python installé) : {'oui' if getattr(sys, 'frozen', False) else 'non'}")
        return 0
    return repl()


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
