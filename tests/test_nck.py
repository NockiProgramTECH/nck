import io
import contextlib
import pathlib

import pytest

from nck import ErreurExecution, ErreurSyntaxe, ErreurType, executer_source, compiler_source

RACINE = pathlib.Path(__file__).resolve().parent.parent


def run(src: str) -> str:
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        executer_source(src, "<test>")
    return buf.getvalue()


# ---------- bases ----------

def test_ecrire_et_types_de_base():
    assert run('ecrire(1, 2.5, "a", vrai, faux, nul, [1, "x"])') == '1 2.5 a vrai faux nul [1, "x"]\n'


def test_arithmetique():
    assert run("ecrire(1 + 2 * 3, 7 % 3, 7 / 2, -(2 + 3), 2 - 5)") == "7 1 3.5 -5 -3\n"


def test_priorites_logiques():
    assert run("ecrire(vrai ou faux et faux, non vrai ou vrai, 1 < 2 et 2 < 3)") == "vrai vrai vrai\n"


def test_textes():
    assert run('ecrire("a" + "b", "ab" * 2, "héllo"[1], longueur("abc"))') == "ab abab é 3\n"


def test_variables_et_inference():
    assert run("variable x = 5\nx = x + 1\nx += 2\nx *= 2\necrire(x)") == "16\n"


def test_variable_sans_valeur():
    assert run("variable x: entier\nx = 3\necrire(x)") == "3\n"


def test_variable_utilisee_avant_init():
    with pytest.raises(ErreurType, match="avant d'avoir reçu une valeur"):
        compiler_source("variable x: entier\necrire(x)")


def test_constante_non_modifiable():
    with pytest.raises(ErreurType, match="constante"):
        compiler_source("constante C = 1\nC = 2")


# ---------- contrôle ----------

def test_si_forme_courte_et_longue():
    src = """
variable n = 20
si (n > 20): ecrire("grand")
sinon: ecrire("petit")
si (n == 20):
    ecrire("egal")
sinon si (n == 21):
    ecrire("21")
sinon:
    ecrire("autre")
fin
"""
    assert run(src) == "petit\negal\n"


def test_si_sans_parentheses():
    assert run('si 1 < 2: ecrire("ok")') == "ok\n"


def test_boucles():
    src = """
variable s = 0
pour i dans intervalle(10):
    si (i == 3): continuer
    si (i == 6): arreter
    s += i
fin
variable k = 0
tantque (k < 3): k += 1
ecrire(s, k)
"""
    assert run(src) == "12 3\n"


def test_pour_sur_entier_et_texte():
    assert run('pour i dans 3: ecrire(i)\npour c dans "ab": ecrire(c)') == "0\n1\n2\na\nb\n"


def test_arreter_hors_boucle():
    with pytest.raises(ErreurType, match="en dehors d'une boucle"):
        compiler_source("arreter")


# ---------- fonctions ----------

def test_fonctions_et_recursion():
    src = """
fonction fact(n: entier) -> entier:
    si (n <= 1): retourner 1
    retourner n * fact(n - 1)
fin
ecrire(fact(10))
"""
    assert run(src) == "3628800\n"


def test_fonction_declaree_apres_usage():
    assert run("ecrire(double(4))\nfonction double(x: entier) -> entier: retourner x * 2") == "8\n"


def test_fonction_valeur_et_fermeture():
    src = """
fonction fabriquer(base: entier) -> fonction<entier, entier>:
    fonction plus(x: entier) -> entier:
        retourner base + x
    fin
    retourner plus
fin
variable plus10 = fabriquer(10)
ecrire(plus10(5))
"""
    assert run(src) == "15\n"


def test_fonction_retour_manquant():
    with pytest.raises(ErreurType, match="doit retourner"):
        compiler_source("fonction f() -> entier:\n    ecrire(1)\nfin")


def test_fonction_mauvais_arguments():
    with pytest.raises(ErreurType, match="texte attendu, mais entier"):
        compiler_source("fonction f(a: texte): ecrire(a)\nf(1)")
    with pytest.raises(ErreurType, match="attend 1 argument"):
        compiler_source("fonction f(a: texte): ecrire(a)\nf()")


def test_portee_locale():
    src = """
variable x = 1
fonction f():
    variable x = 2
    ecrire(x)
fin
f()
ecrire(x)
"""
    assert run(src) == "2\n1\n"


