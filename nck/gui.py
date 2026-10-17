"""Module natif `gui` : interface graphique portable fondée sur Tkinter.

Tkinter n'est importé qu'à l'appel d'une fonction graphique. Vérifier un programme
qui importe `gui` reste donc possible dans un terminal sans serveur graphique.
Les widgets sont des poignées opaques : on les manipule avec les fonctions de ce
module, sans exposer les objets Tkinter au langage.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from .erreurs import ErreurExecution
from .types_nck import BOOLEEN, ENTIER, QUELCONQUE, RIEN, TEXTE, Type, TypeFonction, liste_de, optionnel_de


@dataclass(frozen=True)
class ExportGUI:
    """Signature statique et implémentation d'un nom exporté par `gui`."""

    type: Type
    signature: str
    description: str
    fonction: Callable


@dataclass
class FenetreGUI:
    racine: object
    contenu: object


@dataclass
class ConteneurGUI:
    racine: object
    widget: object
    mode: str


@dataclass
class WidgetGUI:
    racine: object
    widget: object
    genre: str
    variable: object | None = None
    options: tuple[str, ...] = ()
    image: object | None = None
    layout: object | None = None


def _tk_modules():
    """Charge Tkinter à la demande, jamais lors de l'import du module NCK."""
    try:
        import tkinter as tk
        from tkinter import filedialog, messagebox, ttk
    except ImportError:
        raise ErreurExecution(
            "le module 'gui' nécessite Tkinter, qui n'est pas disponible dans cette installation de Python"
        ) from None
    return tk, ttk, messagebox, filedialog


def _avec_erreur(nom: str, action: Callable):
    try:
        return action()
    except ErreurExecution:
        raise
    except Exception as exc:  # noqa: BLE001 — les erreurs Tk sont traduites en erreurs NCK.
        raise ErreurExecution(f"gui.{nom} : {exc}") from None


def _est_entier(valeur: object) -> bool:
    return isinstance(valeur, int) and not isinstance(valeur, bool)


def _exiger_texte(valeur: object, fonction: str) -> str:
    if not isinstance(valeur, str):
        raise ErreurExecution(f"gui.{fonction} attend un texte")
    return valeur


def _parent(parent: object, fonction: str):
    if isinstance(parent, FenetreGUI):
        return parent.racine, parent.contenu, "colonne"
    if isinstance(parent, ConteneurGUI):
        return parent.racine, parent.widget, parent.mode
    if isinstance(parent, WidgetGUI):
        return parent.racine, parent.widget, "colonne"
    raise ErreurExecution(f"gui.{fonction} attend une fenêtre ou un widget parent créé par gui")


def _organiser(widget: object, mode_parent: str, **options) -> None:
    # Une grille attend un appel explicite à gui.placer ; les autres conteneurs
    # disposent automatiquement leurs enfants de haut en bas ou de gauche à droite.
    if mode_parent == "grille":
        return
    options.setdefault("side", "left" if mode_parent == "ligne" else "top")
    options.setdefault("fill", "y" if mode_parent == "ligne" else "x")
    widget.pack(**options)


def _racine_fenetre(fenetre: object, fonction: str):
    if not isinstance(fenetre, FenetreGUI):
        raise ErreurExecution(f"gui.{fonction} attend une fenêtre créée par gui.fenetre")
    return fenetre.racine


def _fenetre(titre: str, largeur: int = 640, hauteur: int = 480) -> FenetreGUI:
    titre = _exiger_texte(titre, "fenetre")
    if not _est_entier(largeur) or not _est_entier(hauteur) or largeur < 1 or hauteur < 1:
        raise ErreurExecution("gui.fenetre attend une largeur et une hauteur entières positives")

    def creer():
        tk, ttk, _, _ = _tk_modules()
        racine = tk.Tk()
        racine.title(titre)
        racine.geometry(f"{largeur}x{hauteur}")
        contenu = ttk.Frame(racine, padding=8)
        contenu.pack(fill="both", expand=True)
        return FenetreGUI(racine, contenu)

    return _avec_erreur("fenetre", creer)


