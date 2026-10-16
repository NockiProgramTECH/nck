# Feuille de route NCK — ce qui reste à faire

État au 16 octobre 2026 : **v0.13.0 en développement, non publiée** (gestionnaire de paquets implémenté ; registre public à déployer).
La version de référence précédente est la v0.12.0.
Historique de ce qui est fait : [CHANGELOG.md](changelog.md).

Principe directeur inchangé : **rapide à prendre en main, simple, typé, en français**. Chaque version livre sa documentation,
ses tests et une entrée dans le CHANGELOG. Les versions sont ordonnées par priorité ; l'ordre peut être ajusté.

---

## Vue d'ensemble

| Version | Thème | Objectif en une phrase |
|---|---|---|
| **v0.13** | Paquets | Partager et réutiliser du code NCK : `nck installer nom`, `importer "nom"` |
| **v0.14** | Interface graphique | Faire des fenêtres en quelques lignes (`fenetre`, `bouton`, `champ`…) |
| **v0.15** | Qualité de vie | Tests intégrés (`test`), `nck formater`, `nck doc`, blocs de doc |
| **v0.16** | Langage avancé | Génériques utilisateur, tuples, unions, énums avec données + `selon` destructurant |
| **v0.17** | Erreurs modernes | `Resultat<T, E>` et opérateur `?`, codes d'erreur, avertissements, erreurs multiples |
| **v0.18** | Modules et stdlib | Espaces de noms réels, `exporter`, stdlib écrite en NCK, FFI Python |
| **v0.19** | Async et flux | `asynchrone` / `attendre`, pipeline `|>`, compréhensions |
| **v0.20** | Outillage pro | LSP standard, débogueur (DAP), playground web, fuzzing, EBNF officielle |
| **v1.0** | Stabilité | Spécification gelée, compatibilité garantie, dépôt public, site |
| **v2.x** | Performance | IR typé → transpilation Python optimisée, puis WASM / natif (moteur C **reporté**, décision utilisateur) |

---

## v0.13 — Gestionnaire de paquets

**Implémenté** : manifeste, commandes, résolution des versions, archives vérifiées, verrouillage, imports de paquets, outil de préparation du registre et scénario de validation des binaires en CI.
Voir [le guide des paquets](PAQUETS.md) et l’exemple `exemples/paquets/maths-plus`.
**Reste à faire avant publication** : créer et alimenter le registre public `nck-paquets`,
puis valider les exécutables autonomes de la v0.13 sur les plateformes cibles.
Les index locaux et HTTPS personnalisés sont utilisables sans ce déploiement.

- `paquet.json` à la racine d'un projet : `nom`, `version`, `description`, `point_entree`, `dependances { "nom": "^1.2" }`.
- Commandes : `nck installer nom[@version]`, `nck desinstaller nom`, `nck paquets` (liste), `nck init` (crée `paquet.json`),
  `nck publier` (plus tard — v1.0).
- Résolution de `importer "nom"` : `./nck_modules/nom/` → `~/.nck/paquets/nom/` → erreur claire « paquet introuvable, essayez `nck installer nom` ».
- Index : un dépôt GitHub `nck-paquets` avec un `index.json` (nom → URL + versions) ; téléchargement en archive, vérification du hash.
- Paquets **100 % NCK** (pas de code Python) pour rester portables avec l'exécutable autonome.
- Verrouillage `paquet.verrou.json` pour des installations reproductibles.
- Doc : `docs/PAQUETS.md` (créer, publier, consommer un paquet) ; exemples : paquet `maths-plus`.

## v0.14 — Interface graphique

**Pourquoi** : demandé par l'utilisateur dès que la POO est complète (c'est fait depuis v0.9).