def test_recursion_trop_profonde():
    with pytest.raises(ErreurExecution, match="récursion trop profonde"):
        run("fonction f(n: entier) -> entier: retourner f(n + 1)\nf(0)")


# ---------- typage ----------

def test_erreur_affectation_type():
    with pytest.raises(ErreurType, match="texte à une cible de type entier"):
        compiler_source('variable age: entier = 25\nage = "vingt"')


def test_erreur_addition_texte_nombre():
    with pytest.raises(ErreurType, match="texte\\(...\\)"):
        compiler_source('ecrire(1 + "a")')


def test_entier_vers_reel_ok():
    assert run("variable x: reel = 3\necrire(x)") == "3\n"


def test_reel_vers_entier_interdit():
    with pytest.raises(ErreurType):
        compiler_source("variable x: entier = 3.5")


def test_condition_non_booleenne():
    with pytest.raises(ErreurType, match="booleen"):
        compiler_source("si (1): ecrire(1)")


def test_liste_typee():
    assert run("variable l: liste<entier> = []\najouter(l, 1)\nl[0] = 5\necrire(l, l[0], longueur(l))") == "[5] 5 1\n"
    with pytest.raises(ErreurType, match="liste<entier>"):
        compiler_source('variable l: liste<entier> = []\najouter(l, "a")')
    with pytest.raises(ErreurType):
        compiler_source("variable l: liste<entier> = [1, 2]\nl[0] = \"a\"")


def test_type_inconnu_suggestion():
    with pytest.raises(ErreurType, match="entier"):
        compiler_source("variable x: int = 1")


def test_quelconque_verifie_a_execution():
    assert run('variable q: quelconque = 1\nq = "a"\necrire(q)') == "a\n"
    with pytest.raises(ErreurExecution, match="entier attendu, mais texte"):
        run('variable q: quelconque = "a"\nvariable n: entier = q')


def test_redeclaration_interdite():
    with pytest.raises(ErreurType, match="déjà déclaré"):
        compiler_source("variable x = 1\nvariable x = 2")


def test_expression_sans_effet():
    with pytest.raises(ErreurType, match="aucun effet"):
        compiler_source("1 + 2")


def test_code_inatteignable():
    with pytest.raises(ErreurType, match="inatteignable"):
        compiler_source("fonction f() -> entier:\n    retourner 1\n    ecrire(2)\nfin")


# ---------- erreurs d'exécution ----------

def test_division_par_zero():
    with pytest.raises(ErreurExecution, match="division par zéro"):
        run("ecrire(1 / 0)")


def test_index_hors_limites():
    with pytest.raises(ErreurExecution, match="hors limites"):
        run("variable l = [1]\necrire(l[3])")


def test_position_erreur():
    with pytest.raises(ErreurType) as exc:
        compiler_source("variable a = 1\n\nvariable b: texte = a")
    assert (exc.value.ligne, exc.value.colonne) == (3, 21)


# ---------- syntaxe ----------

def test_erreurs_syntaxe():
    with pytest.raises(ErreurSyntaxe, match="'fin' attendu"):
        compiler_source("si (vrai):\n    ecrire(1)\n")
    with pytest.raises(ErreurSyntaxe, match="chaîne de caractères non fermée"):
        compiler_source('ecrire("abc)')
    with pytest.raises(ErreurSyntaxe):
        compiler_source("variable = 3")
    with pytest.raises(ErreurSyntaxe, match="'fin' inattendu"):
        compiler_source("fin")


def test_commentaires_et_points_virgules():
    src = "# a\n// b\n/* c\n d */ variable x = 1; x += 1 ; ecrire(x)"
    assert run(src) == "2\n"


def test_expressions_multilignes():
    assert run("variable l = [\n  1,\n  2,\n]\necrire(somme(\n  l\n))") == "3\n"


# ---------- natifs ----------

def test_natifs_divers():
    src = """
ecrire(texte(12), entier("7"), reel("2.5"), entier(3.9), booleen("vrai"))
ecrire(majuscule("ab"), minuscule("AB"), decouper("a,b", ","), joindre(["a", "b"], "-"))
ecrire(trier([3, 1, 2]), inverser([1, 2]), minimum(3, 1), maximum([4, 9]), absolu(-2), racine(16))
ecrire(contient([1, 2], 2), position("abc", "c"), tranche([1, 2, 3], 1), remplacer("aa", "a", "b"))
ecrire(puissance(2, 10), arrondir(2.567, 2), division_entiere(7, 2), plancher(2.7), plafond(2.1))
"""
    assert run(src) == (
        "12 7 2.5 3 vrai\n"
        'AB ab ["a", "b"] a-b\n'
        "[1, 2, 3] [2, 1] 1 9 2 4.0\n"
        "vrai 2 [2, 3] bb\n"
        "1024 2.57 3 2 3\n"
    )


