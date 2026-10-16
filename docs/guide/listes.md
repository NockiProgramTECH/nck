# Listes

Une liste est une suite ordonnée de valeurs **du même type** : `liste<entier>`, `liste<texte>`, `liste<Personne>`…

## Créer et accéder

```nck
variable nombres: liste<entier> = [3, 1, 2]
variable vide: liste<texte> = []            // une liste vide a besoin de son type
variable mixte = [1, 2.5]                   // liste<reel> : l'entier se range dans un reel

ecrire(nombres[0], nombres[-1])             // 3 2
nombres[0] = 10
ecrire(nombres.longueur())                  // 3
ecrire(nombres.tranche(0, 2))               // [10, 1]
```

Un index hors limites lève une erreur d'exécution attrapable.

## Modifier

```nck
variable l = [1, 2]
l.ajouter(3)                // [1, 2, 3]
l.inserer(0, 0)             // [0, 1, 2, 3]
variable dernier = l.retirer()      // retire et retourne 3
variable premier = l.retirer(0)     // retire et retourne 0
ecrire(l, dernier, premier)         // [1, 2] 3 0
```

Les listes sont passées **par référence** : une fonction qui modifie son paramètre modifie la liste d'origine.
Utilisez `l.copier()` pour une copie indépendante.

## Rechercher

```nck
variable fruits = ["pomme", "mangue", "banane"]
ecrire(fruits.contient("mangue"))           // vrai
ecrire(fruits.position("banane"))           // 2   (-1 si absent)
ecrire(fruits.trouver(fonction(f): f.commence_par("m")))   // mangue (ou nul)
ecrire(fruits.tous(fonction(f): f.longueur() > 3))         // vrai
ecrire(fruits.au_moins_un(fonction(f): f == "kiwi"))       // faux
```

## Transformer : `appliquer`, `filtrer`, `reduire`

```nck
variable n = [1, 2, 3, 4, 5]
ecrire(n.appliquer(fonction(x): x * x))             // [1, 4, 9, 16, 25]
ecrire(n.filtrer(fonction(x): x % 2 == 1))          // [1, 3, 5]
ecrire(n.reduire(fonction(acc, x): acc + x, 0))     // 15
ecrire(n.filtrer(fonction(x): x > 2).appliquer(fonction(x): x * 10).somme())   // 120  (chaînage)
n.chaque(fonction(x): ecrire(x))
```

## Trier, inverser, statistiques

```nck
variable l = [3, 1, 2]
ecrire(l.trier(), l.inverser())           // [1, 2, 3] [2, 1, 3]  (nouvelles listes)
ecrire(l.somme(), l.minimum(), l.maximum())   // 6 1 3
ecrire(["b", "a"].trier())                // [a, b]
ecrire(minimum(4, 7), maximum(4, 7, 2))   // 4 7
```

Le tri fonctionne sur les nombres, les textes et les objets dont la classe définit `inferieur`.

## Construire des listes

```nck
ecrire(intervalle(5))             // [0, 1, 2, 3, 4]
ecrire(1..4)                      // [1, 2, 3]
ecrire([0] * 3)                   // [0, 0, 0]
ecrire([1, 2] + [3])              // [1, 2, 3]
ecrire("a-b-c".decouper("-"))     // [a, b, c]
ecrire(["a", "b"].joindre(", "))  // a, b
```

## Listes de listes

```nck
variable grille: liste<liste<entier>> = [[1, 2], [3, 4]]
ecrire(grille[1][0])              // 3
pour ligne dans grille:
    ecrire(ligne.joindre(" "))
fin
```

## Déstructurer

```nck
variable a, b = [1, 2]
variable mini, maxi = [5, 9, 7].trier().tranche(0, 1) + [[5, 9, 7].maximum()]
ecrire(a, b, mini, maxi)
```
