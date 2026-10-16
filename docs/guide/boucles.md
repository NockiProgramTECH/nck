# Boucles

## `pour … dans`

```nck
variable fruits = ["pomme", "mangue", "banane"]

pour fruit dans fruits:             // éléments d'une liste
    ecrire(fruit)
fin

pour i, fruit dans fruits:          // indice + élément
    ecrire(i, fruit)
fin

pour lettre dans "nck":             // caractères d'un texte
    ecrire(lettre)
fin

variable ages = {"Awa": 20, "Ali": 25}
pour nom dans ages:                 // clés d'un dictionnaire
    ecrire(nom)
fin
pour nom, age dans ages:            // clé + valeur
    ecrire(nom, age)
fin
```

## Compter

```nck
pour i dans 5: ecrire(i)                    // 0 1 2 3 4
pour i dans 1..6: ecrire(i)                 // 1 2 3 4 5  (borne droite exclue)
pour i dans intervalle(10, 0, -2): ecrire(i) // 10 8 6 4 2
```

## `tantque`

```nck
variable i = 0
tantque i < 3:
    ecrire(i)
    i += 1
fin
```

## `arreter` et `continuer`

```nck
pour n dans 1..100:
    si n % 2 == 0: continuer       // passe au suivant
    si n > 7: arreter              // sort de la boucle
    ecrire(n)                      // 1 3 5 7
fin
```

## Boucle infinie contrôlée

```nck
variable essais = 0
tantque vrai:
    essais += 1
    si essais == 3: arreter
fin
ecrire(essais)
```

## Variables de boucle et fermetures

Chaque itération possède **sa propre** variable : une fonction anonyme créée dans la boucle garde la valeur du tour.

```nck
variable actions: liste<fonction<entier>> = []
pour i dans 3:
    actions.ajouter(fonction(): i)
fin
ecrire(actions.appliquer(fonction(f): f()))   // [0, 1, 2]
```

## Alternatives sans boucle

Pour transformer ou filtrer une liste, préférez `appliquer`, `filtrer`, `reduire` (voir [Listes](listes.md)) :

```nck
variable carres = (1..6).appliquer(fonction(x): x * x)
ecrire(carres)                                // [1, 4, 9, 16, 25]
```