def test_natif_mauvais_type():
    with pytest.raises(ErreurType, match="majuscule"):
        compiler_source("majuscule(1)")


def test_natif_masquable():
    # Une variable peut masquer un natif (comme en TypeScript) ; le natif redevient visible hors de la portée.
    assert run("fonction f(valeurs: liste<entier>) -> entier: retourner longueur(valeurs)\necrire(f([1, 2]), valeurs({1: 2}))") == "2 [2]\n"


# ---------- exemples du dépôt ----------

@pytest.mark.parametrize("nom", ["bonjour", "fonctions", "boucles", "types"])
def test_exemples(nom):
    source = (RACINE / "exemples" / f"{nom}.nck").read_text(encoding="utf-8")
    assert run(source)  # s'exécute sans erreur et produit une sortie


# ---------- classes (POO) ----------

CLASSE_P = """
classe Personne:
    nom: texte
    age: entier = 0
    fonction saluer() -> texte: retourner "Salut " + soi.nom
    fonction vieillir(n: entier): soi.age += n
fin
"""


def test_classe_creation_et_champs():
    src = CLASSE_P + """
variable p = Personne("Awa", 20)
variable q = Personne(nom = "Ali")
p.vieillir(1)
q.age = 5
ecrire(p, q.age, p.saluer(), type_de(p))
"""
    assert run(src) == 'Personne(nom="Awa", age=21) 5 Salut Awa Personne\n'


def test_classe_erreurs_compilation():
    with pytest.raises(ErreurType, match="obligatoire"):
        compiler_source(CLASSE_P + "Personne()")
    with pytest.raises(ErreurType, match="texte attendu, mais entier"):
        compiler_source(CLASSE_P + "Personne(1)")
    with pytest.raises(ErreurType, match="n'a pas de champ 'prenom'"):
        compiler_source(CLASSE_P + 'Personne(prenom = "a")')
    with pytest.raises(ErreurType, match="n'a pas de champ ni de méthode 'nm'"):
        compiler_source(CLASSE_P + 'ecrire(Personne("a").nm)')
    with pytest.raises(ErreurType, match="texte"):
        compiler_source(CLASSE_P + 'variable p = Personne("a")\np.nom = 1')
    with pytest.raises(ErreurType, match="méthode"):
        compiler_source(CLASSE_P + 'variable p = Personne("a")\np.saluer = 1')
    with pytest.raises(ErreurType, match="arguments nommés"):
        compiler_source("fonction f(a: entier): ecrire(a)\nf(a = 1)")


def test_classe_validation_execution():
    src = """
classe Compte:
    solde: entier
    fonction valider():
        verifier(soi.solde >= 0, "solde négatif")
    fin
fin
Compte(-1)
"""
    with pytest.raises(ErreurExecution, match="solde négatif"):
        run(src)
    with pytest.raises(ErreurExecution, match="texte attendu, mais entier"):
        run(CLASSE_P + "variable q: quelconque = 3\nPersonne(q)")


def test_heritage():
    src = CLASSE_P + """
classe Etudiant herite Personne:
    ecole: texte = "UO"
    fonction saluer() -> texte: retourner "Etudiant " + soi.nom
fin
variable e = Etudiant("Issa", 22)
variable groupe: liste<Personne> = [Personne("A"), e]
ecrire(e.saluer(), e.ecole, longueur(groupe), groupe[1].saluer())
"""
    assert run(src) == "Etudiant Issa UO 2 Etudiant Issa\n"
    with pytest.raises(ErreurType, match="déjà défini"):
        compiler_source(CLASSE_P + "classe E herite Personne:\n    nom: texte\nfin")
    with pytest.raises(ErreurType, match="pas compatible"):
        compiler_source(CLASSE_P + "classe E herite Personne:\n    fonction saluer() -> entier: retourner 1\nfin")
    with pytest.raises(ErreurType, match="parente 'X' inconnue"):
        compiler_source("classe E herite X:\n    a: entier\nfin")


