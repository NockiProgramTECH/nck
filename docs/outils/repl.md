# Mode interactif (REPL)

Tapez `nck` (ou `nck repl`) pour essayer le langage une ligne à la fois :

```text
$ nck
  _   _  ____ _  __
 | \ | |/ ___| |/ /   NCK 0.12.0 — langage de programmation simple, typé et en français
 ...
>>> variable x = 21
>>> x * 2
42
>>> fonction carre(n: entier) -> entier: retourner n * n
>>> carre(x)
441
>>> x = "a"
Erreur de type : 'x' est de type entier, mais reçoit un texte
>>> pour i dans 3:
...     ecrire(i)
... fin
0
1
2
```

- Une **expression** affiche sa valeur ; une instruction n'affiche rien.
- Les blocs (`si`, `pour`, `fonction`, `classe`…) se poursuivent sur les lignes `...` jusqu'au `fin`.
- Les variables et fonctions restent définies d'une ligne à l'autre ; les erreurs ne font pas perdre l'état.
- Quitter : ++ctrl+d++ (Linux/macOS), ++ctrl+z++ puis ++enter++ (Windows), ou `quitter()`.

!!! tip
    Le REPL est idéal pour vérifier une fonction native : `"a-b".decouper("-")`, `formater_date("AAAA")`, `date()`…
