# Textes

## Écrire un texte

```nck
variable a = "Bonjour"
variable b = 'avec des apostrophes'
variable c = "Elle a dit \"salut\"\n"       // échappements
ecrire(a, b, c)
```

Échappements reconnus : `\n` `\t` `\r` `\\` `\"` `\'` `\0` `\{` `\}` `\uXXXX`. Un échappement inconnu (`\q`) est une erreur.

## Textes formatés `f"…"`

```nck
variable nom = "Awa"
variable notes = [12, 15]
ecrire(f"{nom} a {notes.longueur()} notes, moyenne {notes.somme() / notes.longueur()}")
ecrire(f"accolades littérales : \{pas une expression\}")
```

Toute expression est permise entre `{ }`.

## Textes multi-lignes `"""…"""`

```nck
variable aide = """
    Usage : nck fichier.nck
      -v  affiche la version
    """
ecrire(aide)
```

Le retour à la ligne qui suit `"""` est ignoré et l'indentation commune est retirée.

## Opérations courantes

```nck
variable t = "  Bonjour le Monde  "
ecrire(t.nettoyer())                    // Bonjour le Monde
ecrire(t.majuscule(), t.minuscule())
ecrire(t.longueur())                    // 20
ecrire(t.contient("Monde"))             // vrai
ecrire(t.nettoyer().decouper(" "))      // [Bonjour, le, Monde]
ecrire(["a", "b", "c"].joindre("-"))    // a-b-c
ecrire(t.remplacer("Monde", "NCK"))
ecrire("abc".position("c"))             // 2
ecrire("nck".commence_par("n"), "nck".termine_par("k"))
ecrire("7".remplir_gauche(3, "0"))      // 007
ecrire(caractere(65), code("A"))        // A 65
ecrire(formater("{} a {} ans", "Awa", 20))
```

Toutes ces fonctions existent aussi en forme classique : `majuscule(t)`, `decouper(t, " ")`…
Liste complète dans la [référence des natifs](../NATIFS.md#textes).

## Parcourir les caractères

```nck
pour c dans "nck":
    ecrire(c)
fin
pour i, c dans "ab":
    ecrire(i, c)
fin
ecrire("bonjour"[0], "bonjour"[-1])     // b r
```

## Convertir

```nck
ecrire(texte(42) + "!", entier("42") + 1, reel("3,5"))
ecrire(est_nombre("3.5"), est_entier("3.5"))    // vrai faux
```
