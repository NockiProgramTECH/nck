# Types optionnels et `nul`

## Le principe

Une variable d'un type précis ne vaut **jamais** `nul` :

```nck
variable n: texte = nul     // erreur attendue : texte ne peut pas être nul
```

Pour autoriser l'absence de valeur, on ajoute `?` au type : `texte?`, `entier?`, `Personne?`, `liste<entier>?`.

```nck
variable prenom: texte? = nul
prenom = "Awa"              // un texte se range dans un texte?
```

## Utiliser un optionnel : l'affinement

Le vérificateur interdit d'utiliser un `T?` comme un `T` tant qu'il n'a pas été testé :

```nck
variable prenom: texte? = nul
ecrire(prenom.longueur())        // erreur attendue : la valeur peut être nul
```

```nck
variable prenom: texte? = "Awa"

si prenom != nul:
    ecrire(prenom.longueur())    // ok : ici prenom est un texte
fin

fonction saluer(nom: texte?) -> texte:
    si nom == nul: retourner "Bonjour !"
    retourner "Bonjour " + nom   // ok : le cas nul est sorti juste au-dessus
fin
ecrire(saluer(prenom), saluer(nul))
```

Le type est affiné après `si x != nul`, dans le `sinon` de `si x == nul`, après `si x == nul: retourner`,
à droite de `x != nul et …`, et dans `tantque x != nul`. Une réaffectation (`x = nul`) annule l'affinement,
et il n'est pas visible à l'intérieur d'une fonction anonyme.

## Valeur de repli `??`

```nck
variable surnom: texte? = nul
ecrire(surnom ?? "inconnu")                  // inconnu

variable d = {"a": 1}
variable v: entier = d.obtenir("b") ?? 0     // obtenir sans défaut retourne un entier?
ecrire(v)
```

## Fonctions qui retournent des optionnels

| Fonction | Retour |
|---|---|
| `dico.obtenir(cle)` sans défaut | `V?` |
| `liste.trouver(f)` | `T?` |
| `si c alors x sinon nul` | `T?` |

```nck
variable nombres = [1, 5, 9]
variable grand = nombres.trouver(fonction(x): x > 4)
si grand != nul: ecrire("trouvé", grand)
```

## Optionnels dans les classes

```nck
classe Personne:
    nom: texte
    email: texte? = nul

    fonction contact() -> texte:
        retourner soi.email ?? "pas d'email"
    fin
fin
ecrire(Personne("Awa").contact())
ecrire(Personne("Ali", "ali@exemple.bf").contact())
```
