# Référence du langage NCK

NCK est un langage **simple**, **typé statiquement** (comme TypeScript) et dont les mots-clés sont
en **français**. Les fichiers portent l'extension `.nck`.

```
nck programme.nck            # exécute
nck verifier programme.nck   # vérifie syntaxe + types sans exécuter
nck                          # mode interactif (REPL)
```

---

## 1. Commentaires

```
// commentaire sur une ligne
# aussi un commentaire
/* commentaire
   sur plusieurs lignes */
```

## 2. Variables et constantes

```
variable age: entier = 25        // type explicite
variable nom = "Awa"             // type déduit : texte
variable total: reel             // déclarée sans valeur (doit être affectée avant usage)
constante PI = 3.14159           // ne peut plus être modifiée

age = 26
age += 1                         // aussi : -=  *=  /=
```

Règles :
- une variable a **toujours** un type, écrit ou déduit ;
- on ne peut pas changer le type d'une variable (`age = "vingt"` → erreur de type) ;
- une variable ne peut pas être redéclarée dans la même fonction.

Les instructions se terminent par une fin de ligne ou un `;` (plusieurs instructions sur une ligne).

## 3. Types

| Type               | Exemple                          | Description                              |
|--------------------|----------------------------------|------------------------------------------|
| `entier`           | `42`, `-7`, `1_000_000`          | nombre entier (taille illimitée)         |
| `reel`             | `3.14`, `2e10`                   | nombre à virgule                         |
| `texte`            | `"bonjour"`, `'ok'`              | chaîne de caractères (UTF-8)             |
| `booleen`          | `vrai`, `faux`                   | valeur logique                           |
| `liste<T>`         | `[1, 2, 3]`, `liste<texte>`      | liste d'éléments de type `T`             |
| `fonction<A, B, R>`| `fonction<entier, entier, entier>` | fonction prenant `A, B` et renvoyant `R` |
| `NomDeClasse`      | `Personne`                       | instance d'une classe (voir §9)          |
| `quelconque`       | —                                | n'importe quelle valeur (vérifiée à l'exécution) |
| `rien`             | —                                | type de retour d'une fonction sans valeur |
| `nul`              | `nul`                            | absence de valeur                        |

Conversions implicites : un `entier` peut être utilisé partout où un `reel` est attendu. Rien d'autre
n'est implicite : utilisez `texte(x)`, `entier(x)`, `reel(x)`, `booleen(x)`.

Échappements dans les textes : `\n`, `\t`, `\\`, `\"`, `\'`.

## 4. Opérateurs

| Catégorie     | Opérateurs                               | Notes                                            |
|---------------|------------------------------------------|--------------------------------------------------|
| arithmétique  | `+  -  *  /  %`                          | `/` donne toujours un `reel` ; `division_entiere(a, b)` pour un entier |
| comparaison   | `==  !=  <  >  <=  >=`                   | `<` etc. sur nombres ou textes                   |
| logique       | `et  ou  non`                            | évaluation paresseuse                            |
| texte / liste | `+` (concaténation), `*` entier (répétition), `x[i]` (index, négatif accepté) |

Priorité (du plus faible au plus fort) : `ou` < `et` < `non` < comparaisons < `+ -` < `* / %` < `-` unaire < appel / index.

## 5. Blocs

Un bloc commence par `:`. Deux formes :

```
// forme courte : une seule instruction sur la même ligne
si (x > 0): ecrire("positif")

// forme longue : plusieurs lignes, terminée par `fin`
si (x > 0):
    ecrire("positif")
    x -= 1
fin
```

Les parenthèses autour des conditions sont facultatives.

## 6. Conditions

```
si (note >= 16):
    ecrire("très bien")
sinon si (note >= 10):
    ecrire("admis")
sinon:
    ecrire("recalé")
fin

si (a == b): ecrire("égaux") sinon: ecrire("différents")
```

La condition doit être un `booleen` (pas `si (3)`).

## 7. Boucles

```
tantque (i < 10):
    i += 1
fin

pour i dans intervalle(5):        // 0 1 2 3 4
pour i dans intervalle(1, 6):     // 1 2 3 4 5
pour i dans intervalle(10, 0, -2) // 10 8 6 4 2
pour i dans 5:                    // raccourci de intervalle(5)
pour fruit dans fruits:           // éléments d'une liste
pour lettre dans "nck":           // caractères d'un texte
```

`arreter` sort de la boucle, `continuer` passe à l'itération suivante.

## 8. Fonctions

```
fonction additionner(a: entier, b: entier) -> entier:
    retourner a + b
fin

fonction saluer(nom: texte):      // pas de `->` : retourne `rien`
    ecrire("Salut", nom)
fin

fonction carre(x: reel) -> reel: retourner x * x    // forme courte
```

- les paramètres doivent être typés ;
- une fonction avec `-> T` doit retourner une valeur dans **tous** les chemins ;
- une fonction peut être appelée avant sa définition dans le même bloc ;
- les fonctions sont des valeurs : on peut les passer en argument ou les retourner (fermetures).

