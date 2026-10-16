# Ligne de commande `nck`

```text
nck                          bannière puis mode interactif (REPL)
nck fichier.nck [args…]      exécute un programme (commande par défaut)
nck executer fichier.nck     idem, explicite
nck verifier fichier.nck     vérifie syntaxe et types SANS exécuter
nck repl                     mode interactif
nck info                     version, emplacement, mode autonome ou non
nck serveur                  serveur d'analyse pour les éditeurs (JSON)
nck --version                numéro de version
nck --help                   aide
```

## Exécuter

```bash
nck programme.nck
nck programme.nck Awa 3          # arguments → arguments() = ["Awa", "3"]
```

Le dossier courant n'a pas d'importance : les `importer` sont relatifs au fichier qui importe.

## Vérifier

```bash
nck verifier programme.nck
```

Lit le fichier et tous ses modules, vérifie la syntaxe et les types, n'exécute **rien**.
Code de sortie 0 si tout va bien, 1 sinon — pratique dans un script ou une CI :

```bash
for f in src/*.nck; do nck verifier "$f" || exit 1; done
```

## Codes de sortie

| Code | Signification |
|---|---|
| 0 | succès |
| 1 | erreur NCK (syntaxe, type, exécution non attrapée) ou `quitter(1)` |
| 2 | erreur interne (bogue de NCK) — `NCK_DEBUG=1 nck f.nck` affiche la trace |
| 130 | ++ctrl+c++ |

## Variables d'environnement

| Variable | Effet |
|---|---|
| `NCK_DEBUG=1` | affiche la trace Python complète en cas d'erreur interne |

## Entrée / sortie

- `ecrire` écrit sur la sortie standard, `ecrire_erreur` sur la sortie d'erreur ; tout est en UTF-8.
- `lire(invite)` lit une ligne sur l'entrée standard — vous pouvez donc rediriger un fichier : `nck prog.nck < donnees.txt`.

## Sous Windows

Si l'option a été cochée à l'installation :

- **double-clic** sur un `.nck` → exécution dans une console ;
- **clic droit** → *Exécuter avec NCK* / *Vérifier avec NCK*.
