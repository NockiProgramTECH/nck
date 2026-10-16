# Gestion des erreurs

NCK distingue les erreurs détectées **avant** l'exécution (syntaxe, types) et les erreurs **d'exécution**
(division par zéro, fichier introuvable, `verifier` qui échoue…). Seules les secondes se gèrent dans le programme.

## `essayer` / `attraper` / `enfin`

```nck
essayer:
    variable n = entier("abc")
    ecrire(10 / n)
attraper e:                          // e est de type Erreur
    ecrire("Problème :", e.message)
enfin:                               // facultatif, toujours exécuté
    ecrire("terminé")
fin
```

Erreurs d'exécution attrapables : conversion impossible, division par zéro, index hors limites, clé absente,
fichier introuvable, `verifier(...)` faux, récursion trop profonde, et toutes les erreurs levées par `lever`.

## Lever une erreur

```nck
fonction racine_sure(x: reel) -> reel:
    si x < 0: lever "racine d'un nombre négatif"
    retourner racine(x)
fin

essayer:
    ecrire(racine_sure(-1.0))
attraper e:
    ecrire(e.message)            // racine d'un nombre négatif
fin
```

`verifier(condition, message)` est un raccourci : lève une erreur si la condition est fausse.

## Erreurs personnalisées

`Erreur` est une classe intégrée avec un champ `message: texte`. Héritez-en pour créer les vôtres :

```nck
classe ErreurSolde herite Erreur:
    manque: entier
fin

fonction retirer(solde: entier, montant: entier) -> entier:
    si montant > solde: lever ErreurSolde("solde insuffisant", montant - solde)
    retourner solde - montant
fin

essayer:
    retirer(100, 130)
attraper ErreurSolde e:              // seulement ce type (et ses enfants)
    ecrire(e.message, "il manque", e.manque)
attraper e:                          // tout le reste
    ecrire("autre :", e.message)
fin
```

Les clauses `attraper` sont testées dans l'ordre ; si aucune ne correspond, l'erreur remonte à l'appelant.
Une erreur jamais attrapée arrête le programme avec un message et le code de sortie 1.

## Relancer

```nck
fonction charger(chemin: texte) -> texte:
    essayer:
        retourner lire_fichier(chemin)
    attraper e:
        ecrire("échec de lecture, on relance")
        lever e
    fin
fin
essayer:
    charger("inexistant.txt")
attraper e:
    ecrire("attrapé plus haut :", e.message)
fin
```

## Bonnes pratiques

- Attrapez **près** de l'endroit où vous savez quoi faire de l'erreur ; sinon laissez-la remonter.
- Utilisez des classes d'erreur dédiées pour ce que l'appelant doit distinguer, `lever "message"` pour le reste.
- Préférez tester avant quand c'est simple : `fichier_existe(c)`, `est_entier(t)`, `d.obtenir(k, defaut)`.
- `enfin` sert au nettoyage (fermer, supprimer un fichier temporaire), pas à la logique métier.