def test_methode_comme_valeur_et_texte_personnalise():
    src = """
classe Point:
    x: entier
    y: entier
    fonction texte() -> texte: retourner "(" + texte(soi.x) + ", " + texte(soi.y) + ")"
    fonction norme2() -> entier: retourner soi.x * soi.x + soi.y * soi.y
fin
variable p = Point(3, 4)
variable f = p.norme2
ecrire(p, f())
"""
    assert run(src) == "(3, 4) 25\n"


def test_exemple_classes():
    source = (RACINE / "exemples" / "classes.nck").read_text(encoding="utf-8")
    assert "Etudiant" not in run(source).split("\n")[0]


# ---------- gestion des erreurs ----------

def test_essayer_attraper_enfin():
    src = """
essayer:
    ecrire(1)
    si (vrai): lever "boum"
    ecrire(2)
attraper e:
    ecrire("attrapé :", e.message)
enfin:
    ecrire("fin")
fin
"""
    assert run(src) == "1\nattrapé : boum\nfin\n"


def test_erreur_execution_attrapable():
    assert run('essayer:\n    ecrire(1 / 0)\nattraper e:\n    ecrire(e.message)\nfin') == "division par zéro\n"


def test_classe_erreur_personnalisee_et_filtrage():
    src = """
classe ErreurSolde herite Erreur:
    manque: entier
fin
essayer:
    lever ErreurSolde("insuffisant", 5)
attraper ErreurSolde e:
    ecrire(e.message, e.manque, texte(e))
attraper e:
    ecrire("autre")
fin
essayer:
    lever "simple"
attraper ErreurSolde e:
    ecrire("non")
attraper e:
    ecrire("générique :", e.message)
fin
"""
    assert run(src) == "insuffisant 5 ErreurSolde : insuffisant\ngénérique : simple\n"


def test_erreur_non_attrapee_et_propagation():
    with pytest.raises(ErreurExecution, match="erreur non attrapée : boum") as exc:
        run('fonction f(): lever "boum"\nf()')
    assert exc.value.ligne == 1
    with pytest.raises(ErreurExecution, match="non attrapée"):
        run('essayer:\n    lever "x"\nattraper e:\n    lever e\nfin')


def test_retourner_et_arreter_dans_essayer():
    src = """
fonction f() -> entier:
    essayer:
        retourner 1
    enfin:
        ecrire("enfin")
    fin
fin
ecrire(f())
pour i dans 10:
    essayer:
        si (i == 2): arreter
    attraper e:
        ecrire("non")
    fin
    ecrire(i)
fin
"""
    assert run(src) == "enfin\n1\n0\n1\n"


def test_erreurs_statiques_gestion_erreurs():
    with pytest.raises(ErreurType, match="lever"):
        compiler_source("lever 3")
    with pytest.raises(ErreurType, match="héritant de Erreur"):
        compiler_source("essayer:\n    ecrire(1)\nattraper entier e:\n    ecrire(2)\nfin")
    with pytest.raises(ErreurSyntaxe, match="au moins un"):
        compiler_source("essayer:\n    ecrire(1)\nfin")
    with pytest.raises(ErreurType, match="doit retourner"):
        compiler_source("fonction f() -> entier:\n    essayer:\n        retourner 1\n    attraper e:\n        ecrire(e.message)\n    fin\nfin")


def test_exemple_erreurs():
    source = (RACINE / "exemples" / "erreurs.nck").read_text(encoding="utf-8")
    assert "solde final : 70" in run(source)


# ---------- dictionnaires ----------

def test_dico_base():
    src = """
variable d: dico<texte, entier> = {"a": 1, "b": 2}
d["c"] = 3
d["a"] += 10
ecrire(d, d["a"], longueur(d), contient(d, "b"), contient(d, "z"))
ecrire(cles(d), valeurs(d), obtenir(d, "z", 0), retirer(d, "b"), d)
pour k dans d: ecrire(k)
"""
    assert run(src) == ('{"a": 11, "b": 2, "c": 3} 11 3 vrai faux\n'
                        '["a", "b", "c"] [11, 2, 3] 0 2 {"a": 11, "c": 3}\n'
                        "a\nc\n")


def test_dico_inference_et_vide():
    assert run('variable d = {1: "x"}\nd[2] = "y"\necrire(d, type_de(d))') == '{1: "x", 2: "y"} dico\n'
    assert run('variable d = {}\nd["a"] = 1\necrire(d)') == '{"a": 1}\n'
    assert run('variable d: dico<texte, liste<entier>> = {}\nd["a"] = []\najouter(d["a"], 1)\necrire(d)') == '{"a": [1]}\n'


