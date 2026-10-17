from types import SimpleNamespace

import pytest

import nck.gui as gui
from nck import compiler_source, executer_source
from nck.analyse import Analyse
from nck.erreurs import ErreurExecution, ErreurType


class FauxVariable:
    def __init__(self, master=None, value=None):
        self.value = value

    def get(self):
        return self.value

    def set(self, value):
        self.value = value


class FauxWidget:
    def __init__(self, parent=None, **options):
        self.parent = parent
        self.options = dict(options)
        self.children = []
        self.command = options.get("command")
        self.text = options.get("text", "")
        self.values = options.get("values", ())
        self.value = ""
        self.disposition = None
        if hasattr(parent, "children"):
            parent.children.append(self)

    def pack(self, **options):
        self.disposition = ("pack", options)

    def grid(self, **options):
        self.disposition = ("grid", options)

    def configure(self, **options):
        self.options.update(options)
        if "text" in options:
            self.text = options["text"]

    config = configure

    def set(self, value):
        self.value = value

    def yview(self, *args):
        return args

    def insert(self, index, value):
        self.value += value

    def delete(self, start, end=None):
        self.value = ""

    def get(self, start=None, end=None):
        return self.value


class FauxFenetre(FauxWidget):
    def __init__(self):
        super().__init__()
        self.titre = None
        self.dimensions = None
        self.boucle_lancee = False
        self.detruite = False

    def title(self, value):
        self.titre = value

    def geometry(self, value):
        self.dimensions = value

    def mainloop(self):
        self.boucle_lancee = True
        a_visiter = list(self.children)
        while a_visiter:
            widget = a_visiter.pop(0)
            a_visiter.extend(widget.children)
            if widget.command is not None:
                widget.command()

    def destroy(self):
        self.detruite = True


class FauxImage:
    def __init__(self, master=None, file=None):
        self.master = master
        self.file = file


class FauxTk:
    def __init__(self):
        self.fenetres = []
        self.Tk = self._creer_fenetre
        self.StringVar = FauxVariable
        self.BooleanVar = FauxVariable
        self.Text = FauxWidget
        self.PhotoImage = FauxImage

    def _creer_fenetre(self):
        fenetre = FauxFenetre()
        self.fenetres.append(fenetre)
        return fenetre


def installer_faux_tk(monkeypatch):
    tk = FauxTk()
    ttk = SimpleNamespace(
        Frame=FauxWidget,
        Label=FauxWidget,
        Button=FauxWidget,
        Entry=FauxWidget,
        Checkbutton=FauxWidget,
        Combobox=FauxWidget,
        Scrollbar=FauxWidget,
    )
    appels = {"message": [], "question": [], "fichier": []}
    messagebox = SimpleNamespace(
        showinfo=lambda titre, texte: appels["message"].append((titre, texte)),
        askyesno=lambda titre, texte: appels["question"].append((titre, texte)) or True,
        showerror=lambda *args, **kwargs: appels.setdefault("erreur", []).append((args, kwargs)),
    )
    filedialog = SimpleNamespace(
        askopenfilename=lambda **kwargs: appels["fichier"].append(kwargs) or "/tmp/demo.txt",
    )
    monkeypatch.setattr(gui, "_tk_modules", lambda: (tk, ttk, messagebox, filedialog))
    return tk, appels


def test_import_gui_et_signatures_typagees():
    compiler_source('''
importer "gui" comme gui
variable app = gui.fenetre("Démo", 500, 350)
gui.etiquette(app, "Bonjour")
gui.bouton(app, "OK", fonction(): ecrire("clic"))
variable champ = gui.champ(app)
variable selection = gui.liste_deroulante(app, ["A", "B"])
gui.demarrer(app)
''')
    compiler_source('''
depuis "gui" importer fenetre, fermer
variable app = fenetre("Démo")
fermer(app)
''')


def test_gui_est_visible_dans_autocompletion_et_signature():
    completions = Analyse('importer "gui" comme gui\ngui.').completions(2, 5)
    assert "fenetre" in [item["nom"] for item in completions]
    signature = Analyse('importer "gui" comme gui\ngui.fenetre(').signature(2, 13)
    assert signature["label"].startswith("fenetre(titre: texte, largeur: entier = 640")


def test_gui_refuse_les_mauvais_types_statiques():
    with pytest.raises(ErreurType, match="texte attendu"):
        compiler_source('importer "gui" comme gui\ngui.fenetre(12)')
    with pytest.raises(ErreurType, match=r"fonction\(\) -> rien attendu"):
        compiler_source('''
importer "gui" comme gui
variable app = gui.fenetre("Démo")
gui.bouton(app, "OK", 12)
''')


def test_interface_gui_factice_et_callbacks(monkeypatch, capsys):
    tk, appels = installer_faux_tk(monkeypatch)
    executer_source('''
importer "gui" comme gui
variable app = gui.fenetre("NCK", 400, 260)
variable saisie = gui.champ(app, "Awa")
gui.definir_valeur(saisie, "Moussa")
ecrire(gui.valeur(saisie))
variable active = gui.case(app, "Actif", vrai)
ecrire(gui.valeur(active))
variable choix = gui.liste_deroulante(app, ["rouge", "vert"])
ecrire(gui.valeur(choix))
variable notes = gui.zone_texte(app, "départ")
gui.definir_valeur(notes, "fin")
ecrire(gui.valeur(notes))
variable table = gui.grille(app)
variable etiquette = gui.etiquette(table, "cellule")
gui.placer(table, etiquette, 0, 1)
gui.bouton(app, "Cliquez", fonction(): ecrire("clic"))
gui.message("Info", "Bonjour")
si (gui.question("Question", "Continuer ?")): ecrire("oui")
ecrire(gui.choisir_fichier("Ouvrir") ?? "annulé")
gui.demarrer(app)
''')

    assert capsys.readouterr().out.splitlines() == [
        "Moussa", "vrai", "rouge", "fin", "oui", "/tmp/demo.txt", "clic",
    ]
    assert len(tk.fenetres) == 1
    assert tk.fenetres[0].titre == "NCK"
    assert tk.fenetres[0].dimensions == "400x260"
    assert tk.fenetres[0].boucle_lancee
    assert appels["message"] == [("Info", "Bonjour")]
    assert appels["question"] == [("Question", "Continuer ?")]
    assert appels["fichier"] == [{"title": "Ouvrir"}]


def test_layout_auto_et_grille_avec_faux_tk(monkeypatch):
    installer_faux_tk(monkeypatch)
    app = gui._fenetre("Disposition")
    ligne = gui._ligne(app)
    etiquette = gui._etiquette(ligne, "à gauche")
    assert etiquette.widget.disposition[0] == "pack"
    assert etiquette.widget.disposition[1]["side"] == "left"

    grille = gui._grille(app)
    champ = gui._champ(grille, "Awa")
    assert champ.widget.disposition is None
    gui._placer(grille, champ, 0, 1)
    assert champ.widget.disposition[0] == "grid"

    zone = gui._zone_texte(grille, "Texte")
    gui._placer(grille, zone, 1, 0)
    assert zone.layout.disposition[0] == "grid"


def test_gui_erreurs_runtime_sur_poignees_invalides():
    with pytest.raises(ErreurExecution, match="fenêtre ou un widget parent"):
        executer_source('importer "gui" comme gui\ngui.etiquette(12, "invalide")')
    with pytest.raises(ErreurExecution, match="largeur et une hauteur entières positives"):
        executer_source('importer "gui" comme gui\ngui.fenetre("invalide", 0, 100)')
