# Questions fréquentes

## Général

**Pourquoi un langage en français ?**
Pour apprendre et produire sans la barrière de l'anglais : les mots-clés (`si`, `tantque`, `fonction`, `classe`) et les
messages d'erreur sont dans la langue dans laquelle on réfléchit.

**NCK est-il typé ?**
Oui, statiquement : chaque variable a un type (écrit ou déduit) vérifié **avant** l'exécution, comme TypeScript.
Il y a aussi des vérifications à l'exécution (création d'objets, `quelconque`).

**Est-ce rapide ?**
NCK est un interpréteur écrit en Python : largement suffisant pour des scripts, outils, jeux textuels et programmes
d'apprentissage. Un moteur plus rapide est prévu dans la [feuille de route](ROADMAP.md).

**Faut-il installer Python ?**
Non. L'installateur fournit un exécutable `nck` autonome. Python n'est nécessaire que pour contribuer au langage.

**Quelle licence ?**
MIT : utilisation libre, y compris commerciale.

## Langage

**Pourquoi `si liste:` est-il refusé ?**
Seuls `vrai` et `faux` sont des booléens. Écrivez `si liste.longueur() > 0:`. Cela évite les surprises de Python/JS
(`0`, `""`, `[]` « faux »).

**`7 / 2` donne `3.5`, comment avoir `3` ?**
`division_entiere(7, 2)`. `/` retourne toujours un `reel`.

**Comment représenter « pas de valeur » ?**
Avec un type optionnel `T?` et `nul` ; voir [Types optionnels](guide/optionnels.md).

**Pas de `nul` possible dans un `texte` ? Et pour les champs facultatifs ?**
`champ: texte? = nul` dans la classe.

**Pourquoi mon bloc d'une ligne n'a pas besoin de `fin` ?**
`si x > 0: ecrire(x)` est la forme courte (une seule instruction, même ligne). Dès qu'il y a un retour à la ligne, le bloc
se termine par `fin`.

**Comment écrire un `switch` ?**
`selon valeur: cas 1: … cas 2, 3: … sinon: … fin` ; avec une énumération, le vérificateur impose l'exhaustivité.

**Peut-on écrire des accents dans les identifiants ?**
Non (`prénom` → erreur lexicale) : utilisez `prenom`. Les textes et commentaires, eux, acceptent tout l'Unicode.

**Les arguments nommés `f(a = 1)` ?**
Uniquement à la création d'objets : `Personne(nom = "Awa")`.

**Existe-t-il des génériques, tuples, unions, async ?**
Prévus (v0.16–v0.19) : voir la [feuille de route](ROADMAP.md).

## Outils

**Comment avoir la coloration et les erreurs en direct ?**
Installez l'[extension VS Code](EDITEUR.md) (l'installateur propose de le faire).

**`nck` n'est pas reconnu après l'installation.**
Ouvrez un **nouveau** terminal (le PATH est lu au démarrage). Sous Windows, vérifiez que l'option « Ajouter au PATH » était
cochée ; sinon relancez le Setup.

**Comment signaler un bogue ?**
Ouvrez une issue sur [GitHub](https://github.com/NockiProgramTECH/nck/issues) avec le programme minimal et le message.
Si le message commence par « Erreur interne », ajoutez la sortie de `NCK_DEBUG=1 nck fichier.nck`.