def test_dico_erreurs_types():
    D = 'variable d: dico<texte, entier> = {"a": 1}\n'
    with pytest.raises(ErreurType, match="clé doit être un texte"):
        compiler_source(D + "ecrire(d[3])")
    with pytest.raises(ErreurType, match="texte à une cible de type entier"):
        compiler_source(D + 'd["x"] = "vingt"')
    with pytest.raises(ErreurType, match="clé de dictionnaire"):
        compiler_source("variable d = {[1]: 2}")
    with pytest.raises(ErreurType, match="dico<texte, entier>"):
        compiler_source('variable d: dico<texte, entier> = {"a": "b"}')
    with pytest.raises(ErreurType, match="vouliez-vous dire 'dico'"):
        compiler_source("variable d: dict<texte, entier> = {}")
    with pytest.raises(ErreurType, match="'cles' attend un dico"):
        compiler_source("ecrire(cles(3))")


def test_dico_erreurs_execution():
    D = 'variable d: dico<texte, entier> = {"a": 1}\n'
    with pytest.raises(ErreurExecution, match='clé "zoe" introuvable'):
        run(D + 'ecrire(d["zoe"])')
    with pytest.raises(ErreurExecution, match='clé "zoe" introuvable'):
        run(D + 'd["zoe"] += 1')
    assert run(D + 'essayer:\n    ecrire(d["z"])\nattraper e:\n    ecrire(e.message)\nfin') == 'clé "z" introuvable dans le dictionnaire\n'


def test_exemple_dictionnaires():
    source = (RACINE / "exemples" / "dictionnaires.nck").read_text(encoding="utf-8")
    assert '{"le": 3, "chat": 1, "et": 2, "chien": 1, "rat": 1}' in run(source)


# ---------- modules ----------

def test_modules(tmp_path):
    (tmp_path / "outils").mkdir()
    (tmp_path / "outils" / "maths.nck").write_text(
        'constante PI = 3.14\nfonction carre(x: entier) -> entier: retourner x * x\n'
        'variable compteur = 0\nfonction inc(): compteur += 1\n'
        'classe Point:\n    x: entier\n    fonction double() -> entier: retourner soi.x * 2\nfin\n', encoding="utf-8")
    (tmp_path / "outils" / "geo.nck").write_text(
        'importer "maths.nck"\nfonction aire(r: entier) -> reel: retourner maths.PI * maths.carre(r)\n', encoding="utf-8")
    principal = tmp_path / "principal.nck"
    src = (
        'importer "outils/maths.nck"\n'
        'importer "outils/geo.nck" comme g\n'
        'depuis "outils/maths.nck" importer PI, carre\n'
        'maths.inc()\nmaths.inc()\n'
        'ecrire(maths.carre(3), carre(4), PI, maths.compteur, g.aire(1))\n'
        'variable p = maths.Point(5)\necrire(p.double(), p, type_de(maths))\n'
    )
    principal.write_text(src, encoding="utf-8")
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        executer_source(src, str(principal))
    assert buf.getvalue() == "9 16 3.14 2 3.14\n10 Point(x=5) module\n"


def test_modules_erreurs(tmp_path):
    (tmp_path / "m.nck").write_text("constante X = 1\nclasse C:\n    v: entier\nfin\n", encoding="utf-8")
    (tmp_path / "a.nck").write_text('importer "b.nck"\n', encoding="utf-8")
    (tmp_path / "b.nck").write_text('importer "a.nck"\n', encoding="utf-8")
    f = str(tmp_path / "t.nck")

    def check(src, motif):
        with pytest.raises(ErreurType, match=motif):
            compiler_source(src, f)

    check('importer "inexistant.nck"', "module introuvable")
    check('importer "a.nck"', "import circulaire : a.nck -> b.nck -> a.nck")
    check('importer "m.nck"\necrire(m.Y)', "ne définit pas 'Y' \\(disponibles : C, X\\)")
    check('importer "m.nck"\nm.X = 2', "impossible de modifier 'X'")
    check('fonction f(): importer "m.nck"', "niveau principal")
    check('depuis "m.nck" importer Z', "ne définit pas 'Z'")
    check('importer "m.txt"', "fichier .nck")
    check('importer "m.nck"\nclasse C:\n    w: entier\nfin', "définie à la fois")
    check('importer "m.nck"\necrire(m.X + "a")', "additionner un entier et un texte")
