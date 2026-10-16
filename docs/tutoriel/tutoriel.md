# Tutoriel en 30 minutes

Ce tutoriel construit pas à pas un petit **gestionnaire de tâches** et présente au passage l'essentiel du langage.
Chaque extrait peut être copié dans un fichier `.nck` et exécuté avec `nck fichier.nck`.

## 1. Valeurs et types

```nck
variable titre = "Acheter du pain"      // texte
variable priorite: entier = 2           // entier
variable duree = 1.5                    // reel (heures)
variable faite = faux                   // booleen
constante MAX_TACHES = 100              // ne change jamais

ecrire(titre, priorite, duree, faite)   // Acheter du pain 2 1.5 faux
ecrire(type_de(duree))                  // reel
```

NCK a cinq types de base : `entier`, `reel`, `texte`, `booleen` et `rien`.
Un `entier` se range dans un `reel` tout seul ; l'inverse demande une conversion : `entier(3.9)` → `3`.

## 2. Conditions

```nck
variable priorite = 2

si priorite >= 3:
    ecrire("urgent")
sinon si priorite == 2:
    ecrire("normal")
sinon:
    ecrire("quand vous pouvez")
fin

// en une ligne, pour choisir une valeur
variable etiquette = si priorite >= 3 alors "!!!" sinon ""
```

## 3. Listes et boucles

```nck
variable taches: liste<texte> = ["pain", "lait"]
taches.ajouter("œufs")

pour t dans taches:
    ecrire("-", t)
fin

pour i, t dans taches:              // avec l'indice
    ecrire(i + 1, t)
fin

ecrire(taches.longueur(), taches.contient("lait"))   // 3 vrai
```

Les boucles `tantque` et les plages `1..10` existent aussi : voir [Boucles](../guide/boucles.md).

## 4. Fonctions

```nck
fonction formater_tache(titre: texte, faite: booleen = faux) -> texte:
    variable coche = si faite alors "[x]" sinon "[ ]"
    retourner f"{coche} {titre}"
fin

ecrire(formater_tache("pain"))             // [ ] pain
ecrire(formater_tache("lait", vrai))       // [x] lait
```

Les paramètres sont toujours typés (les arguments nommés sont réservés à la création d'objets) ; `-> texte` annonce le type de retour (absent = `rien`).
Le vérificateur s'assure que **tous** les chemins retournent bien un `texte`.

## 5. Une classe pour les tâches

```nck
classe Tache:
    titre: texte
    priorite: entier = 1
    faite: booleen = faux

    fonction valider():                     // appelée automatiquement à la création
        verifier(soi.priorite >= 1 et soi.priorite <= 3, "priorité entre 1 et 3")
    fin

    fonction terminer():
        soi.faite = vrai
    fin

    fonction texte() -> texte:              // personnalise l'affichage
        variable coche = si soi.faite alors "x" sinon " "
        retourner f"[{coche}] {soi.titre} (p{soi.priorite})"
    fin
fin

variable t = Tache("Acheter du pain", 2)    // constructeur automatique
t.terminer()
ecrire(t)                                   // [x] Acheter du pain (p2)
```

Pas de constructeur à écrire : les champs **sont** le constructeur (arguments dans l'ordre ou nommés : `Tache(titre="lait")`).

## 6. Une liste de tâches

```nck
classe Tache:
    titre: texte
    priorite: entier = 1
    faite: booleen = faux
fin

classe ListeTaches:
    taches: liste<Tache> = []

    fonction ajouter(titre: texte, priorite: entier = 1):
        soi.taches.ajouter(Tache(titre, priorite))
    fin

    fonction restantes() -> liste<Tache>:
        retourner soi.taches.filtrer(fonction(t): non t.faite)
    fin

    fonction urgentes() -> liste<texte>:
        retourner soi.restantes().filtrer(fonction(t): t.priorite == 3).appliquer(fonction(t): t.titre)
    fin
fin

variable liste = ListeTaches()
liste.ajouter("pain")
liste.ajouter("impôts", 3)
liste.ajouter("appeler Issa", 3)
liste.taches[0].faite = vrai

ecrire(liste.restantes().longueur())    // 2
ecrire(liste.urgentes())                // [impôts, appeler Issa]
```

`fonction(t): non t.faite` est une **fonction anonyme** ; comme `filtrer` sait qu'il reçoit des `Tache`, le type de `t` est déduit.

## 7. Gérer les erreurs

```nck
classe Tache:
    titre: texte
    priorite: entier = 1

    fonction valider():
        verifier(soi.priorite >= 1 et soi.priorite <= 3, "priorité entre 1 et 3")
    fin
fin

essayer:
    variable t = Tache("test", 7)
attraper e:
    ecrire("Impossible :", e.message)       // Impossible : priorité entre 1 et 3
fin

essayer:
    variable n = entier("abc")
attraper e:
    ecrire(e.message)
enfin:
    ecrire("fin de l'essai")
fin
```

Vos propres erreurs : `classe ErreurTache herite Erreur: … fin` puis `lever ErreurTache("…")`. Voir [Gestion des erreurs](../guide/erreurs.md).

## 8. Sauvegarder en JSON

```nck
classe Tache:
    titre: texte
    priorite: entier = 1
    faite: booleen = faux
fin

variable taches = [Tache("pain"), Tache("impôts", 3, vrai)]

ecrire_fichier("taches.json", vers_json(taches, vrai))

variable donnees = depuis_json(lire_fichier("taches.json"))
pour d dans donnees:
    ecrire(d["titre"], d["priorite"])
fin
supprimer_fichier("taches.json")
```

## 9. Découper en modules

```nck title="taches.nck"
classe Tache:
    titre: texte
    priorite: entier = 1
fin

fonction creer(titre: texte) -> Tache: retourner Tache(titre)
```

```nck title="principal.nck"
importer "taches.nck"
variable t = taches.creer("pain")
ecrire(t.titre)

depuis "taches.nck" importer Tache
variable t2 = Tache("lait", 2)
```

## 10. Énumérations et `selon`

```nck
enumeration Etat: A_FAIRE, EN_COURS, FAITE fin

fonction symbole(e: Etat) -> texte:
    selon e:
        cas Etat.A_FAIRE: retourner " "
        cas Etat.EN_COURS: retourner "~"
        cas Etat.FAITE: retourner "x"
    fin
fin

ecrire(symbole(Etat.EN_COURS))      // ~
ecrire(Etat.valeurs)                // [Etat.A_FAIRE, Etat.EN_COURS, Etat.FAITE]
```

Si vous oubliez un cas, le vérificateur vous le dit avant l'exécution.

## Pour aller plus loin

- [Guide du langage](../guide/index.md) : chaque notion en détail.
- [Fonctions natives](../NATIFS.md) : tout ce qui est disponible sans rien importer.
- [Exemples](../exemples/index.md) : programmes complets fournis avec NCK.
