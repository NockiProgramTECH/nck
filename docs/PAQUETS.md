# Paquets NCK

Depuis la v0.13, un projet peut déclarer et installer des bibliothèques **100 % NCK**.
Aucune commande d'installation n'exécute de script du paquet, ni de code Python.

!!! warning "État du registre public"
    Le gestionnaire est implémenté, mais le registre public `NockiProgramTECH/nck-paquets`
    reste à créer et à alimenter. L'adresse par défaut lui est réservée.
    Pour le moment, utilisez **`--index`** ou **`NCK_INDEX`** avec votre propre index,
    local ou hébergé en HTTPS. Aucun compte ni jeton n'est nécessaire pour un index public.

## Commandes

```bash
nck init --nom mon-projet        # crée paquet.json et module.nck s'il n'existe pas
nck installer maths-plus        # ajoute et installe la dernière version compatible
nck installer maths-plus@1.2.3  # version exacte
nck installer "maths-plus@^1.2" # plage de versions
nck installer                   # installe les dépendances déjà déclarées
nck paquets                     # liste les dépendances directes et transitives
nck desinstaller maths-plus     # retire la dépendance et élague les paquets inutilisés
```

Sauf `init`, ces commandes recherchent le `paquet.json` le plus proche, en remontant
à partir du dossier courant. Elles fonctionnent donc aussi depuis un sous-dossier.
`init` refuse d'écraser un manifeste existant et conserve un éventuel `module.nck`.

Pour un index personnalisé :

```bash
nck installer maths-plus --index /chemin/vers/index.json
nck installer --index https://exemple.org/nck/index.json
nck desinstaller maths-plus --index /chemin/vers/index.json
```

`NCK_INDEX` définit l'index par défaut ; `--index` est prioritaire. Un index distant
ne peut référencer que des archives HTTPS. Un index local peut également référencer
des ZIP locaux, avec des chemins relatifs au fichier d'index.

## Décrire un projet

```json
{
  "nom": "mon-projet",
  "version": "0.1.0",
  "description": "Une application en NCK",
  "point_entree": "module.nck",
  "dependances": {
    "maths-plus": "^1.2"
  }
}
```

- `nom` : lettres minuscules ASCII, chiffres et tirets, commence par une lettre
  (exemples : `maths-plus`, `outils2`).
- `version` : trois nombres, par exemple `1.2.3`, sans préversion ni préfixe `v`.
- `description` : texte facultatif.
- `point_entree` : chemin `.nck` relatif à la racine du paquet, `module.nck` par défaut.
- `dependances` : objet associant un nom à une contrainte, vide par défaut.

### Contraintes disponibles

| Contrainte | Versions acceptées |
|---|---|
| `1.2.3` | uniquement `1.2.3` |
| `*` | toutes les versions stables |
| `^1.2` / `^1.2.3` | de `1.2.0` / `1.2.3` inclus à `2.0.0` exclu |
| `^0.2.3` | de `0.2.3` inclus à `0.3.0` exclu |
| `^0.0.3` | uniquement `0.0.3` |
| `~1.2` / `~1.2.3` | de `1.2.0` / `1.2.3` inclus à `1.3.0` exclu |
| `^1` / `~1` | de `1.0.0` inclus à `2.0.0` exclu |

Les contraintes composées (`>=`, `||`, etc.) et les préversions ne sont pas encore
prises en charge. Un ajout sans version enregistre `^version_installee`.
Le résolveur choisit les versions les plus élevées compatibles, en essayant des
versions antérieures si une dépendance transitive provoque un conflit. Une seule
version de chaque paquet est installée pour tout le projet. La résolution est
limitée à 200 paquets et 10 000 essais.

## Importer une bibliothèque

Après installation de `maths-plus`, les imports suivants sont possibles :

```text
importer "maths-plus" comme maths
ecrire(maths.carre(5))

depuis "maths-plus" importer carre
ecrire(carre(6))
```

Sans `comme`, le nom du paquet devient le nom du module, avec les tirets remplacés
par des soulignements : `maths_plus.carre(5)`.
Les fonctions, classes et types restent vérifiés avant toute exécution.

Le chargeur cherche, depuis le fichier qui importe :