def _etiquette(parent: object, texte: str) -> WidgetGUI:
    texte = _exiger_texte(texte, "etiquette")
    racine, conteneur, mode_parent = _parent(parent, "etiquette")

    def creer():
        _, ttk, _, _ = _tk_modules()
        widget = ttk.Label(conteneur, text=texte)
        _organiser(widget, mode_parent, fill="x", padx=4, pady=3)
        return WidgetGUI(racine, widget, "etiquette")

    return _avec_erreur("etiquette", creer)


def _bouton(parent: object, texte: str, action: object) -> WidgetGUI:
    texte = _exiger_texte(texte, "bouton")
    racine, conteneur, mode_parent = _parent(parent, "bouton")
    if not callable(action):
        raise ErreurExecution("gui.bouton attend une fonction sans argument pour l'action")

    def cliquer():
        try:
            action()
        except Exception as exc:  # noqa: BLE001 — la callback s'exécute dans la boucle Tk.
            try:
                _, _, messagebox, _ = _tk_modules()
                messagebox.showerror("Erreur NCK", str(exc), parent=racine)
            except Exception:  # noqa: BLE001 — la fenêtre peut déjà être fermée.
                import sys
                print(f"Erreur dans l'action du bouton : {exc}", file=sys.stderr)

    def creer():
        _, ttk, _, _ = _tk_modules()
        widget = ttk.Button(conteneur, text=texte, command=cliquer)
        _organiser(widget, mode_parent, fill="x", padx=4, pady=3)
        return WidgetGUI(racine, widget, "bouton")

    return _avec_erreur("bouton", creer)


def _champ(parent: object, valeur: str = "") -> WidgetGUI:
    valeur = _exiger_texte(valeur, "champ")
    racine, conteneur, mode_parent = _parent(parent, "champ")

    def creer():
        tk, ttk, _, _ = _tk_modules()
        variable = tk.StringVar(master=racine, value=valeur)
        widget = ttk.Entry(conteneur, textvariable=variable)
        _organiser(widget, mode_parent, fill="x", padx=4, pady=3)
        return WidgetGUI(racine, widget, "champ", variable)

    return _avec_erreur("champ", creer)


def _case(parent: object, texte: str, valeur: bool = False) -> WidgetGUI:
    texte = _exiger_texte(texte, "case")
    if not isinstance(valeur, bool):
        raise ErreurExecution("gui.case attend un booleen comme valeur initiale")
    racine, conteneur, mode_parent = _parent(parent, "case")

    def creer():
        tk, ttk, _, _ = _tk_modules()
        variable = tk.BooleanVar(master=racine, value=valeur)
        widget = ttk.Checkbutton(conteneur, text=texte, variable=variable)
        _organiser(widget, mode_parent, anchor="w", padx=4, pady=3)
        return WidgetGUI(racine, widget, "case", variable)

    return _avec_erreur("case", creer)


def _liste_deroulante(parent: object, options: list[str], valeur: str | None = None) -> WidgetGUI:
    if not isinstance(options, list) or any(not isinstance(option, str) for option in options):
        raise ErreurExecution("gui.liste_deroulante attend une liste de textes")
    if valeur is not None and not isinstance(valeur, str):
        raise ErreurExecution("gui.liste_deroulante attend un texte ou nul comme valeur initiale")
    if valeur is not None and valeur not in options:
        raise ErreurExecution("la valeur initiale de gui.liste_deroulante doit figurer dans les options")
    racine, conteneur, mode_parent = _parent(parent, "liste_deroulante")
    initiale = valeur if valeur is not None else (options[0] if options else "")

    def creer():
        tk, ttk, _, _ = _tk_modules()
        variable = tk.StringVar(master=racine, value=initiale)
        widget = ttk.Combobox(conteneur, values=options, textvariable=variable, state="readonly")
        _organiser(widget, mode_parent, fill="x", padx=4, pady=3)
        return WidgetGUI(racine, widget, "liste_deroulante", variable, tuple(options))

    return _avec_erreur("liste_deroulante", creer)


