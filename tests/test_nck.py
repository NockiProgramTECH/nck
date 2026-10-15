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


# ---------- bibliothèque standard ----------

def test_fichiers(tmp_path):
    f = str(tmp_path / "a.txt").replace("\\", "\\\\")
    src = f'''
constante F = "{f}"
ecrire_fichier(F, "ligne 1\\nligne 2")
ajouter_fichier(F, "\\nligne 3")
ecrire(fichier_existe(F), lire_lignes(F), longueur(lire_fichier(F)))
supprimer_fichier(F)
ecrire(fichier_existe(F))
essayer:
    lire_fichier(F)
attraper e:
    ecrire(e.message)
fin
'''
    assert run(src) == f'vrai ["ligne 1", "ligne 2", "ligne 3"] 23\nfaux\nfichier introuvable : "{tmp_path / "a.txt"}"\n'


def test_json():
    src = '''
classe P:
    nom: texte
    tags: liste<texte>
fin
variable j = vers_json([P("a", ["x"]), {"k": 1.5}, nul, vrai])
ecrire(j)
variable d = depuis_json(j)
ecrire(d[0]["nom"], d[1]["k"], d[2], longueur(d))
essayer:
    depuis_json("{oups")
attraper e:
    ecrire(contient(e.message, "JSON invalide"))
fin
'''
    assert run(src) == '[{"nom": "a", "tags": ["x"]}, {"k": 1.5}, null, true]\na 1.5 nul 4\nvrai\n'


def test_dates_et_texte():
    src = '''
variable t = creer_date(2026, 12, 25, 10, 30)
variable d = date(t)
ecrire(d["annee"], d["mois"], d["jour"], d["heure"], d["minute"], formater_date("JJ/MM/AAAA hh:mm", t))
ecrire(formater("{} a {} ans", "Awa", 20), formater("{1}-{0}", "a", "b"))
ecrire(est_nombre("3,5"), est_entier("-4"), est_entier("4.0"), remplir_gauche("7", 3, "0"), remplir_droite("ab", 4, ".") + "|")
'''
    assert run(src) == "2026 12 25 10 30 25/12/2026 10:30\nAwa a 20 ans b-a\nvrai vrai faux 007 ab..|\n"


def test_arguments_et_env(monkeypatch):
    from nck import natifs
    monkeypatch.setattr(natifs, "ARGUMENTS", ["x", "y"])
    monkeypatch.setenv("NCK_TEST", "ok")
    assert run('ecrire(arguments(), variable_env("NCK_TEST"), variable_env("NCK_ABSENT", "defaut"))') == '["x", "y"] ok defaut\n'


def test_quelconque_indexable_par_texte():
    assert run('variable d: quelconque = {"a": [1, 2]}\necrire(d["a"][1])') == "2\n"


# ---------- confort : f-textes, défauts, selon, pour i, x ----------

def test_texte_formate():
    assert run('variable n = "Awa"\necrire(f"Bonjour {n}, {1 + 2} {{ok}} {majuscule(n)[0]} {[1, 2]}")') == "Bonjour Awa, 3 {ok} A [1, 2]\n"
    with pytest.raises(ErreurType, match="variable 'x' inconnue") as exc:
        compiler_source('ecrire(f"a {x} b")')
    assert (exc.value.ligne, exc.value.colonne) == (1, 13)
    with pytest.raises(ErreurSyntaxe, match="'}' manquant"):
        compiler_source('ecrire(f"a {1 b")')
    with pytest.raises(ErreurType, match="rien"):
        compiler_source('ecrire(f"{ecrire(1)}")')


def test_parametres_par_defaut():
    src = '''
fonction f(a: entier, b: entier = 10, c: texte = "x") -> texte: retourner f"{a + b}{c}"
ecrire(f(1), f(1, 2), f(1, 2, "y"))
variable g: fonction<entier, texte> = f
ecrire(g(5))
classe K:
    v: entier
    fonction add(n: entier = 1) -> entier: retourner soi.v + n
fin
ecrire(K(1).add(), K(1).add(5))
'''
    assert run(src) == "11x 3x 3y\n15x\n2 6\n"
    with pytest.raises(ErreurSyntaxe, match="doit avoir une valeur par défaut"):
        compiler_source("fonction f(a: entier = 1, b: entier): retourner")
    with pytest.raises(ErreurType, match="valeur par défaut du paramètre 'b'"):
        compiler_source('fonction f(a: entier, b: entier = "x"): retourner')
    with pytest.raises(ErreurType, match="entre 1 et 2"):
        compiler_source("fonction f(a: entier, b: entier = 2): retourner\nf()")


