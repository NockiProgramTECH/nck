# Dictionnaires

Un dictionnaire associe des **clés** à des **valeurs** : `dico<texte, entier>`, `dico<entier, Personne>`…
Les clés sont des `texte`, `entier`, `booleen` ou valeurs d'énumération ; l'ordre d'insertion est conservé.

## Créer et accéder

```nck
variable ages: dico<texte, entier> = {"Awa": 20, "Ali": 25}
variable vide: dico<texte, liste<entier>> = {}

ages["Issa"] = 22               // ajout
ages["Awa"] += 1                // modification
ecrire(ages["Ali"])             // 25
ecrire(ages.longueur())         // 3
ecrire(ages.contient("Awa"))    // vrai
```

`ages["Zoe"]` sur une clé absente lève une erreur d'exécution. Pour éviter cela :

```nck
variable ages = {"Awa": 20}
ecrire(ages.obtenir("Zoe", 0))          // 0 : valeur par défaut
variable a = ages.obtenir("Zoe")        // entier? : nul si absent
ecrire(a ?? -1)
```

## Parcourir

```nck
variable ages = {"Awa": 20, "Ali": 25}
pour nom dans ages:                 // clés
    ecrire(nom, ages[nom])
fin
pour nom, age dans ages:            // clé + valeur
    ecrire(f"{nom} a {age} ans")
fin
ecrire(ages.cles(), ages.valeurs())  // [Awa, Ali] [20, 25]
```

## Retirer, fusionner, copier

```nck
variable a = {"x": 1, "y": 2}
variable b = {"y": 20, "z": 30}
ecrire(retirer(a, "x"))             // 1
ecrire(a.fusionner(b))              // {y: 20, z: 30}  (b l'emporte)
variable c = a.copier()
c["w"] = 0
ecrire(a.contient("w"))             // faux : copie indépendante
```

## Compter des occurrences

```nck
variable mots = "le chat et le chien et le rat".decouper(" ")
variable compte: dico<texte, entier> = {}
pour m dans mots:
    compte[m] = compte.obtenir(m, 0) + 1
fin
ecrire(compte)      // {le: 3, chat: 1, et: 2, chien: 1, rat: 1}
```

## Dictionnaires et JSON

```nck
variable config = {"nom": "NCK", "version": 12}
variable json = vers_json(config, vrai)
ecrire(json)
variable relu = depuis_json(json)
ecrire(relu["nom"])
```

Voir [Fichiers, JSON et dates](fichiers-json-dates.md).
