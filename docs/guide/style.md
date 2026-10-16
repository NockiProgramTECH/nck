# Style et bonnes pratiques

Ces conventions sont celles de la bibliothèque standard et des exemples fournis ; les suivre rend le code
immédiatement familier aux autres programmeurs NCK.

## Nommage

| Élément | Convention | Exemples |
|---|---|---|
| variables, fonctions, méthodes, champs | `minuscules_avec_tirets_bas` | `nombre_total`, `calculer_moyenne` |
| classes, énumérations | `PremiereLettreMajuscule` | `Personne`, `ErreurSolde`, `Couleur` |
| constantes, valeurs d'énumération | `MAJUSCULES` | `PI`, `MAX_TACHES`, `Couleur.ROUGE` |
| membres privés | préfixe `_` | `_solde`, `_recalculer()` |
| fichiers | `minuscules.nck` | `personne.nck`, `utilitaires_texte.nck` |

Écrivez en français, sans accents dans les identifiants (`age`, `prenom`, `annee`) : c'est plus simple à taper
et compatible avec tous les claviers.

## Mise en forme

- Indentation de **4 espaces** à l'intérieur des blocs ; `fin` aligné avec le mot-clé qui ouvre le bloc.
- Forme courte (`si x > 0: ecrire(x)`) pour une seule instruction simple ; forme longue avec `fin` dès qu'il y en a deux.
- Un espace autour des opérateurs (`a + b`, `x == 1`), après les virgules, pas avant `(` d'un appel.
- Pas de parenthèses inutiles autour des conditions : `si age >= 18:` plutôt que `si (age >= 18):`.
- Préférez `f"…"` à la concaténation avec `+`.

```nck
classe Commande:
    client: texte
    lignes: liste<reel> = []

    fonction total() -> reel:
        retourner soi.lignes.somme()
    fin

    fonction texte() -> texte:
        retourner f"Commande de {soi.client} : {soi.total()} F"
    fin
fin

variable c = Commande("Awa", [450.0, 1200.0])
si c.total() > 1000: ecrire("livraison offerte")
ecrire(c)
```

## Types

- Annotez les **paramètres** (obligatoire), les **retours** (obligatoire si ≠ `rien`) et les variables dont le type
  n'est pas évident (`variable notes: liste<reel> = []`).
- Laissez l'inférence faire le reste : `variable total = 0.0`.
- Utilisez `T?` plutôt que des valeurs sentinelles (`-1`, `""`) pour « absent ».
- Réservez `quelconque` aux frontières (JSON, `...args`) et convertissez tout de suite.

## Structure d'un programme

1. `importer` en tête du fichier ;
2. constantes ;
3. énumérations et classes ;
4. fonctions ;
5. code principal en bas (ou une fonction `principal()` appelée à la fin).

```nck
constante VERSION = "1.0"

enumeration Mode: LECTURE, ECRITURE fin

classe Options:
    mode: Mode = Mode.LECTURE
    verbeux: booleen = faux
fin

fonction principal():
    variable options = Options()
    si options.verbeux: ecrire("démarrage", VERSION)
    ecrire("mode :", options.mode.nom)
fin

principal()
```

## Vérifier avant d'exécuter

- `nck verifier fichier.nck` dans vos scripts et votre CI : syntaxe et types sans effet de bord.
- Dans VS Code, les erreurs apparaissent pendant la frappe ([extension](../EDITEUR.md)).
- Ajoutez des `verifier(condition, "message")` aux endroits critiques : ils documentent et protègent.
