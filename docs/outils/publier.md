# Construire et publier NCK

Cette page s'adresse aux personnes qui veulent **contribuer** au langage ou produire leurs propres exécutables.
Pour simplement installer NCK, voir [Installation](../INSTALLATION.md).

## Installer depuis le dépôt

Python 3.10 ou plus récent :

```bash
git clone https://github.com/NockiProgramTECH/nck.git
cd nck
pip install -e ".[dev]"
pytest                         # tests
python outils/verifier_doc.py  # vérifie et exécute tous les exemples de la documentation
```

## Structure du dépôt

| Dossier / fichier | Rôle |
|---|---|
| `nck/lexeur.py` | découpe le texte en jetons |
| `nck/parseur.py` | construit l'arbre syntaxique (`nck/arbre.py`) |
| `nck/verificateur.py` | vérification des types, affinement, exhaustivité |
| `nck/interpreteur.py` | exécution de l'arbre |
| `nck/natifs.py`, `nck/documentation.py` | fonctions natives et leur documentation (survol VS Code, `NATIFS.md`) |
| `nck/analyse.py`, `nck/serveur.py` | complétion, survol, définition — serveur pour l'extension |
| `nck/cli.py` | commande `nck` |
| `nck/paquets.py`, `outils/preparer_paquet.py` | gestionnaire et préparation de bibliothèques |
| `editeurs/vscode/` | extension VS Code |
| `installateur/` | PyInstaller, Inno Setup, scripts d'installation |
| `docs/`, `mkdocs.yml` | ce site |
| `tests/` | tests pytest |

## Construire l'exécutable autonome

```bash
pip install pyinstaller
python installateur/construire.py        # → dist/nck/ + archive .tar.gz ou .zip
```

La construction vérifie d'abord PyInstaller et la bibliothèque partagée du Python
utilisé. Si cette bibliothèque manque, elle s'arrête **sans supprimer les anciens
artefacts**. Sur Debian/Ubuntu, installez le paquet `libpython` correspondant à votre
version (par exemple `libpython3.11` pour Python 3.11) ou utilisez un Python compilé
avec bibliothèque partagée. Les runners GitHub utilisent `actions/setup-python`.

Après construction, validez la distribution hors du dépôt et sans réseau :

```bash
python installateur/verifier_autonome.py dist/nck/nck
```

Sous Windows, utilisez `dist/nck/nck.exe`. Le scénario lance le binaire avec un
`PATH` réduit à son dossier et sans `PYTHONPATH`/`PYTHONHOME`. Il vérifie le mode
autonome, la CLI, l'installation de dépendances transitives depuis un index local,
la vérification des types, l'exécution, le verrou inchangé lors d'une réinstallation
sans index, le refus d'un SHA-256 incorrect sans perte de l'installation et la
désinstallation. Les dossiers de test ont des espaces et des caractères accentués.
Le Python de construction ne sert qu'à préparer les fixtures et lancer les commandes.

Windows, pour l'assistant `NCK-Setup.exe` (installe Inno Setup s'il manque) :

```powershell
powershell -ExecutionPolicy Bypass -File installateur\windows\construire_setup.ps1
```

## Publier une version

1. Mettre à jour `nck/__init__.py` (`__version__`) et `CHANGELOG.md`.
2. Pousser un tag :

```bash
git tag v0.13.0
git push origin v0.13.0
```

GitHub Actions (`.github/workflows/release.yml`) construit Linux x64/arm64, Windows x64 (+ Setup), macOS x64/arm64,
teste chaque exécutable avec ce scénario et publie la Release uniquement si toutes
les constructions et validations réussissent. Un lancement manuel du workflow
construit les artefacts sans publier de release (absence de tag).

## Préparer une bibliothèque NCK

```bash
python outils/preparer_paquet.py exemples/paquets/maths-plus --sortie registre-local
```

Cet outil ne publie rien : il génère une archive reproductible, calcule son SHA-256
et met à jour un index local sans écraser une version existante. `--url-base` permet
de préparer un index HTTPS pour une publication manuelle. Consultez le
[guide des paquets](../PAQUETS.md) pour le format et la procédure de déploiement.

## Construire ce site de documentation

```bash
pip install mkdocs-material ./outils/pygments_nck
mkdocs serve          # aperçu local sur http://127.0.0.1:8000
mkdocs build          # → site/
```

Le site est publié automatiquement sur GitHub Pages par `.github/workflows/docs.yml` à chaque modification de `docs/`
ou `mkdocs.yml`. Tous les blocs `nck` de la documentation sont vérifiés et exécutés par `outils/verifier_doc.py` (en CI aussi).

### Nom de domaine personnalisé

Pour servir le site sur votre propre domaine (ex. `docs.nck-lang.org`) :

1. créez le fichier `docs/CNAME` contenant le domaine (une ligne) — il est copié tel quel dans le site ;
2. chez votre registrar, ajoutez un enregistrement `CNAME` de `docs` vers `nockiprogramtech.github.io` ;
3. dans GitHub → *Settings → Pages*, renseignez le domaine et cochez *Enforce HTTPS* ;
4. mettez `site_url` à jour dans `mkdocs.yml`.
