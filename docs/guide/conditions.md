# Conditions

## `si` / `sinon si` / `sinon`

```nck
variable note = 14

si note >= 16:
    ecrire("très bien")
sinon si note >= 10:
    ecrire("admis")
sinon:
    ecrire("recalé")
fin
```

- Les parenthèses autour de la condition sont facultatives : `si (note >= 16):` fonctionne aussi.
- La condition doit être un `booleen` : `si note:` est une erreur de type.
- Un bloc d'une seule instruction peut tenir sur une ligne, **sans `fin`** :

```nck
variable a, b = 1, 2
si a == b: ecrire("égaux") sinon: ecrire("différents")
```

## Combiner des conditions

```nck
variable age = 20
variable inscrit = vrai
si age >= 18 et inscrit: ecrire("peut voter")
si age < 18 ou non inscrit: ecrire("ne peut pas voter")
```

## Expression `si … alors … sinon …`

Pour choisir une **valeur** plutôt qu'exécuter un bloc :

```nck
variable age = 20
variable statut = si age >= 18 alors "majeur" sinon "mineur"
ecrire(statut)

variable nom: texte? = nul
ecrire(si nom != nul alors nom.majuscule() sinon "inconnu")
```

Le `sinon` est obligatoire et les deux branches doivent avoir des types compatibles.

## `selon` / `cas`

```nck
variable jour = 6
selon jour:
    cas 1: ecrire("lundi")
    cas 6, 7:                      // plusieurs valeurs
        ecrire("week-end")
    sinon:                         // facultatif, en dernier
        ecrire("autre jour")
fin
```

- Les valeurs sont comparées avec `==` (nombres, textes, booléens, énumérations).
- Le premier `cas` qui correspond est exécuté, sans « passage » au suivant.
- Avec une [énumération](enumerations.md), un `selon` sans `sinon` doit couvrir **toutes** les valeurs.

```nck
fonction categorie(code: texte) -> texte:
    selon code:
        cas "A": retourner "excellent"
        cas "B", "C": retourner "bien"
        sinon: retourner "à revoir"
    fin
fin
ecrire(categorie("B"))
```