def _zone_texte(parent: object, contenu: str = "") -> WidgetGUI:
    contenu = _exiger_texte(contenu, "zone_texte")
    racine, conteneur, mode_parent = _parent(parent, "zone_texte")

    def creer():
        tk, ttk, _, _ = _tk_modules()
        cadre = ttk.Frame(conteneur)
        _organiser(cadre, mode_parent, fill="both", expand=True, padx=4, pady=3)
        widget = tk.Text(cadre, height=6, wrap="word")
        barre = ttk.Scrollbar(cadre, orient="vertical", command=widget.yview)
        widget.configure(yscrollcommand=barre.set)
        widget.pack(side="left", fill="both", expand=True)
        barre.pack(side="right", fill="y")
        if contenu:
            widget.insert("1.0", contenu)
        return WidgetGUI(racine, widget, "zone_texte", layout=cadre)

    return _avec_erreur("zone_texte", creer)


def _image(parent: object, chemin: str) -> WidgetGUI:
    chemin = _exiger_texte(chemin, "image")
    racine, conteneur, mode_parent = _parent(parent, "image")

    def creer():
        tk, ttk, _, _ = _tk_modules()
        photo = tk.PhotoImage(master=racine, file=chemin)
        widget = ttk.Label(conteneur, image=photo)
        widget.image = photo  # garde une référence, sinon Tkinter détruit l'image
        _organiser(widget, mode_parent, padx=4, pady=3)
        return WidgetGUI(racine, widget, "image", image=photo)

    return _avec_erreur("image", creer)


def _conteneur(parent: object, mode: str) -> ConteneurGUI:
    racine, parent_widget, mode_parent = _parent(parent, mode)

    def creer():
        _, ttk, _, _ = _tk_modules()
        cadre = ttk.Frame(parent_widget, padding=4)
        _organiser(cadre, mode_parent, fill="both", expand=True, padx=2, pady=2)
        return ConteneurGUI(racine, cadre, mode)

    return _avec_erreur(mode, creer)


def _grille(parent: object) -> ConteneurGUI:
    return _conteneur(parent, "grille")


def _ligne(parent: object) -> ConteneurGUI:
    return _conteneur(parent, "ligne")


def _colonne(parent: object) -> ConteneurGUI:
    return _conteneur(parent, "colonne")


def _placer(conteneur: object, element: object, ligne: int, colonne: int) -> None:
    if not isinstance(conteneur, ConteneurGUI) or conteneur.mode != "grille":
        raise ErreurExecution("gui.placer attend un conteneur créé par gui.grille")
    if not isinstance(element, (WidgetGUI, ConteneurGUI)):
        raise ErreurExecution("gui.placer attend un élément créé par gui ou un conteneur")
    if not _est_entier(ligne) or not _est_entier(colonne) or ligne < 0 or colonne < 0:
        raise ErreurExecution("gui.placer attend des indices de ligne et de colonne entiers positifs ou nuls")
    cible = (element.layout or element.widget) if isinstance(element, WidgetGUI) else element.widget

    def placer():
        cible.grid(row=ligne, column=colonne, sticky="nsew", padx=4, pady=3)

    _avec_erreur("placer", placer)


def _valeur(element: object):
    if not isinstance(element, WidgetGUI):
        raise ErreurExecution("gui.valeur attend un contrôle créé par le module gui")

    def lire():
        if element.genre in ("champ", "case", "liste_deroulante") and element.variable is not None:
            return element.variable.get()
        if element.genre == "zone_texte":
            return element.widget.get("1.0", "end-1c")
        raise ErreurExecution(f"gui.valeur ne peut pas lire un élément de type '{element.genre}'")

    return _avec_erreur("valeur", lire)


def _definir_valeur(element: object, valeur: object) -> None:
    if not isinstance(element, WidgetGUI):
        raise ErreurExecution("gui.definir_valeur attend un contrôle créé par le module gui")

    def definir():
        if element.genre in ("champ", "liste_deroulante"):
            if not isinstance(valeur, str):
                raise ErreurExecution(f"gui.definir_valeur attend un texte pour le contrôle '{element.genre}'")
            if element.genre == "liste_deroulante" and valeur not in element.options:
                raise ErreurExecution("la valeur doit figurer dans les options de la liste déroulante")
            element.variable.set(valeur)
        elif element.genre == "case":
            if not isinstance(valeur, bool):
                raise ErreurExecution("gui.definir_valeur attend un booleen pour une case à cocher")
            element.variable.set(valeur)
        elif element.genre == "zone_texte":
            if not isinstance(valeur, str):
                raise ErreurExecution("gui.definir_valeur attend un texte pour la zone de texte")
            element.widget.delete("1.0", "end")
            element.widget.insert("1.0", valeur)
        else:
            raise ErreurExecution(f"gui.definir_valeur ne peut pas modifier un élément de type '{element.genre}'")

    _avec_erreur("definir_valeur", definir)