1. `nck_modules/nom/`, puis les `nck_modules` des dossiers parents ;
2. `~/.nck/paquets/nom/` (emplacement global manuel, sans commande d'installation globale) ;
3. une erreur avec la suggestion `nck installer nom`.

Un paquet local présent mais invalide provoque une erreur ; il n'est pas remplacé
silencieusement par le paquet global. Les imports de fichiers (`"./outils.nck"`,
`"../modeles.nck"`) restent relatifs au fichier qui importe, y compris dans un paquet.
Les modules sont mis en cache et exécutés une seule fois par programme ; les cycles
d'imports restent refusés.

## Verrouillage et installations reproductibles

`nck installer` écrit :

- `paquet.json` : dépendances directes et contraintes ;
- `paquet.verrou.json` : versions exactes, URL, SHA-256 et dépendances transitives ;
- `nck_modules/` : fichiers des paquets installés.

**Versionnez les deux fichiers JSON**, mais pas `nck_modules/` : ce dossier est généré
et entièrement remplacé par le gestionnaire. N'y stockez pas de modifications manuelles.
Pour un index local, les URL du verrou sont des `file://` absolus : elles ne sont donc
pas portables vers une autre machine. Utilisez des URL HTTPS pour partager un verrou.

Le verrou existant est préféré tant qu'il satisfait les contraintes. Si toutes les
versions verrouillées conviennent, l'index n'est pas consulté. Les archives restent
cependant nécessaires et sont retéléchargées puis vérifiées : **ce n'est pas un cache
hors ligne**. Pour changer de version, utilisez une nouvelle contrainte explicite,
par exemple `nck installer maths-plus@1.3.0` ; il n'y a pas encore de commande `mettre-a-jour`.

L'installation est préparée dans un dossier temporaire. Une archive corrompue, un
conflit ou un manifeste invalide ne modifie pas l'installation existante. Les erreurs
d'écriture lors du remplacement déclenchent une restauration des fichiers précédents
(ce n'est pas une transaction résistante à une coupure de courant). Ne lancez pas
deux installations simultanément dans le même projet.

## Créer un paquet et un index local

Le dépôt contient un exemple dans `exemples/paquets/maths-plus/`.
Une archive ZIP doit contenir **directement** `paquet.json` et le point d'entrée,
pas un dossier parent supplémentaire.

L'outil de préparation fourni pour les développeurs produit un ZIP et un index
local, sans rien publier sur Internet. Depuis la racine du dépôt :

```bash
python outils/preparer_paquet.py exemples/paquets/maths-plus --sortie registre-local
```

Il vérifie le manifeste, les chemins, les fichiers et la syntaxe des sources NCK.
Les types ne sont pas vérifiés à cette étape : ils le seront lors de l'import avec
les dépendances installées. Le ZIP a un ordre, des dates et des permissions fixes,
et n'utilise pas de compression pour rester reproductible entre plateformes.
Le SHA-256 est calculé automatiquement et l'index existant est conservé et enrichi.
**Une version déjà présente ne peut pas changer de contenu ni d'URL** : augmentez
`version` avant de produire une nouvelle archive. Le dossier de sortie doit être
hors du paquet source.

Les fichiers de travail sont exclus : `.git`, `.gitignore`, `.gitattributes`,
`.editorconfig`, `.DS_Store`, `.venv`, `venv`, `__pycache__`, `.pytest_cache`,
`nck_modules`, `build`, `dist`, `.vscode`, `paquet.verrou.json` et `.nck-install-*`.
Les liens symboliques et les autres types de fichiers non portables sont refusés.

Créez ensuite un projet dans un autre dossier, puis lancez :

```bash
nck init --nom essai-paquets
nck installer maths-plus --index /chemin/vers/nck/registre-local/index.json
nck paquets
```

Pour vérifier le résultat, écrivez dans `module.nck` :

```text
importer "maths-plus" comme maths
ecrire(maths.carre(5))         // 25
ecrire(maths.cube(3))          // 27
```

Puis : `nck verifier module.nck` et `nck module.nck`.
La préparation d'archives peut se faire avec n'importe quel outil ZIP ; **Python
n'est pas requis par le gestionnaire dans l'exécutable autonome NCK**.

## Héberger un index

Le format de l’index généré est :
`nom → versions → version → {url, sha256}`. Pour un index distant, les URL peuvent
être absolues ou relatives à l'index et doivent utiliser HTTPS. Les ZIP peuvent
être hébergés dans des GitHub Releases. Une archive doit conserver son URL et son
contenu pour que les verrous existants restent utilisables.

### Préparer les fichiers pour un registre public

Pour générer les URL d'archives HTTPS à l'avance :

```bash
python outils/preparer_paquet.py exemples/paquets/maths-plus --sortie registre-public --url-base https://github.com/NockiProgramTECH/nck-paquets/releases/download/maths-plus-v1.0.0
```

Ce registre et cette release sont **à créer séparément**. L'outil ne fait aucun
appel GitHub et ne téléverse rien. Utilisez un autre dossier de sortie que pour
l'index local, car une URL déjà enregistrée est immuable.

Avant de mettre l'index en service :

1. Vérifiez que le dépôt du registre est public et accessible sans authentification.
2. Créez une release correspondant à l'URL choisie, puis joignez le ZIP généré
   **sans le modifier**.
3. Ajoutez les entrées du fichier `index.json` au registre en conservant toutes les
   versions précédentes.
4. Testez `nck installer maths-plus@1.0.0 --index URL_HTTPS_DE_L_INDEX` depuis un
   projet vierge, puis testez l'import et la restauration depuis le verrou.

Ne rendez pas l'index visible avant les archives qu'il référence. Ne régénérez
pas les ZIP avec un autre logiciel après le calcul des empreintes.

Les archives acceptent les fichiers `.nck`, `.json`, `.md`, `.txt`, `LICENSE` et
`LICENCE`. Les liens symboliques, chemins sortant du paquet, noms de fichiers non
portables et entrées dupliquées sont refusés. Limites : 20 Mio par téléchargement
ZIP, 50 Mio décompressés et 5 000 entrées. Le SHA-256 protège contre une archive
modifiée, **pas contre un index malveillant** : utilisez une source de confiance.
Un paquet NCK peut accéder aux fonctions natives lorsqu'un programme l'importe ;
il n'est pas exécuté dans un bac à sable.

La publication automatique (`nck publier`), l'authentification à un registre privé,
les archives TAR et les dépendances Git directes restent hors de cette première version.
