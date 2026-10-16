# Journal des modifications

## 0.13.0 — gestionnaire de paquets (non publiée)
- Projets `paquet.json` et commandes `nck init`, `nck installer [nom[@version]]`, `nck desinstaller nom`, `nck paquets`.
- Index JSON local ou HTTPS, configurable par `--index` / `NCK_INDEX` ; archives ZIP 100 % NCK avec contrôle SHA-256, validation des chemins et limites de taille. Aucun script d’installation exécuté.
- Résolution des dépendances transitives avec retour sur les versions antérieures en cas de conflit ; contraintes exactes, `*`, `^` et `~`.
- Verrou `paquet.verrou.json` (versions, sources, empreintes), installation préparée avant remplacement et restauration en cas d’erreur d’écriture.
- Imports par nom de paquet depuis les `nck_modules` du fichier et de ses parents, puis `~/.nck/paquets` ; imports locaux inchangés, cache et vérification des types conservés.
- Exécutable autonome : réintégration de `http` et `email`, nécessaires à `urllib`, dans la configuration PyInstaller.
- Préparation de bibliothèques avec `outils/preparer_paquet.py` : ZIP reproductibles, validation de la syntaxe et du contenu, fusion d'index, empreintes et protection des versions existantes ; `--url-base` pour préparer une publication HTTPS, sans téléversement.
- Construction : diagnostic préalable de PyInstaller/libpython sans supprimer les anciens artefacts en cas de prérequis manquant ; validation fonctionnelle des paquets dans chaque binaire de la matrice de release, hors du dépôt et sans Python dans le PATH.
- Guide `docs/PAQUETS.md`, bibliothèque d’exemple `exemples/paquets/maths-plus` et tests de régression.
- Reste à déployer : le registre public `NockiProgramTECH/nck-paquets`. Les index personnalisés sont utilisables dès maintenant.

## 0.12.0 — installation sans Python
- Site de documentation complet (MkDocs Material, `mkdocs.yml`, `docs/`) publié sur GitHub Pages par `docs.yml` : tutoriel, guide du langage en 15 chapitres, référence, outils, exemples, FAQ ; coloration NCK (`outils/pygments_nck`) ; tous les extraits sont vérifiés et exécutés par `outils/verifier_doc.py`.
- Exécutable autonome `nck` (PyInstaller, `installateur/construire.py` + `nck.spec`) : Python embarqué, exemples, docs et extension VS Code inclus.
- **Windows** : `NCK-Setup-<version>.exe` (Inno Setup, `installateur/windows/nck.iss`) — ajout au PATH, association des fichiers `.nck` avec icône, menu contextuel « Exécuter / Vérifier avec NCK », installation optionnelle de l'extension VS Code, désinstallateur propre.
- **Linux / macOS** : `installateur/installer.sh` (téléchargement de la release, `~/.nck`, lien dans `~/.local/bin`, PATH, extension VS Code) ; `installateur/installer.ps1` pour Windows en ligne de commande.
- GitHub Actions `release.yml` : à chaque tag `v*`, construction Linux x64/arm64, Windows x64, macOS x64/arm64 + Setup Windows, publication dans la Release.
- CLI : bannière et REPL quand `nck` est lancé sans argument, nouvelle commande `nck info` (version, chemin, autonome ou non).
- Extension VS Code 0.5.0 : utilise l'exécutable `nck` du PATH (réglage `nck.commande`), `python -m nck` en repli.
- Documentation : `docs/INSTALLATION.md`.
- Correctif : sous Windows avec Python < 3.12, exécution dans un fil à grande pile (la pile C du fil principal débordait avant la limite de 2000 appels NCK).

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
