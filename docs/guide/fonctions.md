# Fonctions

## Définir et appeler

```nck
fonction additionner(a: entier, b: entier) -> entier:
    retourner a + b
fin

fonction saluer(nom: texte):              // pas de `->` : retourne `rien`
    ecrire("Salut", nom)
fin

fonction carre(x: reel) -> reel: retourner x * x    // forme courte, sans `fin`

ecrire(additionner(2, 3), carre(1.5))
saluer("Awa")
```

Règles :

- chaque paramètre est typé ;
- une fonction `-> T` doit retourner une valeur dans **tous** les chemins (le vérificateur le contrôle) ;
- une fonction peut être appelée avant sa définition dans le même fichier.

```nck
fonction signe(n: entier) -> texte:   // erreur attendue : chemin sans retourner
    si n > 0: retourner "positif"
    si n < 0: retourner "négatif"
fin
```

## Paramètres par défaut

```nck
fonction saluer(nom: texte, salut: texte = "Bonjour") -> texte:
    retourner f"{salut} {nom}"
fin
ecrire(saluer("Awa"))              // Bonjour Awa
ecrire(saluer("Awa", "Salut"))     // Salut Awa
```

Les paramètres avec valeur par défaut viennent en dernier. (Les arguments nommés `nom = valeur` sont réservés à la création d'objets.)

## Nombre variable d'arguments `...args`

```nck
fonction somme(...nombres: liste<entier>) -> entier:
    variable total = 0
    pour n dans nombres: total += n
    retourner total
fin
ecrire(somme(1, 2, 3))          // 6
variable l = [4, 5]
ecrire(somme(0, ...l))          // 9   étalement d'une liste
```

## Les fonctions sont des valeurs

```nck
fonction double(n: entier) -> entier: retourner n * 2
fonction appliquer_deux_fois(f: fonction<entier, entier>, x: entier) -> entier:
    retourner f(f(x))
fin
ecrire(appliquer_deux_fois(double, 5))   // 20

variable op = double          // stockée dans une variable
ecrire(op(21))
```

Le type `fonction<P1, P2, …, R>` liste les paramètres puis le retour ; `fonction<rien>` est une fonction sans paramètre ni retour.

## Fonctions anonymes

`fonction(paramètres) -> retour: corps` crée une fonction sans nom. Trois formes :

```nck
variable double = fonction(x: entier) -> entier: retourner x * 2    // instruction courte
variable triple = fonction(x: entier): x * 3                        // expression : retour implicite
variable somme = fonction(a: entier, b: entier):                    // bloc
    variable r = a + b
    retourner r
fin
ecrire(double(2), triple(2), somme(1, 2))
```

Quand le contexte connaît le type attendu, les types des paramètres se **déduisent** :

```nck
variable nombres = [1, 2, 3, 4, 5, 6]
ecrire(nombres.appliquer(fonction(x): x * 2))          // [2, 4, 6, 8, 10, 12]
ecrire(nombres.filtrer(fonction(x): x % 2 == 0))       // [2, 4, 6]
ecrire(nombres.reduire(fonction(acc, x): acc + x, 0))  // 21
ecrire(nombres.trouver(fonction(x): x > 4))            // 5
nombres.chaque(fonction(x): ecrire(x))

fonction au_clic(action: fonction<rien>): action()
au_clic(fonction(): ecrire("cliqué !"))
```

## Fermetures

Une fonction capture les variables de l'endroit où elle est créée :

```nck
fonction compteur() -> fonction<entier>:
    variable n = 0
    retourner fonction():
        n += 1
        retourner n
    fin
fin
variable suivant = compteur()
ecrire(suivant(), suivant(), suivant())   // 1 2 3
```

## Récursivité

```nck
fonction factorielle(n: entier) -> entier:
    si n <= 1: retourner 1
    retourner n * factorielle(n - 1)
fin
ecrire(factorielle(20))
```

La profondeur de récursion est limitée (2000 appels) ; au-delà, une erreur attrapable est levée.

## Décorateurs

Un décorateur reçoit une fonction et en retourne une autre ; `@deco` l'applique à la définition.

```nck
fonction journaliser(f: fonction<liste<quelconque>, quelconque>) -> fonction<liste<quelconque>, quelconque>:
    fonction enveloppe(...args) -> quelconque:
        ecrire("appel avec", args)
        retourner f(...args)
    fin
    retourner enveloppe
fin

@journaliser
fonction addition(a: entier, b: entier) -> entier:
    retourner a + b
fin

ecrire(addition(2, 3))    // appel avec [2, 3]   puis   5
```
