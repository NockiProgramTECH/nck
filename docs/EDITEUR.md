# NCK dans VS Code : coloration, autocomplétion, survol, erreurs en direct

L'extension se trouve dans `editeurs/vscode/`. Elle fonctionne comme Pylance pour Python :
un **serveur d'analyse** écrit en Python (`nck serveur`) est lancé par VS Code et répond aux demandes
de l'éditeur. Il n'y a **aucune dépendance npm** à installer.

## Fonctionnalités

| Fonctionnalité | Comment | Détail |
|---|---|---|
| Coloration syntaxique | automatique | mots-clés, types, natifs, classes, `f"..."`, commentaires |
| Erreurs en direct | en tapant (300 ms) | erreurs de syntaxe **et de type** soulignées en rouge, sans exécuter |
| Autocomplétion | `Ctrl+Espace` ou en tapant | variables/fonctions/classes visibles, natifs avec leur signature, mots-clés, types |
| Complétion des membres | après `objet.`, `soi.`, `module.` | champs et méthodes de la classe, exports du module |
| Survol (hover) | souris sur un nom | type d'une variable, signature d'une fonction/méthode, champs d'une classe, doc des natifs et mots-clés |
| Aide à la signature | en tapant `(` ou `,` | paramètres de la fonction, paramètre courant en gras |
| Aller à la définition | `F12` / `Ctrl+clic` | variables, fonctions, classes, méthodes, champs, y compris dans un module importé |
| Exécuter | `F5` ou bouton ▶ | lance `nck fichier.nck` dans le terminal intégré |
| Indentation / repli | automatique | indentation après `:`, dédentation sur `fin`/`sinon`, repli des blocs |

## Installation

### 1. Rendre le paquet `nck` accessible à Python

Au choix :

```bash
cd nck            # le dépôt
pip install -e .  # recommandé : la commande `nck` et le module sont installés
```

ou, sans installer, indiquez le dossier du dépôt dans le réglage `nck.dossierNck` (voir plus bas).

### 2. Installer l'extension

```bash
# Linux / macOS
cp -r editeurs/vscode ~/.vscode/extensions/nck-lang
# Windows (PowerShell)
Copy-Item -Recurse editeurs\vscode "$env:USERPROFILE\.vscode\extensions\nck-lang"
```

Puis redémarrez VS Code (ou `Ctrl+Shift+P` → *Developer: Reload Window*) et ouvrez un fichier `.nck`.

> Pour la développer : ouvrez le dossier `editeurs/vscode` dans VS Code et appuyez sur `F5`
> (fenêtre « Extension Development Host »).

### 3. Réglages (facultatif)

`Fichier → Préférences → Paramètres`, recherchez « NCK » :

| Réglage | Rôle | Exemple |
|---|---|---|
| `nck.python` | commande Python à utiliser | `python3`, `python`, `C:\Python312\python.exe`, `.venv/bin/python` |
| `nck.dossierNck` | dossier du dépôt si `nck` n'est pas installé avec pip | `/home/moi/projets/nck` |

## En cas de problème

- Ouvrez le panneau *Affichage → Sortie* et choisissez **NCK** : les messages du serveur y sont affichés.
- Testez le serveur à la main : `python3 -m nck serveur` puis tapez
  `{"id":1,"methode":"analyser","fichier":"t.nck","texte":"ecrire(1 +)"}` et Entrée → une réponse JSON doit s'afficher.
- « No module named nck » : installez le paquet (`pip install -e .`) ou remplissez `nck.dossierNck`.

## Pour les autres éditeurs

Le serveur parle un protocole minimal (une ligne JSON par requête, voir `nck/serveur.py`) :
méthodes `analyser`, `completer`, `survoler`, `signature`, `definition`, `fermer`.
Il est facile d'écrire un client pour un autre éditeur ; une version LSP standard est envisageable plus tard.