```
fonction appliquer(f: fonction<entier, entier>, x: entier) -> entier: retourner f(x)
fonction double(n: entier) -> entier: retourner n * 2
ecrire(appliquer(double, 21))   // 42
```

## 9. Classes (programmation orientée objet)

Une classe regroupe des **champs typés** (avec valeur par défaut facultative) et des **méthodes**.
Le constructeur est généré automatiquement à partir des champs, comme avec Pydantic.

```
classe Personne:
    nom: texte
    age: entier = 0                       // champ facultatif grâce à la valeur par défaut

    fonction saluer() -> texte:
        retourner "Bonjour, je suis " + soi.nom
    fin

    fonction vieillir(annees: entier):
        soi.age += annees
    fin

    fonction valider():                   // facultatif : appelée automatiquement à la création
        verifier(soi.age >= 0, "l'âge ne peut pas être négatif")
    fin
fin

variable awa = Personne("Awa", 20)        // arguments dans l'ordre des champs
variable ali = Personne(nom = "Ali")      // ou nommés ; age vaut 0
awa.vieillir(1)
ecrire(awa.nom, awa.saluer())
ecrire(awa)                               // Personne(nom="Awa", age=21)
```

- Dans une méthode, `soi` désigne l'objet courant (comme `self` / `this`).
- Les champs obligatoires manquants, les champs inconnus et les mauvais types sont des **erreurs de compilation**.
- À la création, chaque champ est aussi vérifié à l'exécution (utile quand une valeur vient de `quelconque` ou de `lire`), puis `valider()` est appelée si elle existe.
- Une méthode `texte() -> texte` personnalise l'affichage par `ecrire` / `texte(obj)`.
- Les objets sont comparés par identité (`==` est vrai seulement pour le même objet) et passés par référence.
- Une méthode peut être stockée dans une variable : `variable f = awa.saluer ; f()`.

### Héritage

```
classe Etudiant herite Personne:
    ecole: texte = "Université de Ouagadougou"

    fonction saluer() -> texte:            // redéfinition (la signature doit rester compatible)
        retourner soi.nom + ", étudiant à " + soi.ecole
    fin
fin

variable issa = Etudiant("Issa", 22, "ISGE")   // champs du parent d'abord, puis les siens
variable groupe: liste<Personne> = [awa, issa] // un Etudiant est une Personne
```

La classe parente doit être déclarée avant ses enfants. Un enfant ne peut pas redéclarer un champ du parent.

## 10. Fonctions natives

**Entrées / sorties**
- `ecrire(...)` — affiche les valeurs séparées par un espace
- `lire(invite?)` → `texte` — lit une ligne au clavier

**Conversions / types**
- `texte(x)`, `entier(x)`, `reel(x)`, `booleen(x)`, `type_de(x)`

**Listes** (`liste<T>`)
- `longueur(l)`, `ajouter(l, x)`, `inserer(l, i, x)`, `retirer(l, i?)` → `T`
- `contient(l, x)`, `position(l, x)` (−1 si absent), `tranche(l, debut, fin?)`
- `trier(l)`, `inverser(l)`, `copier(l)`, `somme(l)`, `minimum(l)`, `maximum(l)`
- `intervalle(fin)`, `intervalle(debut, fin, pas?)` → `liste<entier>`

**Textes**
- `longueur(t)`, `majuscule(t)`, `minuscule(t)`, `nettoyer(t)`, `remplacer(t, ancien, nouveau)`
- `decouper(t, sep?)` → `liste<texte>`, `joindre(l, sep?)` → `texte`
- `contient(t, s)`, `position(t, s)`, `commence_par(t, s)`, `termine_par(t, s)`, `tranche(t, debut, fin?)`
- `caractere(code)`, `code(caractere)`

**Mathématiques**
- `absolu`, `racine`, `puissance(a, b)`, `arrondir(x, decimales?)`, `plancher`, `plafond`
- `division_entiere(a, b)`, `minimum(a, b, ...)`, `maximum(a, b, ...)`
- `aleatoire()` → reel dans [0, 1[, `aleatoire(max)`, `aleatoire(min, max)` → entier

**Divers**
- `horloge()` → secondes (chronométrage), `attendre(secondes)`, `quitter(code?)`
- `verifier(condition, message?)` — stoppe le programme si la condition est fausse

## 11. Erreurs

Trois familles, toutes avec ligne et colonne :

```
Erreur de syntaxe : 'fin' attendu pour fermer le bloc commencé ligne 2
Erreur de type : 'age' est de type entier, mais reçoit un texte
  --> programme.nck:3:7
   |
  3| age = "vingt"
   |       ^
Erreur d'exécution : division par zéro
```

Les erreurs de syntaxe et de type sont détectées **avant** d'exécuter la moindre ligne.

## 12. Mots réservés

`variable constante fonction classe herite retourner si sinon tantque pour dans fin arreter continuer et ou non vrai faux nul`

`soi` est défini automatiquement dans les méthodes.
