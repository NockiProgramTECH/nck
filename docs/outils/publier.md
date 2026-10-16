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
| `editeurs/vscode/` | extension VS Code |
| `installateur/` | PyInstaller, Inno Setup, scripts d'installation |
| `docs/`, `mkdocs.yml` | ce site |
| `tests/` | tests pytest |

## Construire l'exécutable autonome

```bash
pip install pyinstaller
python installateur/construire.py        # → dist/nck/ + archive .tar.gz ou .zip
```

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
teste chaque exécutable et publie la Release.

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
