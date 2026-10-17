# Installer NCK

NCK s'installe **sans Python** : l'exécutable `nck` embarque tout ce qu'il lui faut.
Les releases officielles ciblent **Linux x64/arm64 et Windows x64**. Les fichiers sont disponibles dans les [Releases GitHub](https://github.com/NockiProgramTECH/nck/releases).

| Fichier de la release | Pour |
|---|---|
| `NCK-Setup-<version>.exe` | Windows — **assistant d'installation** (recommandé) |
| `nck-<version>-windows-x64.zip` | Windows — archive portable |
| `nck-<version>-linux-x64.tar.gz`, `…-linux-arm64.tar.gz` | Linux |

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

## Linux

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

À la main : décompressez l'archive `.tar.gz` et ajoutez le dossier `nck/` à votre PATH.

---

## macOS — support autonome reporté

Les nouvelles releases ne produisent pas d'exécutable macOS. L'installateur
`installer.sh` s'arrête sur macOS avec un message explicite, sans télécharger ni
modifier l'installation existante. Les anciennes archives éventuellement publiées
restent des fichiers historiques, pas une garantie de support de la v0.13.

Pour expérimenter, utilisez [l'installation depuis le dépôt](#pour-les-developpeurs-installer-depuis-le-depot)
avec Python 3.10 ou plus récent. Ce parcours n'est pas validé sur macOS par la CI
actuelle. Les scripts de construction restent disponibles pour une reprise future.

GitHub Actions peut construire sur des runners macOS sans Mac personnel ; la
réactivation attendra une validation adaptée de l'installation et de l'exécution.

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
| Linux | relancez `installer.sh` | `rm -rf ~/.nck ~/.local/bin/nck ~/.vscode/extensions/nck-lang` |

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

Windows, pour l'assistant `NCK-Setup.exe` — **un seul script** qui construit l'exécutable, installe Inno Setup s'il manque (via `winget`) et compile :

```powershell
powershell -ExecutionPolicy Bypass -File installateur\windows\construire_setup.ps1   # → dist\NCK-Setup-0.12.0.exe
```

> `iscc` n'est **pas** une commande fournie par Windows : elle vient d'[Inno Setup 6](https://jrsoftware.org/isdl.php)
> (`winget install JRSoftware.InnoSetup`). Après installation, elle n'est pas dans le PATH ; appelez-la par son chemin complet :
> `& "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe" /DVersion=0.12.0 installateur\windows\nck.iss`
> — ou laissez simplement GitHub Actions le faire (voir « Publier une version »).

Fichiers concernés :

| Fichier | Rôle |
|---|---|
| `installateur/nck.spec` | recette PyInstaller (exécutable `nck`, exemples, docs, extension VS Code embarqués) |
| `installateur/lanceur.py` | point d'entrée de l'exécutable |
| `installateur/construire.py` | construit puis archive `dist/nck/` |
| `installateur/windows/nck.iss` | assistant Windows (PATH, associations, menu contextuel, extension VS Code) |
| `installateur/windows/construire_setup.ps1` | construit l'exécutable puis `NCK-Setup.exe` (installe Inno Setup au besoin) |
| `installateur/installer.sh`, `installer.ps1` | installateurs en ligne de commande |
| `.github/workflows/release.yml` | à chaque tag `vX.Y.Z` : construit Linux x64/arm64 et Windows x64 (+ Setup), puis publie la Release |

### Publier une version

```bash
# 1. mettre à jour nck/__init__.py (__version__) et CHANGELOG.md
git tag v0.12.0 && git push origin v0.12.0
# 2. GitHub Actions construit et attache les fichiers à la Release v0.12.0
```

> Les scripts `installer.sh` / `installer.ps1` et les liens de téléchargement exigent que le dépôt soit **public**
> (ou que l'utilisateur soit authentifié). Tant que le dépôt est privé, distribuez directement les fichiers de la Release.
