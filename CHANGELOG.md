# Journal des modifications

## 0.11.1 — corrections de l'audit
- **E1** Les `importer` sont traités avant tout : une classe importée peut servir de type (`p: Personne`) et de parent (`herite Personne`).
- **E2** Les fermetures créées dans une boucle (`pour`, `tantque`) capturent la valeur de chaque itération.
- **E3** L'affinement `T?` → `T` est annulé par une affectation (`p = nul`) et n'est pas visible depuis une fermeture.
- **E4** Les très grands entiers (plus de 4300 chiffres) s'affichent (limite Python levée).
- **E5** Plus de trace Python : erreurs internes affichées proprement (`NCK_DEBUG=1` pour la trace), `OverflowError` traduit, caractères comme `²` refusés par le lexeur.
- **E6** Compteur de récursion global et fiable ; l'erreur est attrapable autant de fois que nécessaire.
- **E7** Une fonction décorée peut être définie avant son décorateur.
- **E8** `liste<entier>= [1]` (`>=` collé) est accepté.
- **E9** `si`/`tantque` sur une valeur `quelconque` exigent un booléen à l'exécution ; `vrai == 1` est faux ; échappement inconnu (`\q`) = erreur, `\uXXXX` ajouté ; `tantque vrai:` sans `arreter` compte comme sortie de fonction ; `oppose` corrigé, `ParentNck.__call__` retiré.
- Version unique (`nck.__version__`), `LICENSE` MIT, CI GitHub Actions (Linux/Windows/macOS × Python 3.10/3.12), tests de régression E1–E9.

## 0.11.0
- Notation méthode sur les valeurs (`liste.ajouter(x)`, chaînage), énumérations avec `selon` exhaustif, expression `si … alors … sinon …`, affectation/déclaration multiples et déstructuration, textes `"""…"""`.

## 0.10.0
- Fonctions anonymes avec typage contextuel, `appliquer`/`filtrer`/`reduire`/`chaque`/`trouver`/`tous`/`au_moins_un`, types optionnels `T?` avec affinement et `??`, plages `a..b`.

## 0.9.0
- POO complète : `parent`, `statique`, constantes de classe, membres privés `_x`, méthodes `abstraite`, `est_un`, surcharge d'opérateurs ; décorateurs `@deco` ; `...args` et étalement `f(...liste)`.

## 0.8.0 et avant
- v0.8 serveur d'analyse + extension VS Code ; v0.7 confort (`f"…"`, défauts, `selon`) ; v0.6 bibliothèque standard ; v0.5 modules ; v0.4 dicos ; v0.3 erreurs ; v0.2 classes ; v0.1 moteur.
