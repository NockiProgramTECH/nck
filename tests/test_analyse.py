"""Tests du moteur d'analyse pour l'éditeur (autocomplétion, survol, signature, diagnostics)."""
import io
import json

from nck.analyse import Analyse
from nck.serveur import Serveur

SRC = '''classe Personne:
    nom: texte
    age: entier = 0
    fonction saluer(x: entier = 1) -> texte:
        retourner soi.nom
    fin
fin
fonction add(a: entier, b: entier) -> entier:
    variable total = a + b
    retourner total
fin
variable p = Personne("Awa")
ecrire(p.saluer(), add(1, 2))
'''


def noms(items):
    return [i["nom"] for i in items]


def test_diagnostics():
    assert Analyse(SRC).diagnostics() == []
    d = Analyse(SRC + 'variable n: entier = "x"\n').diagnostics()
    assert len(d) == 1 and d[0]["ligne"] == 14 and "entier" in d[0]["message"]


def test_survol():
    a = Analyse(SRC)
    assert "variable p: Personne" in a.survol(12, 10)["contenu"]
    assert "méthode saluer(x: entier = …) -> texte" in a.survol(13, 11)["contenu"]
    assert "ecrire(...valeurs)" in a.survol(13, 2)["contenu"]
    assert "variable total: entier" in a.survol(10, 16)["contenu"]
    assert "classe Personne(nom: texte, age: entier = …)" in a.survol(1, 9)["contenu"]
    assert "mot-clé" in a.survol(8, 2)["contenu"]
    assert "champ nom: texte" in a.survol(5, 23)["contenu"]
    assert a.survol(13, 30) is None


def test_definition():
    a = Analyse(SRC, "/x/t.nck")
    assert a.definition(13, 11) == {"fichier": "/x/t.nck", "ligne": 4, "colonne": 14}
    assert a.definition(13, 22) == {"fichier": "/x/t.nck", "ligne": 8, "colonne": 10}
    assert a.definition(13, 8) == {"fichier": "/x/t.nck", "ligne": 12, "colonne": 10}
    assert a.definition(13, 2) is None   # natif


def test_completions_membres_pendant_la_frappe():
    src = SRC.replace("ecrire(p.saluer()", "ecrire(p.")
    items = Analyse(src, ligne_curseur=13).completions(13, 10)
    assert noms(items) == ["nom", "age", "saluer"]
    assert items[2]["insertion"] == "saluer("
    src = SRC.replace("retourner soi.nom", "retourner soi.")
    assert noms(Analyse(src, ligne_curseur=5).completions(5, 23)) == ["nom", "age", "saluer"]


def test_completions_generales_portee():
    a = Analyse(SRC)
    locaux = noms(a.completions(10, 5))
    assert "total" in locaux and "a" in locaux and "add" in locaux and "Personne" in locaux
    assert "p" not in locaux                      # déclaré plus bas, hors fonction
    globaux = noms(a.completions(13, 1))
    assert "p" in globaux and "total" not in globaux
    assert "ecrire" in globaux and "tantque" in globaux and "entier" in globaux


def test_signature():
    a = Analyse(SRC)
    s = a.signature(13, 24)
    assert s["label"] == "fonction add(a: entier, b: entier) -> entier" and s["actif"] == 0
    assert a.signature(13, 27)["actif"] == 1
    assert a.signature(13, 17)["label"] == "méthode saluer(x: entier = …) -> texte"
    assert a.signature(12, 23)["parametres"] == ["nom: texte", "age: entier = …"]
    assert a.signature(13, 8)["label"].startswith("ecrire(")
    assert a.signature(13, 1) is None


def test_modules_dans_editeur(tmp_path):
    (tmp_path / "m.nck").write_text("fonction carre(x: entier) -> entier: retourner x * x\nconstante K = 2\n", encoding="utf-8")
    f = str(tmp_path / "t.nck")
    a = Analyse('importer "m.nck"\necrire(m.', f, ligne_curseur=2)
    assert noms(a.completions(2, 10)) == ["K", "carre"]
    b = Analyse('importer "m.nck"\necrire(m.carre(', f, ligne_curseur=2)
    assert b.signature(2, 16)["label"] == "fonction carre(x: entier) -> entier"
    c = Analyse('importer "m.nck"\necrire(m.carre(2))', f)
    assert c.definition(2, 11)["fichier"] == str(tmp_path / "m.nck")


def test_serveur():
    srv = Serveur()
    entree = io.StringIO(
        json.dumps({"id": 1, "methode": "analyser", "fichier": "/x.nck", "texte": "variable a = 1\necrire(a +)"}) + "\n"
        + json.dumps({"id": 2, "methode": "survoler", "fichier": "/x.nck", "ligne": 2, "colonne": 8}) + "\n"
        + json.dumps({"id": 3, "methode": "inconnue"}) + "\n")
    sortie = io.StringIO()
    srv.boucle(entree, sortie)
    reps = [json.loads(l) for l in sortie.getvalue().splitlines()]
    assert reps[0]["resultat"]["diagnostics"][0]["ligne"] == 2
    assert "variable a: entier" in reps[1]["resultat"]["survol"]["contenu"]
    assert "méthode inconnue" in reps[2]["erreur"]
