# Installer NCK

NCK s'installe **sans Python** : l'exécutable `nck` embarque tout ce qu'il lui faut.
Toutes les versions sont publiées dans les [Releases GitHub](https://github.com/NockiProgramTECH/nck/releases).

| Fichier de la release | Pour |
|---|---|
| `NCK-Setup-<version>.exe` | Windows — **assistant d'installation** (recommandé) |
| `nck-<version>-windows-x64.zip` | Windows — archive portable |
| `nck-<version>-linux-x64.tar.gz`, `…-linux-arm64.tar.gz` | Linux |
| `nck-<version>-macos-x64.tar.gz`, `…-macos-arm64.tar.gz` | macOS (Intel / Apple Silicon) |

---

## Windows

### Avec l'assistant (recommandé)

1. Téléchargez **`NCK-Setup-<version>.exe`** et lancez-le.
2. Choisissez les options :
   - **Ajouter nck au PATH** → la commande `nck` fonctionne dans tous les terminaux (coché par défaut) ;
   - **Associer les fichiers `.nck`** → icône NCK et double-clic pour exécuter (coché) ;
   - **Menu contextuel** → clic droit sur un `.nck` : *Exécuter avec NCK*, *Vérifier avec NCK* (coché) ;
   - **Extension Visual Studio Code** → coloration, erreurs en direct, complétion (si VS Code est installé) ;
   - **Exemples** → copiés dans `Documents\NCK\exemples`.
3. Terminez, **ouvrez un nouveau terminal** et tapez :

```
nck info
```

L'installation se fait par défaut pour l'utilisateur courant (aucun droit administrateur requis) dans
`C:\Users\<vous>\AppData\Local\Programs\NCK`. Désinstallation : *Paramètres → Applications → NCK*
(le PATH et les associations sont nettoyés).

### En ligne de commande (PowerShell)

```powershell
irm https://raw.githubusercontent.com/NockiProgramTECH/nck/main/installateur/installer.ps1 | iex
```

Installe dans `%LOCALAPPDATA%\NCK`, ajoute le dossier au PATH utilisateur et installe l'extension VS Code si VS Code est présent.
Variables facultatives : `$env:NCK_VERSION = "0.12.0"`, `$env:NCK_PREFIX = "D:\Outils\NCK"`.

### Archive portable

Décompressez `nck-<version>-windows-x64.zip` où vous voulez : `nck\nck.exe` fonctionne tel quel (clé USB, dossier partagé…).

---

## Linux et macOS

```sh
curl -fsSL https://raw.githubusercontent.com/NockiProgramTECH/nck/main/installateur/installer.sh | sh
```

Le script :
- détecte le système et l'architecture, télécharge la dernière release ;
- installe dans `~/.nck` et crée le lien `~/.local/bin/nck` ;
- ajoute `~/.local/bin` au PATH (`.bashrc`, `.zshrc`, `.profile`) si nécessaire ;
- installe l'extension VS Code dans `~/.vscode/extensions/nck-lang` si VS Code est présent.

Variables facultatives : `NCK_VERSION=0.12.0`, `NCK_PREFIX=/opt/nck`, `NCK_BIN=/usr/local/bin` (avec `sudo`).

Ouvrez ensuite un nouveau terminal : `nck info`.

> **macOS** : si le système affiche « nck ne peut pas être ouvert car il provient d'un développeur non identifié »,
> exécutez une fois `xattr -dr com.apple.quarantine ~/.nck`.

À la main : décompressez l'archive `.tar.gz` et ajoutez le dossier `nck/` à votre PATH.

---

## Vérifier l'installation

```
$ nck info
  _   _  ____ _  __
 | \ | |/ ___| |/ /   NCK 0.12.0 — langage de programmation simple, typé et en français
 |  \| | |   | ' /    installé : /home/moi/.nck/nck
 ...
Autonome (sans Python installé) : oui

$ nck ~/.nck/exemples/bonjour.nck
```

- `nck` seul → bannière puis mode interactif (REPL) ;
- `nck fichier.nck` → exécute ; `nck verifier fichier.nck` → vérifie les types sans exécuter ;
- `nck --help` → toutes les commandes.

Les exemples et la documentation sont fournis avec l'installation (`exemples/`, `docs/` à côté de l'exécutable).

---

## Mettre à jour / désinstaller

| | Mettre à jour | Désinstaller |
|---|---|---|
| Windows (Setup) | lancez le nouveau `NCK-Setup` | *Paramètres → Applications → NCK* |
| Windows (script) | relancez `installer.ps1` | supprimez `%LOCALAPPDATA%\NCK` et retirez-le du PATH |
| Linux / macOS | relancez `installer.sh` | `rm -rf ~/.nck ~/.local/bin/nck ~/.vscode/extensions/nck-lang` |

---

## Pour les développeurs : installer depuis le dépôt

Python 3.10+ requis :

```bash
git clone https://github.com/NockiProgramTECH/nck.git
cd nck
pip install -e .          # commande `nck` + module `python -m nck`
pytest                    # tests
```

### Construire soi-même l'exécutable et l'installateur

```bash
pip install pyinstaller
python installateur/construire.py        # → dist/nck/ + dist/nck-<version>-<os>-<arch>.tar.gz|zip
```

Windows, en plus (avec [Inno Setup 6](https://jrsoftware.org/isinfo.php)) :

```powershell
iscc /DVersion=0.12.0 installateur\windows\nck.iss   # → dist\NCK-Setup-0.12.0.exe
```

Fichiers concernés :

| Fichier | Rôle |
|---|---|
| `installateur/nck.spec` | recette PyInstaller (exécutable `nck`, exemples, docs, extension VS Code embarqués) |
| `installateur/lanceur.py` | point d'entrée de l'exécutable |
| `installateur/construire.py` | construit puis archive `dist/nck/` |
| `installateur/windows/nck.iss` | assistant Windows (PATH, associations, menu contextuel, extension VS Code) |
| `installateur/installer.sh`, `installer.ps1` | installateurs en ligne de commande |
| `.github/workflows/release.yml` | à chaque tag `vX.Y.Z` : construit pour les 5 plateformes et publie la Release |

### Publier une version

```bash
# 1. mettre à jour nck/__init__.py (__version__) et CHANGELOG.md
git tag v0.12.0 && git push origin v0.12.0
# 2. GitHub Actions construit et attache les fichiers à la Release v0.12.0
```

> Les scripts `installer.sh` / `installer.ps1` et les liens de téléchargement exigent que le dépôt soit **public**
> (ou que l'utilisateur soit authentifié). Tant que le dépôt est privé, distribuez directement les fichiers de la Release.
