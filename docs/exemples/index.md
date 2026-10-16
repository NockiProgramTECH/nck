# Exemples

Les programmes ci-dessous sont fournis avec NCK (dossier `exemples/` de l'installation, ou
[sur GitHub](https://github.com/NockiProgramTECH/nck/tree/main/exemples)). Exécutez-les avec `nck exemples/nom.nck`.

| Fichier | Ce qu'il montre |
|---|---|
| `bonjour.nck` | le plus petit programme : variable, condition, `ecrire` |
| `types.nck` | types de base, conversions, inférence |
| `fonctions.nck` | définition, retour, fonctions comme valeurs |
| `boucles.nck` | `pour`, `tantque`, `arreter`, `continuer` |
| `dictionnaires.nck` | `dico<K, V>`, accès, parcours, `obtenir` |
| `classes.nck` | classes, `valider`, héritage, `texte()` |
| `poo_avancee.nck` | `parent`, `statique`, constantes, privé, abstraite, opérateurs, décorateurs, `...args` |
| `erreurs.nck` | `essayer`/`attraper`/`enfin`, `lever`, erreurs personnalisées |
| `fonctions_anonymes.nck` | lambdas, `appliquer`/`filtrer`/`reduire`, `T?`, `??`, plages |
| `confort.nck`, `confort2.nck` | `f"…"`, paramètres par défaut, `selon`, énumérations, notation méthode, affectation multiple |
| `stdlib.nck` | fichiers, JSON, dates, arguments |
| `modules/principal.nck` | `importer`, `comme`, `depuis … importer` |
| `devine.nck` | petit jeu interactif (`lire`, `aleatoire`) |
| `benchmark.nck` | mesure de performance (Fibonacci récursif) |

## Petits programmes complets

### Table de multiplication

```nck
pour i dans 1..11:
    variable ligne = (1..11).appliquer(fonction(j): texte(i * j).remplir_gauche(4, " ")).joindre("")
    ecrire(ligne)
fin
```

### FizzBuzz

```nck
pour n dans 1..16:
    variable mot = ""
    si n % 3 == 0: mot += "Fizz"
    si n % 5 == 0: mot += "Buzz"
    ecrire(si mot == "" alors texte(n) sinon mot)
fin
```

### Statistiques sur une liste

```nck
variable notes = [12.5, 15, 9, 17.5, 11]
variable moyenne = notes.somme() / notes.longueur()
variable ecarts = notes.appliquer(fonction(n): puissance(n - moyenne, 2))
variable ecart_type = racine(ecarts.somme() / notes.longueur())
ecrire(f"moyenne {arrondir(moyenne, 2)}, écart-type {arrondir(ecart_type, 2)}")
ecrire("au-dessus de la moyenne :", notes.filtrer(fonction(n): n > moyenne))
```

### Inventaire avec classes et JSON

```nck
classe Article:
    nom: texte
    quantite: entier
    prix: reel

    fonction valider():
        verifier(soi.quantite >= 0, "quantité négative")
    fin

    fonction valeur() -> reel: retourner soi.quantite * soi.prix
fin

classe Inventaire:
    articles: liste<Article> = []

    fonction ajouter(a: Article): soi.articles.ajouter(a)

    fonction valeur_totale() -> reel:
        retourner soi.articles.reduire(fonction(acc, a): acc + a.valeur(), 0.0)
    fin

    fonction en_rupture() -> liste<texte>:
        retourner soi.articles.filtrer(fonction(a): a.quantite == 0).appliquer(fonction(a): a.nom)
    fin

    fonction sauvegarder(chemin: texte): ecrire_fichier(chemin, vers_json(soi.articles, vrai))
fin

variable inv = Inventaire()
inv.ajouter(Article("riz 25kg", 10, 18000.0))
inv.ajouter(Article("huile 5L", 0, 7500.0))
inv.ajouter(Article("sucre 1kg", 42, 650.0))

ecrire("valeur totale :", inv.valeur_totale())
ecrire("en rupture :", inv.en_rupture())
inv.sauvegarder("inventaire.json")
ecrire(lire_fichier("inventaire.json"))
supprimer_fichier("inventaire.json")
```

### Compter les mots d'un fichier

```nck
ecrire_fichier("texte.txt", "le chat dort. Le chien court, le chat regarde.")

variable compte: dico<texte, entier> = {}
pour brut dans lire_fichier("texte.txt").minuscule().decouper(" "):
    variable mot = brut.remplacer(".", "").remplacer(",", "")
    si mot == "": continuer
    compte[mot] = compte.obtenir(mot, 0) + 1
fin

pour mot, n dans compte:
    si n > 1: ecrire(mot, n)
fin
supprimer_fichier("texte.txt")
```

### Machine à états avec énumération

```nck
enumeration Feu: VERT, ORANGE, ROUGE fin

fonction suivant(f: Feu) -> Feu:
    selon f:
        cas Feu.VERT: retourner Feu.ORANGE
        cas Feu.ORANGE: retourner Feu.ROUGE
        cas Feu.ROUGE: retourner Feu.VERT
    fin
fin

variable f = Feu.VERT
pour i dans 5:
    ecrire(f.nom)
    f = suivant(f)
fin
```

### Jeu : devine le nombre

```nck title="devine.nck"
constante secret = aleatoire(1, 100)
variable essais = 0
tantque vrai:
    variable saisie = lire("Votre nombre (1-100) ? ")
    si non est_entier(saisie):
        ecrire("Entrez un nombre entier.")
        continuer
    fin
    essais += 1
    variable n = entier(saisie)
    si n < secret: ecrire("plus grand")
    sinon si n > secret: ecrire("plus petit")
    sinon:
        ecrire(f"Bravo, trouvé en {essais} essai(s) !")
        arreter
    fin
fin
```
