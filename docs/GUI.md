# Interfaces graphiques

Le module natif `gui` apporte un premier ensemble de fenêtres et de contrôles basé sur
**Tkinter** (version 0.14 en développement). Il n'y a pas de dépendance NCK à installer.
L'exécutable ou Python doit toutefois inclure Tkinter, et l'application doit être lancée
dans une session de bureau graphique.

Importer `gui` et exécuter `nck verifier` ne crée aucune fenêtre : le module graphique
est chargé seulement lorsqu'une fonction graphique est appelée. Les exemples de cette
page sont donc vérifiés par la documentation, mais ne sont pas lancés automatiquement
sans écran graphique.

## Première fenêtre

```nck
// nécessite un environnement graphique
importer "gui" comme gui

variable fenetre = gui.fenetre("Bonjour NCK", 420, 220)
variable nom = gui.champ(fenetre, "Awa")
variable reponse = gui.etiquette(fenetre, "Bonjour !")

gui.bouton(fenetre, "Saluer", fonction():
    gui.definir_texte(reponse, "Bonjour " + texte(gui.valeur(nom)) + " !")
fin)

gui.demarrer(fenetre)
```

Enregistrez ce code dans `exemples/gui/bonjour_gui.nck`, puis lancez-le depuis une
session graphique avec `nck exemples/gui/bonjour_gui.nck`. `demarrer` lance la boucle
d'événements : la ligne suivante ne s'exécute qu'à la fermeture de la fenêtre.

## Fonctions disponibles

| Fonction | Rôle |
|---|---|
| `fenetre(titre, largeur = 640, hauteur = 480)` | Crée la fenêtre principale et son conteneur. |
| `etiquette(parent, texte)` | Affiche un texte. |
| `bouton(parent, texte, action)` | Appelle une fonction sans argument au clic. |
| `champ(parent, valeur = "")` | Champ de saisie sur une ligne. |
| `case(parent, texte, valeur = faux)` | Case à cocher. |
| `liste_deroulante(parent, options, valeur = nul)` | Liste en lecture seule ; sélectionne la première option par défaut. |
| `zone_texte(parent, contenu = "")` | Zone de texte multiligne avec barre de défilement. |
| `image(parent, chemin)` | Affiche une image PNG ou GIF locale. |
| `ligne(parent)` / `colonne(parent)` | Conteneur horizontal / vertical. Les contrôles y sont rangés automatiquement. |
| `grille(parent)` / `placer(grille, element, ligne, colonne)` | Conteneur de grille ; les indices commencent à zéro. |
| `valeur(element)` / `definir_valeur(element, valeur)` | Lit ou modifie un champ, une case, une liste ou une zone de texte. |
| `definir_texte(element, texte)` | Change le texte d'une étiquette ou d'un bouton. |
| `message(titre, texte)` / `question(titre, texte)` | Boîte informative / question Oui-Non. |
| `choisir_fichier(titre = "Choisir un fichier")` | Sélecteur de fichier ; retourne `texte?` (`nul` si annulé). |
| `fermer(fenetre)` / `demarrer(fenetre)` | Ferme ou démarre la boucle d'événements. |

Les fonctions de contrôle acceptent comme `parent` une fenêtre, un conteneur ou un autre
widget créé par `gui`. Les widgets sont pour le moment des poignées opaques de type
`quelconque` : utilisez les fonctions de `gui` plutôt que d'accéder directement à des
attributs Tkinter. Les arguments texte, booléens, listes et callbacks sont vérifiés par
le vérificateur statique de NCK ; les types de classes de widgets et l'autocomplétion de
leurs propriétés seront complétés pendant la v0.14.

### Disposition automatique et grille

Les contrôles ajoutés à la fenêtre ou à une `ligne` / `colonne` sont disposés
automatiquement. Pour une disposition précise, créez une grille et placez-y chaque
élément. N'utilisez pas le placement automatique et `placer` sur un même conteneur.

```nck
// nécessite un environnement graphique
importer "gui" comme gui
variable app = gui.fenetre("Grille", 360, 180)
variable table = gui.grille(app)
variable titre = gui.etiquette(table, "Nom")
variable saisie = gui.champ(table, "Awa")
gui.placer(table, titre, 0, 0)
gui.placer(table, saisie, 0, 1)
gui.demarrer(app)
```

## Limites actuelles

- Une fenêtre et les contrôles utilisent le thème natif Tkinter ; les styles avancés ne
  sont pas encore exposés.
- Les valeurs dynamiques se lisent et s'écrivent avec `valeur` et `definir_valeur` ;
  elles ne sont pas encore des propriétés (`champ.valeur`).
- Les images acceptées sont celles prises en charge par `tkinter.PhotoImage` (PNG/GIF).
- En environnement Linux minimal, installez le paquet Tkinter de la distribution Python
  si nécessaire. Sans affichage (par exemple un serveur sans session graphique), les
  fonctions de création de fenêtre retournent une erreur NCK claire.
