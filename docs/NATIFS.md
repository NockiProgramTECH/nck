# Référence des fonctions natives

Cette page est générée depuis `nck/documentation.py` (la même source que le survol dans VS Code).

## Entrées / sorties

| Fonction | Description |
|---|---|
| `ecrire(...valeurs) -> rien` | Affiche les valeurs séparées par un espace, puis un retour à la ligne. |
| `ecrire_erreur(...valeurs) -> rien` | Comme `ecrire`, mais sur la sortie d'erreur. |
| `lire(invite: texte = "") -> texte` | Lit une ligne saisie au clavier (sans le retour à la ligne). |

## Conversions et types

| Fonction | Description |
|---|---|
| `texte(valeur: quelconque) -> texte` | Convertit n'importe quelle valeur en texte. |
| `entier(valeur: quelconque) -> entier` | Convertit en entier ("42" → 42, 3.9 → 3, vrai → 1). Erreur si impossible. |
| `reel(valeur: quelconque) -> reel` | Convertit en nombre réel ("2.5" ou "2,5" → 2.5). |
| `booleen(valeur: quelconque) -> booleen` | Convertit en booléen ("vrai"/"oui"/"1" → vrai). |
| `type_de(valeur: quelconque) -> texte` | Nom du type d'une valeur à l'exécution ("entier", "liste", nom de classe…). |

## Listes

| Fonction | Description |
|---|---|
| `longueur(x: liste | texte | dico) -> entier` | Nombre d'éléments d'une liste ou d'un dico, ou de caractères d'un texte. |
| `intervalle(debut: entier, fin: entier, pas: entier = 1) -> liste<entier>` | Liste d'entiers de `debut` (inclus) à `fin` (exclu). `intervalle(5)` = [0, 1, 2, 3, 4]. |
| `ajouter(l: liste<T>, element: T) -> rien` | Ajoute un élément à la fin de la liste. |
| `inserer(l: liste<T>, index: entier, element: T) -> rien` | Insère un élément à la position donnée. |
| `retirer(l: liste<T>, index: entier = -1) -> T` | Retire et retourne l'élément à l'index (le dernier par défaut). Pour un dico : `retirer(d, cle)`. |
| `contient(c: liste | texte | dico, x) -> booleen` | Vrai si la liste contient `x`, si le texte contient le sous-texte, ou si le dico a la clé. |
| `position(c: liste | texte, x) -> entier` | Index de la première occurrence, ou -1 si absent. |
| `trier(l: liste<T>) -> liste<T>` | Nouvelle liste triée par ordre croissant. |
| `inverser(l: liste<T>) -> liste<T>` | Nouvelle liste dans l'ordre inverse. |
| `copier(x: liste | dico) -> liste | dico` | Copie superficielle d'une liste ou d'un dico. |
| `tranche(c: liste | texte, debut: entier, fin: entier = longueur) -> liste | texte` | Sous-liste ou sous-texte de `debut` (inclus) à `fin` (exclu). |
| `somme(l: liste<entier | reel>) -> entier | reel` | Somme des nombres de la liste. |
| `minimum(l: liste) | minimum(a, b, ...) -> T` | Plus petite valeur d'une liste ou des arguments. |
| `maximum(l: liste) | maximum(a, b, ...) -> T` | Plus grande valeur d'une liste ou des arguments. |

## Dictionnaires