- Module natif `gui` (basé sur Tkinter embarqué dans l'exécutable — aucune dépendance) :
  `fenetre(titre, largeur, hauteur)`, `etiquette`, `bouton(texte, action)`, `champ`, `case`, `liste_deroulante`, `zone_texte`, `image`, `grille`/`colonne`/`ligne` pour la mise en page.
- Événements avec fonctions anonymes : `bouton("OK", fonction(): ecrire("cliqué"))`.
- Liaison de données simple : `champ.valeur`, `etiquette.texte = …`.
- Boîtes de dialogue : `message`, `question`, `choisir_fichier`.
- Typage complet (classes `Fenetre`, `Bouton`… visibles par l'autocomplétion VS Code).
- Doc : `docs/GUI.md` + 5 exemples (calculatrice, bloc-notes, liste de tâches, convertisseur, jeu du nombre mystère).

## v0.15 — Qualité de vie du développeur

- Blocs `test "nom": … fin` avec `verifier(condition)` / `verifier_egal(a, b)` ; commande `nck tester [dossier]` avec rapport coloré.
- `nck formater fichier.nck` : formateur canonique (indentation, espaces, `fin` alignés) ; option « formater à l'enregistrement » dans VS Code.
- Commentaires de documentation `### …` sur fonctions/classes → `nck doc` génère du Markdown ; affichés au survol dans VS Code.
- `nck executer --temps` (chronométrage), `nck verifier --strict` (avertissements traités en erreurs).
- Tests « golden » : sortie attendue de chaque exemple figée dans `tests/golden/`.

## v0.16 — Langage avancé

- **Génériques utilisateur** : `fonction premier<T>(l: liste<T>): T?`, `classe Pile<T>`.
- **Tuples** : `(entier, texte)`, retour multiple typé, destructuration déjà existante réutilisée.
- **Unions** : `entier | texte`, affinement par `est_un` / `selon type`.
- **Énumérations avec données** : `cas Cercle(rayon: reel)` + `selon` destructurant (`cas Cercle(r): …`), exhaustivité vérifiée.
- **Contrats** : `exige` (précondition) / `garantit` (postcondition) sur les fonctions, vérifiés à l'exécution.
- Doc : chapitres ajoutés à `LANGAGE.md`, exemples `generiques.nck`, `formes.nck`.

## v0.17 — Erreurs modernes

- Type `Resultat<T, E>` (`Ok(v)` / `Erreur(e)`) et opérateur `?` pour propager : `variable f = ouvrir(chemin)?;`.
- Codes d'erreur stables (`NCK-T001` type incompatible, `NCK-S002` nom inconnu…) documentés dans `docs/ERREURS.md` avec explication et correction suggérée ; `nck expliquer NCK-T001`.
- **Erreurs multiples** : le vérificateur continue après la première erreur et les rapporte toutes.
- **Avertissements** : variable inutilisée, code inatteignable, comparaison toujours vraie, ombre d'un nom.
- Suggestions « vouliez-vous dire … ? » (distance d'édition) pour les noms inconnus.

## v0.18 — Modules et bibliothèque standard

- Espaces de noms réels : un module n'expose que ce qu'il `exporte` ; plus de collision de noms entre fichiers.
- Imports relatifs et de dossier (`importer "utils/"` → `utils/module.nck`), imports circulaires détectés avec message clair.
- Stdlib réécrite **en NCK** là où c'est possible (`texte`, `listes`, `maths`), compilée en cache pour rester rapide ; seul le cœur reste natif.
- **FFI Python** optionnelle : `importer python "math" comme m` (désactivée dans l'exécutable autonome strict, activable par option).
- Nouveaux modules : `http` (client), `chemins`, `aleatoire` étendu, `csv`, `regex`.

## v0.19 — Asynchrone et flux de données

- `fonction asynchrone`, `attendre`, `lancer_tous([...])` ; boucle d'événements intégrée (basée sur asyncio).
- Opérateur pipeline `|>` : `donnees |> filtrer(f) |> appliquer(g)`.
- Compréhensions : `[x * 2 pour x dans l si x > 0]`, `{k: v pour …}`.
- Itérateurs paresseux / générateurs (`produire`).

## v0.20 — Outillage professionnel

- Serveur **LSP** standard (remplace le protocole JSON maison) → support Neovim, Sublime, Zed, JetBrains.
- **Débogueur** (DAP) : points d'arrêt, pas à pas, variables dans VS Code.
- **Playground web** : NCK dans le navigateur (moteur via Pyodide) pour essayer sans installer.
- Fuzzing du lexeur/parseur, grammaire **EBNF** officielle dans `docs/GRAMMAIRE.md`, benchmark suivi en CI.

## v1.0 — Stabilité

- Spécification du langage gelée (toute rupture ⇒ v2) ; politique de compatibilité et de dépréciation.
- Dépôt rendu **public** → `installer.sh` / `installer.ps1`, releases et paquets fonctionnent pour tout le monde.
- Site de documentation (généré depuis `docs/`), tutoriel « NCK en 30 minutes », galerie d'exemples.
- Signature de l'exécutable Windows/macOS (plus d'avertissement SmartScreen / Gatekeeper).

## v2.x — Performance

- IR typé interne → **transpilation vers Python optimisé** (gain estimé ×3–10 sur l'interpréteur arborescent actuel).
- Ensuite : cible **WebAssembly** (playground, navigateur) puis **natif** ; le moteur C reste **reporté** jusqu'à décision de l'utilisateur.

---

## Petites tâches transverses (à glisser dans n'importe quelle version)

- [ ] Première construction réelle de l'exécutable via GitHub Actions (tag `v0.12.0`) et correction des éventuels oublis PyInstaller.
- [ ] Icône `.nck` dans l'Explorateur Linux (fichier `.desktop` + MIME) et macOS (bundle `.app`).
- [ ] Traduction anglaise de la documentation (`docs/en/`).
- [ ] Mode `nck --couleur=non` et détection de terminal sans couleur.
- [ ] Complétion automatique du shell (`bash`, `zsh`, `PowerShell`) pour la commande `nck`.
- [ ] Couverture de tests mesurée en CI (objectif ≥ 90 %).
