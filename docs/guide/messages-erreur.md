# Messages d'erreur

NCK affiche toujours la ligne, la colonne et un extrait du code. Quatre familles (lexicale, syntaxe, type, exécution) :

```text
Erreur lexicale : échappement inconnu '\q'
Erreur de syntaxe : 'fin' attendu pour fermer le bloc commencé ligne 2
Erreur de type : 'age' est de type entier, mais reçoit un texte
  --> programme.nck:3:7
   |
  3| age = "vingt"
   |       ^
Erreur d'exécution : division par zéro
```

Les erreurs de syntaxe et de type sont détectées **avant** d'exécuter la moindre ligne (`nck verifier` ne fait que cela).

## Codes de sortie

| Code | Signification |
|---|---|
| 0 | succès |
| 1 | erreur NCK (syntaxe, type ou exécution non attrapée), ou `quitter(1)` |
| 2 | erreur interne de NCK (merci de la signaler, avec `NCK_DEBUG=1` pour la trace) |
| 130 | interrompu par ++ctrl+c++ |

## Erreurs fréquentes et solutions

| Message | Cause | Solution |
|---|---|---|
| `'fin' attendu pour fermer le bloc commencé ligne N` | bloc multi-lignes sans `fin` | ajoutez `fin`, ou mettez l'unique instruction sur la même ligne |
| `'x' est de type entier, mais reçoit un texte` | changement de type d'une variable | convertissez (`entier(...)`) ou déclarez une autre variable |
| `la condition de 'si' doit être un booleen, mais c'est un liste<entier>` | `si liste:` / `si n:` | `si liste.longueur() > 0:` / `si n != 0:` |
| `variable 'x' inconnue` | faute de frappe, ou variable hors de portée | vérifiez l'orthographe et le bloc de déclaration |
| `une valeur de type texte? n'a pas de champ ni de méthode … (la valeur peut être nul …)` | optionnel utilisé sans test | `si x != nul:` ou `x ?? repli` |
| `ce 'selon' sur Couleur n'est pas complet : il manque …` | cas d'énumération oublié | ajoutez le `cas` ou un `sinon` |
| `la fonction 'g' doit retourner un texte dans tous les cas` | `fonction -> T` sans `retourner` final | ajoutez un `retourner` après les `si` |
| `'_x' est privé` | accès à un membre `_x` hors de la classe | passez par une méthode publique |
| `'Forme' est abstraite (il manque 'aire')` | instanciation d'une classe abstraite | instanciez une classe enfant qui implémente la méthode |
| `les arguments nommés ne sont possibles que pour créer un objet` | `f(a = 1)` sur une fonction | passez les arguments dans l'ordre |
| `division par zéro` | exécution | testez le diviseur, ou `essayer` / `attraper` |
| `index 5 hors limites (la liste a 3 élément(s))` | exécution | vérifiez `longueur()` |
| `clé "x" introuvable dans le dictionnaire` | exécution | `d.obtenir("x", defaut)` ou `d.contient("x")` |
| `impossible de convertir le texte 'abc' en entier` | `entier("abc")` | testez `est_entier(t)` ou attrapez |
| `récursion trop profonde dans 'f' (plus de 2000 appels imbriqués)` | récursion sans cas de base | ajoutez la condition d'arrêt ou passez à une boucle |
| `échappement inconnu '\q'` | `"\q"` dans un texte | `"\\q"` pour un antislash littéral |

## Lire un message dans VS Code

Avec l'[extension](../EDITEUR.md), les erreurs sont soulignées pendant la frappe et listées dans le panneau
*Problèmes* (++ctrl+shift+m++). Survolez le soulignement pour voir le message complet.
