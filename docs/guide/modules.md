# Modules

Un programme peut être découpé en plusieurs fichiers `.nck`. Les chemins sont **relatifs au fichier qui importe**.

## Trois façons d'importer

```nck title="outils/maths.nck"
constante PI = 3.14159
fonction carre(x: reel) -> reel: retourner x * x
classe Cercle:
    rayon: reel
    fonction aire() -> reel: retourner PI * carre(soi.rayon)
fin
```

```nck title="principal.nck"
importer "outils/maths.nck"                  // accessible via le nom du fichier
ecrire(maths.carre(2.0), maths.PI)

importer "outils/maths.nck" comme m          // avec un alias
ecrire(m.Cercle(1.0).aire())

depuis "outils/maths.nck" importer carre, Cercle   // noms importés directement
variable c: Cercle = Cercle(2.0)             // une classe importée sert de type
ecrire(carre(3.0), c.aire())
```

## Règles

- Tout ce qui est déclaré au niveau principal d'un module (fonctions, classes, énumérations, constantes, variables) est accessible.
- Un module n'est exécuté **qu'une seule fois**, même importé plusieurs fois ; son état est partagé.
- `importer` se place au niveau principal du fichier (de préférence en tête) ; les imports circulaires sont refusés.
- Les variables d'un module ne se modifient pas de l'extérieur (`m.compteur = 0` est une erreur) : passez par une fonction du module.
- `depuis … importer x` copie la **valeur** de `x` au moment de l'import.
- Les noms de classes doivent être uniques dans tout le programme.

## Organiser un projet

```text
mon_projet/
├── principal.nck          # point d'entrée : nck principal.nck
├── modeles/
│   ├── personne.nck
│   └── commande.nck
├── services/
│   └── stockage.nck
└── tests/
    └── test_commande.nck
```

```nck title="modeles/personne.nck"
classe Personne:
    nom: texte
fin
```

```nck title="services/stockage.nck"
depuis "../modeles/personne.nck" importer Personne

fonction sauvegarder(p: Personne, chemin: texte):
    ecrire_fichier(chemin, vers_json(p))
fin
```

```nck title="principal.nck"
depuis "modeles/personne.nck" importer Personne
importer "services/stockage.nck" comme stockage

stockage.sauvegarder(Personne("Awa"), "awa.json")
ecrire(lire_fichier("awa.json"))
supprimer_fichier("awa.json")
```

!!! note "Paquets"
    Les bibliothèques partagées s’installent avec `nck installer nom` et s’importent
    avec `importer "nom"`. Consultez le [guide des paquets](../PAQUETS.md) pour configurer
    un index, déclarer des dépendances et utiliser le fichier de verrouillage.
