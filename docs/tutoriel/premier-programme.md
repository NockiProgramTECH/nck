# Premier programme

Cinq minutes pour écrire, vérifier et exécuter votre premier programme NCK.

## 1. Vérifier l'installation

Ouvrez un terminal et tapez :

```bash
nck info
```

Vous devez voir la bannière NCK et la version. Sinon, suivez la page [Installation](../INSTALLATION.md).

## 2. Écrire le fichier

Créez un fichier `bonjour.nck` (n'importe quel éditeur ; [VS Code](../EDITEUR.md) est recommandé) :

```nck title="bonjour.nck"
// Mon premier programme NCK
variable nom = lire("Comment vous appelez-vous ? ")
variable age: entier = entier(lire("Quel âge avez-vous ? "))

si age >= 18:
    ecrire(f"Bonjour {nom}, vous êtes majeur.")
sinon:
    ecrire(f"Bonjour {nom}, encore {18 - age} an(s) avant la majorité.")
fin
```

Trois choses à remarquer :

1. `variable` déclare une variable ; le type est **déduit** (`nom` est un `texte`) ou **écrit** (`age: entier`).
2. Un bloc commence par `:` et se termine par `fin`.
3. `f"…{expression}…"` insère des valeurs dans un texte.

## 3. Vérifier sans exécuter

```bash
nck verifier bonjour.nck
```

NCK lit tout le programme et vérifie la syntaxe **et les types** avant d'exécuter quoi que ce soit.
Essayez d'écrire `age = "vingt"` à la fin du fichier : 

```text
Erreur de type : 'age' est de type entier, mais reçoit un texte
  --> bonjour.nck:10:7
   |
 10| age = "vingt"
   |       ^
```

## 4. Exécuter

```bash
nck bonjour.nck
```

```text
Comment vous appelez-vous ? Awa
Quel âge avez-vous ? 20
Bonjour Awa, vous êtes majeur.
```

Sous Windows, vous pouvez aussi **double-cliquer** sur le fichier `.nck` (si l'association a été cochée à l'installation),
ou faire clic droit → *Exécuter avec NCK*.

## 5. Et ensuite ?

- Le [tutoriel en 30 minutes](tutoriel.md) couvre fonctions, listes, classes et erreurs.
- Le [guide du langage](../guide/index.md) détaille chaque notion.
- Le mode interactif `nck` (sans argument) permet d'essayer une ligne à la fois : voir [REPL](../outils/repl.md).
