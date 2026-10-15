# NCK

**NCK** est un langage de programmation simple, rapide à prendre en main, **typé statiquement**
(dans l'esprit de TypeScript / Pydantic) et dont les mots-clés sont en **français**.
Les programmes sont des fichiers `.nck`.

```
// bonjour.nck
variable nombre = 20

si (nombre > 20): ecrire("ton nombre est grand")
sinon: ecrire("ton nombre est petit ou égal à 20")

fonction additionner(a: entier, b: entier) -> entier:
    retourner a + b
fin

ecrire("2 + 3 =", additionner(2, 3))
```

```
$ nck bonjour.nck
ton nombre est petit ou égal à 20
2 + 3 = 5
```

## Pourquoi NCK ?

- **Simple** : une poignée de mots-clés, des blocs ouverts par `:` et fermés par `fin`, pas de point-virgule obligatoire.
- **Typé** : chaque variable a un type (écrit ou déduit). Les erreurs de type sont signalées **avant** l'exécution, avec la ligne, la colonne et une suggestion.
- **Lisible** : `si`, `sinon`, `tantque`, `pour ... dans`, `fonction`, `retourner`, `vrai`, `faux`, `et`, `ou`, `non`.
- **Rapide** : l'interpréteur compile le programme en fermetures Python plutôt que de parcourir l'arbre à chaque instruction.

## Installation

Python 3.10 ou plus récent est nécessaire.

```bash
git clone https://github.com/NockiProgramTECH/nck.git
cd nck
pip install -e .          # installe la commande `nck`
```

Sans installation : `python -m nck programme.nck`.

## Utilisation

```bash
nck programme.nck            # exécute un fichier
nck programme.nck a b        # ... avec des arguments (lus par arguments())
nck verifier programme.nck   # vérifie la syntaxe et les types, sans exécuter
nck                          # mode interactif
```

## Aperçu du langage

```
// Types : entier, reel, texte, booleen, liste<T>, dico<K, V>, fonction<...>, quelconque
variable age: entier = 25
variable prix = 19.99                       // reel déduit
variable fruits: liste<texte> = ["mangue", "banane"]
variable ages: dico<texte, entier> = {"Awa": 20}
constante PI = 3.14159

ajouter(fruits, "papaye")
ages["Ali"] = 25
pour fruit dans fruits:
    ecrire("-", majuscule(fruit))
fin

variable i = 0
tantque (i < 10):
    i += 1
    si (i % 2 == 0): continuer
    si (i > 7): arreter
    ecrire(i)
fin

fonction factorielle(n: entier) -> entier:
    si (n <= 1): retourner 1
    retourner n * factorielle(n - 1)
fin
ecrire(f"5! = {factorielle(5)}")
```

Et des classes typées, à la Pydantic :

```
classe Personne:
    nom: texte
    age: entier = 0

    fonction saluer() -> texte:
        retourner "Bonjour, je suis " + soi.nom
    fin
fin

variable awa = Personne("Awa", 20)
ecrire(awa.saluer(), awa)        // Bonjour, je suis Awa Personne(nom="Awa", age=20)
Personne()                        // Erreur de type : il manque le(s) champ(s) obligatoire(s) 'nom'
```

Et quand on se trompe :

```
age = "vingt-cinq"
```
```
Erreur de type : impossible d'affecter un texte à une cible de type entier
  --> programme.nck:2:7
   |
  2| age = "vingt-cinq"
   |       ^
```

La référence complète (types, opérateurs, fonctions natives…) est dans [`docs/LANGAGE.md`](docs/LANGAGE.md).
D'autres programmes se trouvent dans [`exemples/`](exemples/).

## Coloration syntaxique (VS Code)

Une extension minimale se trouve dans [`editeurs/vscode/`](editeurs/vscode/). Pour l'installer :

```bash
# Linux / macOS
cp -r editeurs/vscode ~/.vscode/extensions/nck-lang
# Windows (PowerShell)
Copy-Item -Recurse editeurs\vscode "$env:USERPROFILE\.vscode\extensions\nck-lang"
```

puis redémarrez VS Code : les fichiers `.nck` sont colorés, et les commentaires / blocs / parenthèses sont gérés.

## Structure du projet

```
nck/
├── lexeur.py         # texte source → jetons
├── parseur.py        # jetons → arbre syntaxique (AST)
├── arbre.py          # définition des nœuds de l'AST
├── types_nck.py      # système de types (compatibilité, inférence)
├── verificateur.py   # vérification statique des types
├── interpreteur.py   # compilation de l'AST en fermetures + exécution
├── natifs.py         # fonctions intégrées (ecrire, longueur, ...)
├── modules.py        # chargement des modules importés
├── erreurs.py        # erreurs avec position
└── cli.py            # commande `nck`
exemples/             # programmes .nck
tests/                # tests (pytest)
docs/LANGAGE.md       # référence du langage
```

## Développement

```bash
pip install -e ".[dev]"
pytest
```

## Feuille de route

- [x] v0.1 — moteur Python : lexeur, parseur, vérificateur de types, interpréteur, REPL
- [x] v0.2 — classes typées avec validation (`classe`, `herite`, `soi`, `valider`)
- [x] v0.3 — gestion des erreurs (`essayer` / `attraper` / `enfin` / `lever`), extension VS Code
- [x] v0.4 — dictionnaires `dico<K, V>`
- [x] v0.5 — modules (`importer "fichier.nck"`, `comme`, `depuis … importer`)
- [x] v0.6 — bibliothèque standard : fichiers, JSON, date/heure, arguments, formatage
- [x] v0.7 — textes formatés `f"..."`, paramètres par défaut, `selon`/`cas`, `pour i, x dans`
- [ ] réécriture du moteur en C
