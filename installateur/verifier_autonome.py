"""Test fonctionnel de la distribution, sans réseau et hors du dépôt.

    python installateur/verifier_autonome.py dist/nck/nck

Le Python de construction prépare les fixtures ; toutes les commandes NCK passent
ensuite par l'exécutable fourni, sans PYTHONPATH/PYTHONHOME ni Python dans le PATH.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

RACINE = Path(__file__).resolve().parents[1]
if str(RACINE) not in sys.path:
    sys.path.insert(0, str(RACINE))

from outils.preparer_paquet import preparer


class ErreurValidation(Exception):
    pass


def verifier(commande: list[str], distribution: Path, autonome: bool = True) -> None:
    exemple = distribution / 'exemples/paquets/maths-plus'
    if not (exemple / 'paquet.json').is_file():
        raise ErreurValidation(f"exemple de paquet manquant dans la distribution : {exemple}")
    env = os.environ.copy()
    env.pop('PYTHONPATH', None)
    env.pop('PYTHONHOME', None)
    if autonome:
        env['PATH'] = str(Path(commande[0]).parent)
    env['PYTHONUTF8'] = '1'
    env['PYTHONIOENCODING'] = 'utf-8'

    with tempfile.TemporaryDirectory(prefix='nck-validation-') as temp:
        racine = Path(temp)
        registre = racine / 'registre local é'
        archive, index = preparer(exemple, registre)
        projet = racine / 'projet avec espaces é'
        projet.mkdir()
        env['NCK_INDEX'] = str(index)

        def lancer(*args, attendu=0, sortie=None):
            resultat = subprocess.run([*commande, *args], cwd=projet, env=env,
                                      capture_output=True, text=True, encoding='utf-8', timeout=60)
            if resultat.returncode != attendu or (sortie is not None and sortie not in resultat.stdout):
                raise ErreurValidation(
                    f"échec de {' '.join(args)} (code {resultat.returncode}, attendu {attendu})\n"
                    f"{resultat.stdout}{resultat.stderr}")
            return resultat

        lancer('--version', sortie='nck ')
        info = lancer('info')
        if autonome and 'Autonome (sans Python installé) : oui' not in info.stdout:
            raise ErreurValidation('le programme testé ne se déclare pas autonome')
        lancer('init', '--nom', 'essai-autonome')
        # Une dépendance transitive vérifie aussi la résolution dans le binaire.
        lib = racine / 'lib-haut'
        lib.mkdir()
        (lib / 'paquet.json').write_text(json.dumps({
            'nom': 'calculs', 'version': '1.0.0', 'point_entree': 'module.nck',
            'dependances': {'maths-plus': '^1.0'},
        }), encoding='utf-8')
        (lib / 'module.nck').write_text(
            'depuis "maths-plus" importer carre, cube\n'
            'fonction resultat() -> entier: retourner carre(5) + cube(3)\n', encoding='utf-8')
        preparer(lib, registre)
        lancer('installer', 'calculs')
        lancer('paquets', sortie='maths-plus@1.0.0 (transitive)')
        programme = projet / 'module.nck'
        programme.write_text('importer "calculs"\necrire(calculs.resultat())\n', encoding='utf-8')
        lancer('verifier', str(programme), sortie='aucune erreur')
        lancer(str(programme), sortie='52\n')
        verrou = (projet / 'paquet.verrou.json').read_bytes()
        shutil.rmtree(projet / 'nck_modules')
        index.unlink()  # La réinstallation doit fonctionner sans consulter l'index.
        lancer('installer')
        if (projet / 'paquet.verrou.json').read_bytes() != verrou:
            raise ErreurValidation('le verrou a changé pendant la réinstallation')
        lancer(str(programme), sortie='52\n')
        archive.write_bytes(b'archive alteree')
        erreur = lancer('installer', attendu=1)
        if 'SHA-256 incorrect' not in erreur.stderr:
            raise ErreurValidation(f"archive corrompue non détectée : {erreur.stderr}")
        if (projet / 'paquet.verrou.json').read_bytes() != verrou:
            raise ErreurValidation('une installation échouée a modifié le verrou')
        lancer(str(programme), sortie='52\n')
        lancer('desinstaller', 'calculs')
        lancer('paquets', sortie='Aucun paquet installé.')
    print('Validation réussie : exécution, dépendances transitives, verrou, SHA-256 et désinstallation.')


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('executable', type=Path)
    args = ap.parse_args(argv)
    executable = args.executable.resolve()
    try:
        if not executable.is_file():
            raise ErreurValidation(f'exécutable introuvable : {executable}')
        verifier([str(executable)], executable.parent)
    except (ErreurValidation, OSError, subprocess.TimeoutExpired) as exc:
        print(f'Erreur de validation : {exc}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