| Fonction | Description |
|---|---|
| `cles(d: dico<K, V>) -> liste<K>` | Liste des clés du dictionnaire (dans l'ordre d'insertion). |
| `valeurs(d: dico<K, V>) -> liste<V>` | Liste des valeurs du dictionnaire. |
| `obtenir(d: dico<K, V>, cle: K, defaut: V) -> V` | Valeur associée à la clé, ou `defaut` si la clé est absente (nul sans défaut). |
| `fusionner(a: dico, b: dico) -> dico` | Nouveau dico contenant les entrées de `a` puis de `b` (qui l'emporte). |

## Textes

| Fonction | Description |
|---|---|
| `majuscule(t: texte) -> texte` | Texte en majuscules. |
| `minuscule(t: texte) -> texte` | Texte en minuscules. |
| `nettoyer(t: texte) -> texte` | Supprime les espaces au début et à la fin. |
| `remplacer(t: texte, ancien: texte, nouveau: texte) -> texte` | Remplace toutes les occurrences de `ancien` par `nouveau`. |
| `decouper(t: texte, separateur: texte = espaces) -> liste<texte>` | Découpe le texte en morceaux. Sans séparateur : sur les espaces. |
| `joindre(l: liste, separateur: texte = "") -> texte` | Assemble les éléments en un texte, séparés par `separateur`. |
| `commence_par(t: texte, prefixe: texte) -> booleen` | Vrai si le texte commence par `prefixe`. |
| `termine_par(t: texte, suffixe: texte) -> booleen` | Vrai si le texte se termine par `suffixe`. |
| `caractere(code: entier) -> texte` | Caractère correspondant au code Unicode (65 → "A"). |
| `code(c: texte) -> entier` | Code Unicode d'un caractère ("A" → 65). |
| `formater(modele: texte, ...valeurs) -> texte` | Remplace chaque `{}` par la valeur suivante (ou `{0}`, `{1}` par position). |
| `est_nombre(t: texte) -> booleen` | Vrai si le texte représente un nombre ("3.5", "-2"). |
| `est_entier(t: texte) -> booleen` | Vrai si le texte représente un entier ("42", "-7"). |
| `remplir_gauche(t: texte, taille: entier, car: texte) -> texte` | Complète à gauche jusqu'à `taille` caractères ("7", 3, "0" → "007"). |
| `remplir_droite(t: texte, taille: entier, car: texte) -> texte` | Complète à droite jusqu'à `taille` caractères. |

## Mathématiques

| Fonction | Description |
|---|---|
| `absolu(x: entier | reel) -> entier | reel` | Valeur absolue. |
| `racine(x: reel) -> reel` | Racine carrée (erreur si négatif). |
| `puissance(base: reel, exposant: reel) -> reel` | `base` élevé à la puissance `exposant` (entier si les deux sont entiers). |
| `arrondir(x: reel, decimales: entier = 0) -> entier | reel` | Arrondit (entier sans décimales, réel sinon). |
| `plancher(x: reel) -> entier` | Plus grand entier ≤ x. |
| `plafond(x: reel) -> entier` | Plus petit entier ≥ x. |
| `division_entiere(a: entier, b: entier) -> entier` | Quotient entier (7, 2 → 3). `/` donne toujours un réel. |
| `aleatoire() -> reel | aleatoire(max) | aleatoire(min, max) -> entier` | Réel dans [0, 1[ sans argument ; entier entre les bornes incluses sinon. |

## Temps et dates

| Fonction | Description |
|---|---|
| `horloge() -> reel` | Secondes écoulées (haute précision) : pour chronométrer. |
| `attendre(secondes: reel) -> rien` | Met le programme en pause. |
| `maintenant() -> reel` | Horodatage actuel (secondes depuis le 1er janvier 1970). |
| `date(horodatage: reel = maintenant()) -> dico<texte, entier>` | Dico avec annee, mois, jour, heure, minute, seconde, jour_semaine (1 = lundi). |
| `formater_date(format: texte = "JJ/MM/AAAA hh:mm:ss", horodatage: reel = maintenant()) -> texte` | Date formatée : AAAA, AA, MM, JJ, hh, mm, ss. |
| `creer_date(annee, mois, jour, heure = 0, minute = 0, seconde = 0) -> reel` | Horodatage d'une date donnée. |

## Fichiers

| Fonction | Description |
|---|---|
| `lire_fichier(chemin: texte) -> texte` | Contenu complet d'un fichier texte (UTF-8). Erreur attrapable si introuvable. |
| `lire_lignes(chemin: texte) -> liste<texte>` | Lignes d'un fichier texte. |
| `ecrire_fichier(chemin: texte, contenu: texte) -> rien` | Écrit le texte dans le fichier (écrase l'existant). |
| `ajouter_fichier(chemin: texte, contenu: texte) -> rien` | Ajoute le texte à la fin du fichier. |
| `supprimer_fichier(chemin: texte) -> rien` | Supprime un fichier. |
| `fichier_existe(chemin: texte) -> booleen` | Vrai si le fichier existe. |
| `dossier_existe(chemin: texte) -> booleen` | Vrai si le dossier existe. |
| `creer_dossier(chemin: texte) -> rien` | Crée le dossier (et ses parents) s'il n'existe pas. |
| `lister_dossier(chemin: texte = ".") -> liste<texte>` | Noms des fichiers et dossiers contenus, triés. |
| `joindre_chemin(...morceaux: texte) -> texte` | Assemble des morceaux de chemin avec le bon séparateur. |
| `dossier_courant() -> texte` | Dossier de travail actuel. |

## JSON

| Fonction | Description |
|---|---|
| `vers_json(valeur, joli: booleen = faux) -> texte` | Convertit listes, dicos, objets (leurs champs), nombres, textes, booléens en JSON. |
| `depuis_json(t: texte) -> quelconque` | Analyse un texte JSON (dicos, listes…). Erreur attrapable si invalide. |

## Système

| Fonction | Description |
|---|---|
| `arguments() -> liste<texte>` | Arguments passés après le fichier : `nck prog.nck a b` → ["a", "b"]. |
| `variable_env(nom: texte, defaut: texte = "") -> texte` | Valeur d'une variable d'environnement. |
| `quitter(code: entier = 0) -> rien` | Arrête le programme avec le code de sortie donné. |
| `verifier(condition: booleen, message: texte = "assertion échouée") -> rien` | Lève une erreur (attrapable) si la condition est fausse. |