def _definir_texte(element: object, texte: str) -> None:
    texte = _exiger_texte(texte, "definir_texte")
    if not isinstance(element, WidgetGUI) or element.genre not in ("etiquette", "bouton"):
        raise ErreurExecution("gui.definir_texte attend une étiquette ou un bouton créé par gui")
    _avec_erreur("definir_texte", lambda: element.widget.configure(text=texte))


def _demarrer(fenetre: object) -> None:
    racine = _racine_fenetre(fenetre, "demarrer")
    _avec_erreur("demarrer", racine.mainloop)


def _fermer(fenetre: object) -> None:
    racine = _racine_fenetre(fenetre, "fermer")
    _avec_erreur("fermer", racine.destroy)


def _message(titre: str, texte: str) -> None:
    titre = _exiger_texte(titre, "message")
    texte = _exiger_texte(texte, "message")

    def afficher():
        _, _, messagebox, _ = _tk_modules()
        messagebox.showinfo(titre, texte)

    _avec_erreur("message", afficher)


def _question(titre: str, texte: str) -> bool:
    titre = _exiger_texte(titre, "question")
    texte = _exiger_texte(texte, "question")

    def demander():
        _, _, messagebox, _ = _tk_modules()
        return bool(messagebox.askyesno(titre, texte))

    return _avec_erreur("question", demander)


def _choisir_fichier(titre: str = "Choisir un fichier") -> str | None:
    titre = _exiger_texte(titre, "choisir_fichier")

    def choisir():
        _, _, _, filedialog = _tk_modules()
        chemin = filedialog.askopenfilename(title=titre)
        return chemin or None

    return _avec_erreur("choisir_fichier", choisir)


def _type_fonction(params: tuple[Type, ...], retour: Type, obligatoires: int | None = None) -> TypeFonction:
    mini = len(params) if obligatoires is None else obligatoires
    return TypeFonction("fonction", (), params, retour, mini)


_ACTION = _type_fonction((), RIEN)


def _export(type_: Type, signature: str, description: str, fonction: Callable) -> ExportGUI:
    return ExportGUI(type_, signature, description, fonction)


