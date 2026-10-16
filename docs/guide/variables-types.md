# Variables, constantes et types

## Déclarer une variable

```nck
variable age: entier = 25        // type explicite
variable nom = "Awa"             // type déduit : texte
variable total: reel             // déclarée sans valeur : à affecter avant usage
constante PI = 3.14159           // constante : ne peut plus changer

age = 26
age += 1                         // aussi -=  *=  /=
total = age * 1.5
ecrire(nom, age, total, PI)
```

Règles :

- une variable a **toujours** un type, écrit ou déduit à partir de la première valeur ;
- ce type ne change jamais : `age = "vingt"` est une erreur de type, détectée avant l'exécution ;
- une variable ne peut pas être redéclarée dans le même bloc ;
- une instruction se termine par la fin de ligne, ou par `;` pour en mettre plusieurs sur une ligne.

```nck
variable x = 1
x = "un"      // erreur attendue : 'x' est de type entier, mais reçoit un texte
```

## Les types de base

| Type | Exemples | Remarques |
|---|---|---|
| `entier` | `0`, `-7`, `1000000` | précision illimitée |
| `reel` | `3.14`, `-0.5`, `2.0` | nombres à virgule |
| `texte` | `"Bonjour"`, `'a'`, `f"{x}"` | chaînes de caractères Unicode |
| `booleen` | `vrai`, `faux` | seuls booléens possibles |
| `rien` | — | « pas de valeur » (retour d'une fonction sans `->`) |
| `quelconque` | n'importe quoi | pour les données dynamiques (JSON) |

Types composés : `liste<T>`, `dico<K, V>`, `fonction<P1, P2, R>`, `T?` (optionnel), noms de classes et d'énumérations.

```nck
variable notes: liste<reel> = [12.5, 15, 9]        // un entier se range dans un reel
variable ages: dico<texte, entier> = {"Awa": 20}
variable surnom: texte? = nul                      // peut être nul
variable double: fonction<entier, entier> = fonction(x: entier): x * 2
```

## Conversions entre types

Aucune conversion n'est implicite, sauf `entier` → `reel`. Pour le reste, on appelle une fonction :

```nck
ecrire(entier("42") + 1)        // 43
ecrire(reel("2,5") * 2)         // 5.0   (la virgule française est acceptée)
ecrire(texte(3.5) + " m")       // 3.5 m
ecrire(entier(3.9))             // 3   (troncature)
ecrire(booleen("oui"))          // vrai
ecrire(arrondir(2.567, 2))      // 2.57
ecrire(type_de([1, 2]))         // liste
```

`entier("abc")` lève une erreur **attrapable** (voir [Gestion des erreurs](erreurs.md)).
Pour tester avant : `est_nombre("3.5")`, `est_entier("42")`.

## Déclaration et affectation multiples

```nck
variable a, b = 1, "deux"        // chaque variable prend le type de sa valeur
a, b = 2, "trois"
variable x, y = 10, 20
x, y = y, x                      // échange en une ligne

variable mini, maxi = [4, 9]     // déstructuration d'une liste

fonction bornes(l: liste<entier>) -> liste<entier>:
    retourner l.minimum(), l.maximum()      // `retourner a, b` renvoie la liste [a, b]
fin
variable bas, haut = bornes([3, 7, 5])
ecrire(bas, haut)                // 3 7
```

## Portée

Une variable existe dans le bloc où elle est déclarée (fonction, boucle, `si`…) et dans les blocs qu'il contient.

```nck
variable compteur = 0

fonction incrementer():
    compteur += 1            // la variable globale est visible et modifiable
fin

pour i dans 3:
    variable carre = i * i   // `carre` n'existe que dans la boucle
    incrementer()
fin
ecrire(compteur)             // 3
```

## `quelconque` : les données dynamiques

`quelconque` accepte n'importe quelle valeur ; c'est le type retourné par `depuis_json`. On peut l'indexer et le convertir,
mais pas l'utiliser aveuglément : `si` et `tantque` exigent un vrai booléen à l'exécution.

```nck
variable donnees: quelconque = depuis_json("{\"nom\": \"Awa\", \"age\": 20}")
variable nom: texte = texte(donnees["nom"])
variable age: entier = entier(donnees["age"])
ecrire(nom, age)
```
