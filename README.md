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

📚 **Documentation complète : [nockiprogramtech.github.io/nck](https://nockiprogramtech.github.io/nck/)** — tutoriel, guide du langage, référence, outils, exemples.

## Installation

**Sans rien d'autre à installer** (ni Python, ni dépendances) — voir [`docs/INSTALLATION.md`](docs/INSTALLATION.md) :

| Système | Méthode |
|---|---|
| Windows | Téléchargez **`NCK-Setup-<version>.exe`** dans les [Releases](https://github.com/NockiProgramTECH/nck/releases) et suivez l'assistant (PATH, fichiers `.nck`, extension VS Code) |
| Windows (terminal) | `irm https://raw.githubusercontent.com/NockiProgramTECH/nck/main/installateur/installer.ps1 \| iex` |
| Linux | `curl -fsSL https://raw.githubusercontent.com/NockiProgramTECH/nck/main/installateur/installer.sh \| sh` |

Puis, dans un nouveau terminal : `nck info`.

**Releases officielles : Linux x64/arm64 et Windows x64.** Le support des exécutables
macOS est reporté ; l'installation depuis les sources avec Python reste possible,
mais n'est pas validée sur macOS par la CI actuelle.

Pour les développeurs (Python 3.10+) : `git clone … && cd nck && pip install -e .`

## Utilisation

```bash
nck programme.nck            # exécute un fichier
nck programme.nck a b        # ... avec des arguments (lus par arguments())
nck verifier programme.nck   # vérifie la syntaxe et les types, sans exécuter
nck                          # mode interactif
```

## Paquets (v0.13)

```bash
nck init --nom mon-projet
nck installer maths-plus --index /chemin/vers/index.json
nck paquets
```

Les bibliothèques s'importent avec `importer "maths-plus" comme maths`. Le gestionnaire
résout les dépendances, vérifie le SHA-256 des archives et écrit `paquet.verrou.json`.
Le registre public reste à mettre en service : utilisez pour l'instant un index
personnalisé. Voir le [guide des paquets](docs/PAQUETS.md), avec un exemple local complet.

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

La référence complète du langage est dans [`docs/LANGAGE.md`](docs/LANGAGE.md), celle des fonctions natives dans
[`docs/NATIFS.md`](docs/NATIFS.md).
D'autres programmes se trouvent dans [`exemples/`](exemples/).

## VS Code : coloration, autocomplétion, survol, erreurs en direct

L'extension [`editeurs/vscode/`](editeurs/vscode/) offre l'expérience « Pylance » pour NCK : coloration,
erreurs de syntaxe et de type soulignées en tapant, autocomplétion (variables, fonctions, `objet.`, `module.`),
infos au survol, aide à la signature, aller à la définition, exécution par `F5`.

L'installateur (`NCK-Setup.exe`, `installer.sh`, `installer.ps1`) propose de l'installer pour vous. À la main :

```bash
cp -r editeurs/vscode ~/.vscode/extensions/nck-lang           # Linux/macOS
Copy-Item -Recurse editeurs\vscode "$env:USERPROFILE\.vscode\extensions\nck-lang"   # Windows
```

puis redémarrez VS Code. L'extension utilise l'exécutable `nck` du PATH (ou `python -m nck` à défaut). Guide complet : [`docs/EDITEUR.md`](docs/EDITEUR.md).

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
editeurs/vscode/      # extension VS Code
docs/                 # LANGAGE.md, NATIFS.md, EDITEUR.md
```

## Développement

```bash
pip install -e ".[dev]"
pytest
```

Historique détaillé : [CHANGELOG.md](CHANGELOG.md). Licence MIT.

## Feuille de route

- [x] v0.1 — moteur Python : lexeur, parseur, vérificateur de types, interpréteur, REPL
- [x] v0.2 — classes typées avec validation (`classe`, `herite`, `soi`, `valider`)
- [x] v0.3 — gestion des erreurs (`essayer` / `attraper` / `enfin` / `lever`), extension VS Code
- [x] v0.4 — dictionnaires `dico<K, V>`
- [x] v0.5 — modules (`importer "fichier.nck"`, `comme`, `depuis … importer`)
- [x] v0.6 — bibliothèque standard : fichiers, JSON, date/heure, arguments, formatage
- [x] v0.7 — textes formatés `f"..."`, paramètres par défaut, `selon`/`cas`, `pour i, x dans`
- [x] v0.8 — serveur d'analyse pour VS Code : autocomplétion, survol, signature, définition, erreurs en direct
- [x] v0.9 — POO complète (`parent`, `statique`, `constante` de classe, privé `_x`, `abstraite`, `est_un`, surcharge d'opérateurs), décorateurs `@deco`, `...args`
- [x] v0.10 — fonctions anonymes `fonction(x): x * 2`, `appliquer`/`filtrer`/`reduire`…, types optionnels `texte?` + `??`, plages `a..b`
- [x] v0.11 — notation méthode `liste.ajouter(x)`, énumérations, `si … alors … sinon` en expression, affectation multiple, textes `"""…"""`
- [x] v0.12 — installateur sans Python : `NCK-Setup.exe` (Windows), `installer.sh` (Linux/macOS), releases automatiques, `nck info`
- [ ] v0.13 — paquets `nck installer` · v0.14 — interface graphique · v0.15 — tests/formateur/doc · v0.16 — génériques, tuples, unions · … · v1.0
- [ ] réécriture du moteur en C (reportée)

Détail complet de ce qui reste : [`docs/ROADMAP.md`](docs/ROADMAP.md).