EXPORTS: dict[str, ExportGUI] = {
    "fenetre": _export(_type_fonction((TEXTE, ENTIER, ENTIER), QUELCONQUE, 1),
                        "fenetre(titre: texte, largeur: entier = 640, hauteur: entier = 480) -> quelconque",
                        "Crée une fenêtre et son conteneur principal.", _fenetre),
    "etiquette": _export(_type_fonction((QUELCONQUE, TEXTE), QUELCONQUE),
                          "etiquette(parent: quelconque, texte: texte) -> quelconque",
                          "Ajoute une étiquette de texte à une fenêtre ou à un conteneur.", _etiquette),
    "bouton": _export(_type_fonction((QUELCONQUE, TEXTE, _ACTION), QUELCONQUE),
                       "bouton(parent: quelconque, texte: texte, action: fonction() -> rien) -> quelconque",
                       "Ajoute un bouton qui appelle l'action sans argument lorsqu'il est cliqué.", _bouton),
    "champ": _export(_type_fonction((QUELCONQUE, TEXTE), QUELCONQUE, 1),
                      "champ(parent: quelconque, valeur: texte = \"\") -> quelconque",
                      "Ajoute un champ de saisie de texte.", _champ),
    "case": _export(_type_fonction((QUELCONQUE, TEXTE, BOOLEEN), QUELCONQUE, 2),
                     "case(parent: quelconque, texte: texte, valeur: booleen = faux) -> quelconque",
                     "Ajoute une case à cocher.", _case),
    "liste_deroulante": _export(_type_fonction((QUELCONQUE, liste_de(TEXTE), optionnel_de(TEXTE)), QUELCONQUE, 2),
                                 "liste_deroulante(parent: quelconque, options: liste<texte>, valeur: texte? = nul) -> quelconque",
                                 "Ajoute une liste déroulante. La première option est sélectionnée par défaut.",
                                 _liste_deroulante),
    "zone_texte": _export(_type_fonction((QUELCONQUE, TEXTE), QUELCONQUE, 1),
                           "zone_texte(parent: quelconque, contenu: texte = \"\") -> quelconque",
                           "Ajoute une zone de texte multiligne avec barre de défilement.", _zone_texte),
    "image": _export(_type_fonction((QUELCONQUE, TEXTE), QUELCONQUE),
                      "image(parent: quelconque, chemin: texte) -> quelconque",
                      "Affiche une image PNG ou GIF depuis un fichier local.", _image),
    "grille": _export(_type_fonction((QUELCONQUE,), QUELCONQUE),
                       "grille(parent: quelconque) -> quelconque",
                       "Crée un conteneur destiné au placement explicite par ligne et colonne.", _grille),
    "ligne": _export(_type_fonction((QUELCONQUE,), QUELCONQUE),
                      "ligne(parent: quelconque) -> quelconque",
                      "Crée un conteneur horizontal.", _ligne),
    "colonne": _export(_type_fonction((QUELCONQUE,), QUELCONQUE),
                        "colonne(parent: quelconque) -> quelconque",
                        "Crée un conteneur vertical.", _colonne),
    "placer": _export(_type_fonction((QUELCONQUE, QUELCONQUE, ENTIER, ENTIER), RIEN),
                       "placer(grille: quelconque, element: quelconque, ligne: entier, colonne: entier)",
                       "Place un widget ou un conteneur dans une grille (indices à partir de zéro).", _placer),
    "valeur": _export(_type_fonction((QUELCONQUE,), QUELCONQUE),
                       "valeur(element: quelconque) -> quelconque",
                       "Lit la valeur courante d'un champ, d'une case, d'une liste ou d'une zone de texte.", _valeur),
    "definir_valeur": _export(_type_fonction((QUELCONQUE, QUELCONQUE), RIEN),
                              "definir_valeur(element: quelconque, valeur: quelconque)",
                              "Modifie la valeur d'un champ, d'une case, d'une liste ou d'une zone de texte.",
                              _definir_valeur),
    "definir_texte": _export(_type_fonction((QUELCONQUE, TEXTE), RIEN),
                             "definir_texte(element: quelconque, texte: texte)",
                             "Change le texte d'une étiquette ou d'un bouton.", _definir_texte),
    "demarrer": _export(_type_fonction((QUELCONQUE,), RIEN),
                         "demarrer(fenetre: quelconque)",
                         "Lance la boucle d'événements et garde la fenêtre ouverte.", _demarrer),
    "fermer": _export(_type_fonction((QUELCONQUE,), RIEN),
                       "fermer(fenetre: quelconque)",
                       "Ferme la fenêtre.", _fermer),
    "message": _export(_type_fonction((TEXTE, TEXTE), RIEN),
                        "message(titre: texte, texte: texte)",
                        "Affiche une boîte de dialogue informative.", _message),
    "question": _export(_type_fonction((TEXTE, TEXTE), BOOLEEN),
                         "question(titre: texte, texte: texte) -> booleen",
                         "Pose une question Oui/Non et retourne vrai si l'utilisateur répond Oui.", _question),
    "choisir_fichier": _export(_type_fonction((TEXTE,), optionnel_de(TEXTE), 0),
                                "choisir_fichier(titre: texte = \"Choisir un fichier\") -> texte?",
                                "Ouvre le sélecteur de fichiers ; retourne nul si l'utilisateur annule.",
                                _choisir_fichier),
}


def fonctions_module() -> dict[str, Callable]:
    """Retourne les fonctions à installer dans l'environnement d'un module `gui`."""
    return {nom: export.fonction for nom, export in EXPORTS.items()}