def test_selon():
    src = '''
fonction nom(n: entier) -> texte:
    selon (n):
        cas 1: retourner "un"
        cas 2, 3:
            retourner "deux-trois"
        sinon: retourner "autre"
    fin
fin
ecrire(nom(1), nom(3), nom(9))
variable x = 2.5
selon (x):
    cas 1 + 1.5: ecrire("calculé")
fin
selon ("b"):
    cas "a": ecrire("non")
fin
'''
    assert run(src) == "un deux-trois autre\ncalculé\n"
    with pytest.raises(ErreurType, match="ne peut jamais correspondre"):
        compiler_source('selon (3):\n    cas "a": ecrire(1)\nfin')
    with pytest.raises(ErreurType, match="doit retourner"):
        compiler_source('fonction f(n: entier) -> entier:\n    selon (n):\n        cas 1: retourner 1\n    fin\nfin')
    with pytest.raises(ErreurSyntaxe, match="au moins un 'cas'"):
        compiler_source("selon (3):\nfin")


def test_pour_deux_variables():
    src = '''
pour i, x dans ["a", "b"]: ecrire(i, x)
pour k, v dans {"x": 1}: ecrire(k, v)
pour i, c dans "ab": ecrire(i, c)
pour i, x dans [10, 20, 30]:
    si (i == 1): arreter
    ecrire(x)
fin
'''
    assert run(src) == "0 a\n1 b\nx 1\n0 a\n1 b\n10\n"
    with pytest.raises(ErreurType, match="même nom"):
        compiler_source("pour i, i dans [1]: ecrire(i)")
    with pytest.raises(ErreurType, match="'n' est de type entier, mais reçoit un texte"):
        compiler_source('pour k, v dans {"x": 1}:\n    variable n: entier = k\nfin')


def test_exemple_confort():
    source = (RACINE / "exemples" / "confort.nck").read_text(encoding="utf-8")
    assert "7 -> week-end" in run(source)


# ---------- v0.9 : POO complète et décorateurs ----------


POO_AVANCEE = (RACINE / "exemples" / "poo_avancee.nck").read_text(encoding="utf-8")


def test_exemple_poo_avancee():
    out = run(POO_AVANCEE)
    assert "[carré] petit : 4.0 cm" in out
    assert "vrai faux" in out
    assert "[(1.0, 0.0), (2.0, 2.0), (5.0, 5.0)]" in out
    assert "appel avec [0, 4, 5]\n9" in out


def test_abstraite_non_instanciable():
    with pytest.raises(ErreurType, match="abstraite"):
        run("classe A:\n    abstraite fonction f() -> entier\nfin\nvariable a = A()\n")


def test_prive_inaccessible():
    with pytest.raises(ErreurType, match="privé"):
        run("classe A:\n    _x: entier = 1\nfin\nvariable a = A()\necrire(a._x)\n")


def test_statique_et_constante():
    out = run("classe T:\n    constante MAX = 3\n    statique fonction deux() -> entier: retourner 2\nfin\n"
              "ecrire(T.MAX + T.deux())\n")
    assert out == "5\n"
    with pytest.raises(ErreurType, match="statique"):
        run("classe A:\n    fonction f() -> entier: retourner 1\nfin\necrire(A.f())\n")


def test_parent_hors_heritage():
    with pytest.raises(ErreurType, match="parent"):
        run("classe A:\n    x: entier\n    fonction g(): ecrire(parent.x)\nfin\n")


def test_operateur_manquant():
    with pytest.raises(ErreurType, match="plus"):
        run("classe A:\n    x: entier\nfin\nvariable a = A(1) + A(2)\n")


