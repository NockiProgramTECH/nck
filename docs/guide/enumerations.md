# Énumérations

Une énumération est un ensemble **fermé** de valeurs nommées. Plus sûr qu'un texte ou un entier :
le vérificateur connaît toutes les valeurs possibles.

## Déclarer

```nck
enumeration Couleur: ROUGE, VERT, BLEU fin

enumeration Etat:          // ou sur plusieurs lignes
    OUVERT
    FERME
fin

variable c = Couleur.VERT
ecrire(c)                  // Couleur.VERT
ecrire(c.nom, c.indice)    // VERT 1
ecrire(Couleur.valeurs)    // [Couleur.ROUGE, Couleur.VERT, Couleur.BLEU]
ecrire(c == Couleur.VERT, Couleur.ROUGE < Couleur.BLEU)    // vrai vrai
```

## `selon` exhaustif

Sans `sinon`, un `selon` sur une énumération doit traiter **tous** les cas :

```nck
enumeration Couleur: ROUGE, VERT, BLEU fin

fonction temperature(c: Couleur) -> texte:
    selon c:
        cas Couleur.ROUGE: retourner "chaud"
        cas Couleur.VERT, Couleur.BLEU: retourner "froid"
    fin
fin
ecrire(temperature(Couleur.BLEU))
```

```nck
enumeration Couleur: ROUGE, VERT, BLEU fin
fonction f(c: Couleur) -> texte:    // erreur attendue : il manque Couleur.BLEU
    selon c:
        cas Couleur.ROUGE: retourner "chaud"
        cas Couleur.VERT: retourner "froid"
    fin
fin
```

## Comme clé de dictionnaire

```nck
enumeration Couleur: ROUGE, VERT, BLEU fin
variable prix: dico<Couleur, entier> = {Couleur.ROUGE: 10, Couleur.VERT: 12}
ecrire(prix[Couleur.ROUGE], prix.obtenir(Couleur.BLEU, 0))
```

## Convertir depuis un texte

```nck
enumeration Niveau: BAS, MOYEN, HAUT fin

fonction depuis_texte(t: texte) -> Niveau?:
    retourner Niveau.valeurs.trouver(fonction(n): n.nom == t.majuscule())
fin
ecrire(depuis_texte("haut") ?? Niveau.BAS)   // Niveau.HAUT
```

Les énumérations se partagent entre modules comme les classes.
