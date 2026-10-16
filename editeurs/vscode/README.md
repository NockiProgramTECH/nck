# Extension VS Code pour NCK

Coloration syntaxique, commentaires, auto-fermeture des parenthèses/guillemets, indentation et repli
des blocs (`:` … `fin`) pour les fichiers `.nck`.

## Installation (sans Marketplace)

```bash
# Linux / macOS
cp -r editeurs/vscode ~/.vscode/extensions/nck-lang
# Windows (PowerShell)
Copy-Item -Recurse editeurs\vscode "$env:USERPROFILE\.vscode\extensions\nck-lang"
```

Redémarrez VS Code. Pour la développer : ouvrez ce dossier dans VS Code et appuyez sur `F5`
(« Extension Development Host »).

## Publication (plus tard)

```bash
npm install -g @vscode/vsce
cd editeurs/vscode && vsce package     # produit nck-lang-0.1.0.vsix
code --install-extension nck-lang-0.1.0.vsix
```
