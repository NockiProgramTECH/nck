"""Vérifie que tous les blocs ```nck de la documentation passent `nck verifier`, puis s'exécutent sans erreur.

    python outils/verifier_doc.py [docs/]

Un bloc dont la ligne d'ouverture contient `title="x.nck"` est écrit sous ce nom (utile pour les modules).
Un bloc contenant le marqueur `// erreur attendue` doit échouer à la vérification.
"""
import os
import re
import subprocess
import sys
import tempfile

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# LANGAGE.md est la référence condensée : ses extraits sont volontairement fragmentaires (ex. une ligne `pour` sans corps).
EXCLUS = {"LANGAGE.md"}
BLOC = re.compile(r"^```nck([^\n]*)\n(.*?)^```", re.S | re.M)


def main(dossier: str = "docs") -> int:
    echecs = 0
    total = 0
    fichiers = sorted(
        os.path.join(r, f) for r, _, fs in os.walk(os.path.join(RACINE, dossier)) for f in fs if f.endswith(".md")
    )
    with tempfile.TemporaryDirectory() as tmp:
        for chemin in fichiers:
            if os.path.basename(chemin) in EXCLUS:
                continue
            texte = open(chemin, encoding="utf-8").read()
            for i, m in enumerate(BLOC.finditer(texte), 1):
                entete, code = m.group(1), m.group(2)
                total += 1
                nom = re.search(r'title="([^"]+)"', entete)
                fichier = os.path.join(tmp, nom.group(1) if nom else f"bloc_{total}.nck")
                os.makedirs(os.path.dirname(fichier), exist_ok=True)
                with open(fichier, "w", encoding="utf-8") as f:
                    f.write(code)
                r = subprocess.run([sys.executable, "-m", "nck", "verifier", fichier], capture_output=True,
                                   text=True, encoding="utf-8", cwd=tmp)
                attendu_echec = "// erreur attendue" in code
                ok = (r.returncode != 0) if attendu_echec else (r.returncode == 0)
                # Exécution aussi, quand le bloc ne nécessite ni saisie interactive ni interface graphique.
                sans_execution = "// nécessite un environnement graphique" in code
                if (ok and not attendu_echec and not sans_execution
                        and "lire(" not in code and "arguments()" not in code):
                    try:
                        r = subprocess.run([sys.executable, "-m", "nck", fichier], capture_output=True, text=True,
                                           encoding="utf-8", cwd=tmp, timeout=20)
                        ok = r.returncode == 0
                    except subprocess.TimeoutExpired:
                        ok = False
                if not ok:
                    echecs += 1
                    ligne = texte[: m.start()].count("\n") + 1
                    rel = os.path.relpath(chemin, RACINE)
                    print(f"✗ {rel}:{ligne} (bloc {i})")
                    print("   " + (r.stdout + r.stderr).strip().replace("\n", "\n   "))
    print(f"{total - echecs}/{total} blocs nck valides")
    return 1 if echecs else 0


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:]))