def test_variadique_types():
    with pytest.raises(ErreurType, match="argument 2"):
        run("fonction f(...a: liste<texte>):\n    ecrire(a)\nfin\nf(\"a\", 2)\n")
    assert run("fonction n(...a) -> entier: retourner longueur(a)\necrire(n(), n(1, \"b\", vrai))\n") == "0 3\n"


def test_decorateur_invalide():
    with pytest.raises(ErreurType, match="décorateur"):
        run("fonction d(x: entier) -> entier: retourner x\n@d\nfonction f():\n    ecrire(1)\nfin\n")


# ---------- v0.10 : fonctions anonymes, optionnels, plages ----------


def test_exemple_fonctions_anonymes():
    out = run((RACINE / "exemples" / "fonctions_anonymes.nck").read_text(encoding="utf-8"))
    assert out.startswith("[2, 4, 6, 8, 10, 12]\n[2, 4, 6]\n21\n5\nvrai faux\n")
    assert "Bonjour ! Bonjour Issa\nnul 0\nyy\n" in out


def test_lambda_sans_contexte():
    with pytest.raises(ErreurType, match="déduire le type du paramètre"):
        run("variable f = fonction(x): x * 2\n")
    assert run("variable f = fonction(x: entier): x * 2\necrire(f(4))\n") == "8\n"


def test_optionnel_doit_etre_teste():
    with pytest.raises(ErreurType, match="peut être nul"):
        run("variable p: texte? = nul\necrire(p + \"x\")\n")
    with pytest.raises(ErreurType, match="reçoit un nul"):
        run("variable p: texte = nul\n")
    out = run("variable p: texte? = \"ab\"\nsi p != nul et longueur(p) > 1:\n    ecrire(longueur(p))\nfin\necrire(p ?? \"?\")\n")
    assert out == "2\nab\n"


def test_retour_precoce_affine():
    src = "fonction f(n: entier?) -> entier:\n    si n == nul:\n        retourner 0\n    fin\n    retourner n + 1\nfin\necrire(f(nul), f(2))\n"
    assert run(src) == "0 3\n"


def test_sinon_nul_inutile():
    with pytest.raises(ErreurType, match="inutile"):
        run("variable a = 1\necrire(a ?? 2)\n")


def test_plage():
    assert run("ecrire(1..4)\npour i dans 0..2:\n    ecrire(i)\nfin\n") == "[1, 2, 3]\n0\n1\n"
    with pytest.raises(ErreurType, match="entiers"):
        run("ecrire(1.5..3)\n")


def test_filtrer_type():
    with pytest.raises(ErreurType, match="booleen"):
        run("ecrire(filtrer([1], fonction(x): x + 1))\n")


# ---------- v0.11 : énumérations, notation méthode, conditionnelle, affectation multiple ----------


def test_exemple_confort2():
    out = run((RACINE / "exemples" / "confort2.nck").read_text(encoding="utf-8"))
    assert out.startswith("Couleur.VERT VERT 1 froid [Couleur.ROUGE, Couleur.VERT, Couleur.BLEU] vrai vrai\n10\n4 [1, 2, 3, 5] [30, 20, 50]\n")
    assert "2 trois\n2 1\n11\nmajeur 0\nBonjour,\n  le monde !\nFin.\n" in out


def test_selon_enum_incomplet():
    with pytest.raises(ErreurType, match="n'est pas complet"):
        run("enumeration C: A, B fin\nfonction f(c: C) -> texte:\n    selon c:\n        cas C.A: retourner \"a\"\n    fin\nfin\n")


def test_methode_native_inconnue():
    with pytest.raises(ErreurType, match="ajouter"):
        run("variable l = [1]\nl.ajoutr(2)\n")
    with pytest.raises(ErreurType, match="parenthèses"):
        run("variable l = [1]\necrire(l.longueur)\n")


def test_conditionnelle_types():
    with pytest.raises(ErreurType, match="incompatibles"):
        run("variable s = si vrai alors 1 sinon \"a\"\n")
    assert run("variable n = si 1 > 0 alors \"p\" sinon nul\necrire(n ?? \"-\")\n") == "p\n"


def test_destructuration_taille():
    with pytest.raises(ErreurExecution, match="3 élément"):
        run("variable a, b = [1, 2, 3]\n")
