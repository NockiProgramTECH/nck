# Classes et objets

## Définir une classe

Une classe regroupe des **champs typés** (avec valeur par défaut facultative) et des **méthodes**.
Le constructeur est généré automatiquement à partir des champs, comme avec Pydantic.

```nck
classe Personne:
    nom: texte
    age: entier = 0                       // facultatif grâce à la valeur par défaut

    fonction saluer() -> texte:
        retourner "Bonjour, je suis " + soi.nom
    fin

    fonction vieillir(annees: entier):
        soi.age += annees
    fin
fin

variable awa = Personne("Awa", 20)        // arguments dans l'ordre des champs
variable ali = Personne(nom = "Ali")      // ou nommés ; age vaut 0
awa.vieillir(1)
ecrire(awa.nom, awa.saluer())
ecrire(awa)                               // Personne(nom="Awa", age=21)
```

- `soi` désigne l'objet courant (comme `self` / `this`) ; il est implicite dans les méthodes.
- Champ obligatoire manquant, champ inconnu, mauvais type : **erreurs de compilation**.
- Les objets sont passés par référence et comparés par identité (sauf méthode `egal`).

## Validation automatique

Une méthode `valider()` est appelée à chaque création :

```nck
classe Compte:
    titulaire: texte
    solde: entier = 0

    fonction valider():
        verifier(soi.solde >= 0, "le solde ne peut pas être négatif")
    fin
fin

essayer:
    variable c = Compte("Awa", -5)
attraper e:
    ecrire(e.message)             // le solde ne peut pas être négatif
fin
```

## Affichage personnalisé

```nck
classe Point:
    x: reel
    y: reel
    fonction texte() -> texte: retourner f"({soi.x}, {soi.y})"
fin
ecrire(Point(1.0, 2.0))           // (1.0, 2.0)
```

## Héritage

```nck
classe Personne:
    nom: texte
    age: entier = 0
    fonction saluer() -> texte: retourner "Je suis " + soi.nom
fin

classe Etudiant herite Personne:
    ecole: texte = "Université de Ouagadougou"

    fonction saluer() -> texte:            // redéfinition
        retourner parent.saluer() + ", étudiant à " + soi.ecole
    fin
fin

variable issa = Etudiant("Issa", 22, "ISGE")   // champs du parent d'abord
variable groupe: liste<Personne> = [Personne("Awa"), issa]   // un Etudiant est une Personne
pour p dans groupe: ecrire(p.saluer())
ecrire(est_un(issa, Personne), type_de(issa))   // vrai Etudiant
```

- La classe parente doit être déclarée avant ses enfants ; un enfant ne redéclare pas un champ du parent.
- `parent.methode()` appelle la version de la classe parente.
- `est_un(objet, Classe)` teste la classe, héritage compris ; `type_de(objet)` donne le nom exact.

## Méthodes statiques et constantes de classe

```nck
classe Temperature:
    degres: reel
    constante ZERO_ABSOLU = -273.15

    statique fonction depuis_fahrenheit(f: reel) -> Temperature:
        retourner Temperature((f - 32.0) / 1.8)
    fin
fin

variable t = Temperature.depuis_fahrenheit(100.0)
ecrire(t.degres, Temperature.ZERO_ABSOLU)
```

## Membres privés

Un nom qui commence par `_` n'est accessible que depuis les méthodes de la classe :

```nck
classe Compte:
    _solde: entier = 0
    fonction deposer(montant: entier): soi._solde += montant
    fonction solde() -> entier: retourner soi._solde
fin
variable c = Compte()
c.deposer(50)
ecrire(c.solde())     // 50
```

```nck
classe Compte:
    _solde: entier = 0
fin
ecrire(Compte()._solde)    // erreur attendue : '_solde' est privé
```

## Méthodes abstraites

```nck
classe Forme:
    nom: texte
    abstraite fonction aire() -> reel
    fonction decrire() -> texte: retourner f"{soi.nom} : {soi.aire()}"
fin

classe Carre herite Forme:
    cote: reel
    fonction aire() -> reel: retourner soi.cote * soi.cote
fin

ecrire(Carre("petit", 2.0).decrire())   // petit : 4.0
```

Une classe avec une méthode abstraite non implémentée ne peut pas être instanciée.

## Surcharge d'opérateurs

| Opérateur | Méthode à définir |
|---|---|
| `a + b`, `a - b`, `a * b`, `a / b`, `a % b` | `plus`, `moins`, `fois`, `divise`, `modulo` |
| `-a` | `oppose()` |
| `a == b`, `a != b` | `egal(autre) -> booleen` |
| `a < b`, `>`, `<=`, `>=` | `inferieur(autre) -> booleen` |

```nck
classe Vecteur:
    x: reel
    y: reel
    fonction plus(autre: Vecteur) -> Vecteur: retourner Vecteur(soi.x + autre.x, soi.y + autre.y)
    fonction egal(autre: Vecteur) -> booleen: retourner soi.x == autre.x et soi.y == autre.y
    fonction texte() -> texte: retourner f"({soi.x}, {soi.y})"
fin
ecrire(Vecteur(1.0, 2.0) + Vecteur(3.0, 4.0))          // (4.0, 6.0)
ecrire(Vecteur(1.0, 1.0) == Vecteur(1.0, 1.0))          // vrai
```

`trier`, `contient`, `maximum`… fonctionnent sur des objets qui définissent `inferieur` / `egal`.

## Méthodes comme valeurs

```nck
classe Compteur:
    n: entier = 0
    fonction incrementer(): soi.n += 1
fin
variable c = Compteur()
variable f = c.incrementer
f()
f()
ecrire(c.n)      // 2
```

## Classes et JSON

`vers_json(objet)` sérialise les champs ; pour relire, construisez l'objet depuis le dico :

```nck
classe Personne:
    nom: texte
    age: entier
fin
variable json = vers_json(Personne("Awa", 20))
ecrire(json)                                   // {"nom": "Awa", "age": 20}
variable d = depuis_json(json)
variable p = Personne(texte(d["nom"]), entier(d["age"]))
ecrire(p)
```
