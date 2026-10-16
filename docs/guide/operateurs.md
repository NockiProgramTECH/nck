# Opérateurs et expressions

## Arithmétique

```nck
ecrire(7 + 2, 7 - 2, 7 * 2)     // 9 5 14
ecrire(7 / 2)                   // 3.5   `/` donne TOUJOURS un reel
ecrire(division_entiere(7, 2))  // 3
ecrire(7 % 2)                   // 1     reste de la division
ecrire(-7 % 3)                  // 2     (comme Python)
ecrire(puissance(2, 10))        // 1024
```

`+` sert aussi à concaténer des textes ou des listes, et `*` à les répéter :

```nck
ecrire("ab" + "cd", "-" * 10)   // abcd ----------
ecrire([1, 2] + [3], [0] * 3)   // [1, 2, 3] [0, 0, 0]
```

## Comparaisons

```nck
ecrire(3 == 3.0, 3 != 4)        // vrai vrai
ecrire(2 < 3, "a" < "b")        // vrai vrai  (textes : ordre alphabétique)
ecrire([1, 2] == [1, 2])        // vrai       listes comparées par contenu
```

Pas de coercition : comparer un `booleen` à un `entier` (`vrai == 1`) est refusé par le vérificateur
(« comparaison impossible entre booleen et entier »).

Les objets de classes sont comparés par **identité** (même objet), sauf si la classe définit `egal` (voir [Classes](classes.md#surcharge-doperateurs)).

## Logique

```nck
variable age = 20
variable permis = vrai
ecrire(age >= 18 et permis)     // vrai
ecrire(age < 18 ou non permis)  // faux
```

`et` et `ou` sont **paresseux** : la partie droite n'est évaluée que si nécessaire. C'est ce qui permet
`x != nul et x.longueur() > 0`.

## Index et tranches

```nck
variable l = [10, 20, 30, 40]
ecrire(l[0], l[-1])             // 10 40   (négatif = depuis la fin)
ecrire(l.tranche(1, 3))         // [20, 30]
ecrire("bonjour"[0], "bonjour".tranche(0, 3))   // b bon
```

## Plages `a..b`

`a..b` produit la liste des entiers de `a` à `b - 1` :

```nck
ecrire(1..5)                    // [1, 2, 3, 4]
pour i dans 0..3: ecrire(i)     // 0 1 2
```

## Repli `??`

`x ?? y` vaut `x` s'il n'est pas `nul`, sinon `y` (voir [Types optionnels](optionnels.md)) :

```nck
variable d: dico<texte, entier> = {"a": 1}
ecrire(d.obtenir("z") ?? 0)     // 0
```

## Expression conditionnelle

```nck
variable n = 7
variable parite = si n % 2 == 0 alors "pair" sinon "impair"
ecrire(parite)
```

## Priorité des opérateurs

Du plus faible au plus fort :

| Niveau | Opérateurs |
|---|---|
| 1 | `??` |
| 2 | `ou` |
| 3 | `et` |
| 4 | `non` |
| 5 | `==  !=  <  >  <=  >=` |
| 6 | `..` |
| 7 | `+  -` |
| 8 | `*  /  %` |
| 9 | `-` unaire |
| 10 | appel `f()`, index `x[i]`, membre `x.y` |

En cas de doute, mettez des parenthèses : `(a et b) ou c`.
