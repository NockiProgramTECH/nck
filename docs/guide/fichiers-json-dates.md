# Fichiers, JSON et dates

## Lire et écrire des fichiers

```nck
ecrire_fichier("notes.txt", "première ligne\n")
ajouter_fichier("notes.txt", "deuxième ligne\n")

ecrire(lire_fichier("notes.txt"))          // tout le contenu
pour i, ligne dans lire_lignes("notes.txt"):
    ecrire(i + 1, ligne)
fin

ecrire(fichier_existe("notes.txt"))        // vrai
supprimer_fichier("notes.txt")
```

Les fichiers sont lus et écrits en UTF-8. Les erreurs (fichier introuvable, accès refusé) sont attrapables :

```nck
essayer:
    ecrire(lire_fichier("inexistant.txt"))
attraper e:
    ecrire("Impossible :", e.message)
fin
```

## Dossiers et chemins

```nck
creer_dossier("donnees/archives")
ecrire(dossier_existe("donnees"))
ecrire(lister_dossier("donnees"))                    // [archives]
ecrire(joindre_chemin("donnees", "archives", "a.txt")) // bon séparateur selon le système
ecrire(dossier_courant())
```

## JSON

```nck
classe Produit:
    nom: texte
    prix: reel
    tags: liste<texte> = []
fin

variable panier = [Produit("riz", 450.0, ["base"]), Produit("huile", 1200.0)]

variable json = vers_json(panier, vrai)             // joli = indenté
ecrire(json)
ecrire_fichier("panier.json", json)

variable donnees = depuis_json(lire_fichier("panier.json"))   // quelconque
variable total = 0.0
pour p dans donnees:
    total += reel(p["prix"])
fin
ecrire("total :", total)                            // total : 1650.0
supprimer_fichier("panier.json")
```

- `vers_json` accepte listes, dicos, objets (leurs champs), nombres, textes, booléens, `nul`.
- `depuis_json` retourne un `quelconque` : indexez avec `["cle"]` / `[i]`, puis convertissez (`texte(...)`, `entier(...)`, `reel(...)`).
- Un JSON invalide lève une erreur attrapable.

## Dates et heures

```nck
variable t = maintenant()                       // secondes depuis 1970 (reel)
ecrire(formater_date())                         // 16/10/2026 14:05:09  (JJ/MM/AAAA hh:mm:ss)
ecrire(formater_date("AAAA-MM-JJ"))             // 2026-10-16
ecrire(formater_date("JJ/MM/AAAA", t + 86400))  // demain

variable d = date()                             // dico<texte, entier>
ecrire(d["annee"], d["mois"], d["jour"], d["jour_semaine"])   // jour_semaine : 1 = lundi

variable noel = creer_date(2026, 12, 25)
variable jours = plancher((noel - t) / 86400)
ecrire(f"encore {jours} jours avant Noël")
```

## Chronométrer et attendre

```nck
variable debut = horloge()
variable s = 0
pour i dans 100000: s += i
ecrire(f"{s} calculé en {arrondir(horloge() - debut, 3)} s")
attendre(0.1)                                   // pause de 0,1 seconde
```

## Arguments et environnement

```nck title="salut.nck"
variable args = arguments()                     // nck salut.nck Awa 3
si args.longueur() < 2:
    ecrire_erreur("usage : nck salut.nck NOM NOMBRE")
    quitter(1)
fin
pour i dans entier(args[1]):
    ecrire("Bonjour", args[0])
fin
ecrire(variable_env("HOME", "?"))
```
