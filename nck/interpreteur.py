"""Interpréteur : compile l'AST (déjà vérifié) en fermetures Python puis l'exécute.

Chaque nœud est transformé une seule fois en une fonction Python `fn(env)`, ce qui évite
le coût d'une traversée de l'arbre à chaque exécution (bien plus rapide qu'un « tree-walker »).
"""

import sys
from typing import Callable

from .arbre import (
    Affectation, Appel, Arreter, Binaire, Bloc, Continuer, DeclClasse, DeclFonction, DeclVariable,
    DicoLit, Essayer, Etalement, ExprInstr, Expr, FonctionAnonyme, Identifiant, DeclMultiple, AffectationMultiple, DeclEnum, Conditionnelle, Importer, Index, Instr, Lever, ListeLit, Litteral, Logique, Membre,
    Pour, Programme, Retourner, Selon, Si, TantQue, TexteFormate, Unaire,
)
from .erreurs import ErreurExecution, ErreurNck
from .modules import Chargeur
from .natifs import NATIFS, OPERATEURS_CLASSE, ClasseNck, EnumNck, FonctionNck, ModuleNck, ObjetNck, ParentNck, ValeurEnum, nom_type_valeur, vers_texte
from .types_nck import ENTIER, QUELCONQUE, TEXTE, Type, TypeClasse, est_dico, est_liste, valeur_compatible


def _repr_cle(k) -> str:
    return '"' + k + '"' if isinstance(k, str) else vers_texte(k)


# ---------- signaux de contrôle ----------

class _Retour(Exception):
    __slots__ = ("valeur",)

    def __init__(self, valeur):
        self.valeur = valeur


class _Arret(Exception):
    pass


class _Continue(Exception):
    pass


class Levee(Exception):
    """Erreur levée par `lever` (ou convertie depuis une erreur d'exécution) : transporte un objet Erreur."""

    def __init__(self, objet: ObjetNck, ligne: int = 0, colonne: int = 0):
        super().__init__(objet.champs.get("message"))
        self.objet = objet
        self.ligne = ligne
        self.colonne = colonne


def fabriquer_classe_erreur() -> ClasseNck:
    classe = ClasseNck("Erreur", ())
    classe.champs = ["message"]
    classe.types_champs = {"message": TEXTE}

    def construire(*args, **nommes):
        valeurs = dict(zip(classe.champs, args))
        valeurs.update(nommes)
        if "message" not in valeurs:
            raise ErreurExecution("il manque le champ obligatoire 'message' pour créer une 'Erreur'")
        if not isinstance(valeurs["message"], str):
            raise ErreurExecution(f"champ 'message' de 'Erreur' : texte attendu, mais {nom_type_valeur(valeurs['message'])} reçu")
        return ObjetNck(classe, {"message": valeurs["message"]})

    classe.construire = construire
    return classe


# ---------- environnement ----------

class Env:
    __slots__ = ("vars", "parent")

    def __init__(self, parent: "Env | None" = None):
        self.vars: dict[str, object] = {}
        self.parent = parent

    def chercher(self, nom: str):
        e: Env | None = self
        while e is not None:
            if nom in e.vars:
                return e.vars[nom]
            e = e.parent
        raise KeyError(nom)

    def affecter(self, nom: str, valeur) -> None:
        e: Env | None = self
        while e is not None:
            if nom in e.vars:
                e.vars[nom] = valeur
                return
            e = e.parent
        raise KeyError(nom)


Fn = Callable[[Env], object]


class Interpreteur:
    def __init__(self, fichier: str = "<entrée>", limite_recursion: int = 2000,
                 chargeur: Chargeur | None = None, base_env: "Env | None" = None):
        self.fichier = fichier
        self.limite_recursion = limite_recursion
        self.chargeur = chargeur if chargeur is not None else Chargeur()
        if base_env is None:
            # Environnement de base partagé par le programme principal et tous les modules : natifs + Erreur
            base_env = Env()
            for nom, natif in NATIFS.items():
                base_env.vars[nom] = natif
            base_env.vars["Erreur"] = fabriquer_classe_erreur()
        self.base_env = base_env
        self.classe_erreur = base_env.vars["Erreur"]
        self.global_env = Env(base_env)

    def erreur(self, message: str, noeud) -> ErreurExecution:
        return ErreurExecution(message, noeud.ligne, noeud.colonne, self.fichier)

    # ----- point d'entrée -----

    def executer(self, prog: Programme) -> None:
        corps = self.compiler_instructions(prog.instructions)
        ancienne_limite = sys.getrecursionlimit()
        sys.setrecursionlimit(max(ancienne_limite, self.limite_recursion * 6))
        try:
            corps(self.global_env)
        except Levee as l:
            o = l.objet
            nom = o.classe.nom
            message = vers_texte(o) if "texte" in o.classe.methodes else o.champs.get("message", "")
            raise ErreurExecution(f"{nom} non attrapée : {message}" if nom != "Erreur" else f"erreur non attrapée : {message}",
                                  l.ligne, l.colonne, self.fichier) from None
        except RecursionError:
            raise ErreurExecution("récursion trop profonde (dépassement de pile)", 0, 0, self.fichier) from None
        finally:
            sys.setrecursionlimit(ancienne_limite)

    # ----- instructions -----

    def compiler_instructions(self, instructions: list[Instr]) -> Fn:
        # Les fonctions sont « hissées » : elles existent dès le début de leur bloc,
        # ce qui permet de les appeler avant leur définition (comme l'autorise le vérificateur).
        ordonnees = ([i for i in instructions if isinstance(i, DeclClasse)]
                     + [i for i in instructions if isinstance(i, DeclFonction)]
                     + [i for i in instructions if not isinstance(i, (DeclFonction, DeclClasse))])
        fns = [self.instruction(i) for i in ordonnees]
        if len(fns) == 1:
            return fns[0]

        def bloc(env):
            for f in fns:
                f(env)
        return bloc

    def instruction(self, instr: Instr) -> Fn:
        return getattr(self, "i_" + type(instr).__name__)(instr)

    def _verif(self, t: Type, noeud, contexte: str):
        def verif(v):
            if not valeur_compatible(v, t):
                raise self.erreur(f"{contexte} : {t} attendu, mais {nom_type_valeur(v)} reçu ({vers_texte(v)})", noeud)
            return v
        return verif

    def i_DeclVariable(self, d: DeclVariable) -> Fn:
        nom = d.nom
        if d.valeur is None:
            def decl_vide(env):
                env.vars[nom] = None
            return decl_vide
        val = self.expression(d.valeur)
        if d.verif_runtime:  # type: ignore[attr-defined]
            verif = self._verif(d.type, d, f"variable '{nom}'")  # type: ignore[attr-defined]

            def decl_verif(env):
                env.vars[nom] = verif(val(env))
            return decl_verif

        def decl(env):
            env.vars[nom] = val(env)
        return decl

    def i_Affectation(self, a: Affectation) -> Fn:
        val = self.expression(a.valeur)
        if a.verif_runtime:  # type: ignore[attr-defined]
            verif = self._verif(a.type, a, "affectation")  # type: ignore[attr-defined]
            val0 = val
            val = lambda env: verif(val0(env))  # noqa: E731
        op = a.op
        if isinstance(a.cible, Identifiant):
            nom = a.cible.nom
            if op == "=":
                def aff(env):
                    e = env
                    while e is not None:
                        if nom in e.vars:
                            e.vars[nom] = val(env)
                            return
                        e = e.parent
                    raise KeyError(nom)
                return aff
            binop = self.operateur_binaire(op[0], a, a.cible.type, a.valeur.type)  # type: ignore[attr-defined]

            def aff_composee(env):
                e = env
                while e is not None:
                    if nom in e.vars:
                        e.vars[nom] = binop(e.vars[nom], val(env))
                        return
                    e = e.parent
                raise KeyError(nom)
            return aff_composee

        if isinstance(a.cible, Membre):
            objet = self.expression(a.cible.objet)
            champ = a.cible.nom
            noeud_m = a.cible

            def obtenir_objet(env):
                o = objet(env)
                if not isinstance(o, ObjetNck) or champ not in o.champs:
                    raise self.erreur(f"un {nom_type_valeur(o)} n'a pas de champ '{champ}'", noeud_m)
                return o

            if op == "=":
                def aff_membre(env):
                    obtenir_objet(env).champs[champ] = val(env)
                return aff_membre
            binop = self.operateur_binaire(op[0], a, a.cible.type, a.valeur.type)  # type: ignore[attr-defined]

            def aff_membre_composee(env):
                o = obtenir_objet(env)
                o.champs[champ] = binop(o.champs[champ], val(env))
            return aff_membre_composee

        assert isinstance(a.cible, Index)
        conteneur = self.expression(a.cible.cible)
        index = self.expression(a.cible.index)
        noeud = a.cible

        if est_dico(a.cible.cible.type):  # type: ignore[attr-defined]
            if op == "=":
                def aff_cle(env):
                    conteneur(env)[index(env)] = val(env)
                return aff_cle
            binop = self.operateur_binaire(op[0], a, a.cible.type, a.valeur.type)  # type: ignore[attr-defined]

            def aff_cle_composee(env):
                d = conteneur(env)
                k = index(env)
                if k not in d:
                    raise self.erreur(f"clé {_repr_cle(k)} introuvable dans le dictionnaire", noeud.index)
                d[k] = binop(d[k], val(env))
            return aff_cle_composee

        def indexer(env):
            c = conteneur(env)
            i = index(env)
            if isinstance(c, dict):
                return c, i
            if not isinstance(c, list):
                raise self.erreur(f"impossible de modifier un élément d'un {nom_type_valeur(c)}", noeud)
            if not isinstance(i, int) or isinstance(i, bool):
                raise self.erreur(f"l'index doit être un entier, mais c'est un {nom_type_valeur(i)}", noeud.index)
            if not -len(c) <= i < len(c):
                raise self.erreur(f"index {i} hors limites (la liste a {len(c)} élément(s))", noeud.index)
            return c, i

        if op == "=":
            def aff_index(env):
                c, i = indexer(env)
                c[i] = val(env)
            return aff_index
        binop = self.operateur_binaire(op[0], a, a.cible.type, a.valeur.type)  # type: ignore[attr-defined]

        def aff_index_composee(env):
            c, i = indexer(env)
            c[i] = binop(c[i], val(env))
        return aff_index_composee

    def i_ExprInstr(self, e: ExprInstr) -> Fn:
        return self.expression(e.expr)

    def i_Bloc(self, b: Bloc) -> Fn:
        return self.compiler_instructions(b.instructions)

    def i_Si(self, s: Si) -> Fn:
        cond = self.expression(s.condition)
        alors = self.compiler_instructions(s.alors.instructions)
        if s.sinon is None:
            def si(env):
                if cond(env):
                    alors(env)
            return si
        sinon = self.instruction(s.sinon) if isinstance(s.sinon, Si) else self.compiler_instructions(s.sinon.instructions)

        def si_sinon(env):
            if cond(env):
                alors(env)
            else:
                sinon(env)
        return si_sinon

    def i_TantQue(self, t: TantQue) -> Fn:
        cond = self.expression(t.condition)
        corps = self.compiler_instructions(t.corps.instructions)
        utilise_controle = _contient_controle(t.corps)
        if not utilise_controle:
            def tantque(env):
                while cond(env):
                    corps(env)
            return tantque

        def tantque_controle(env):
            while cond(env):
                try:
                    corps(env)
                except _Continue:
                    continue
                except _Arret:
                    break
        return tantque_controle

    def i_Pour(self, p: Pour) -> Fn:
        iterable = self.expression(p.iterable)
        corps = self.compiler_instructions(p.corps.instructions)
        nom = p.variable
        utilise_controle = _contient_controle(p.corps)
        noeud = p.iterable

        nom2 = p.variable2

        def obtenir(env):
            it = iterable(env)
            if isinstance(it, dict):
                return list(it.items()) if nom2 is not None else list(it)   # copie : le corps peut modifier le dico
            if isinstance(it, bool) or not isinstance(it, (list, str, int)):
                raise self.erreur(f"impossible de parcourir un {nom_type_valeur(it)}", noeud)
            if isinstance(it, int):
                it = range(it)
            return enumerate(it) if nom2 is not None else it

        if nom2 is not None:
            def pour2(env):
                vars_ = env.vars
                for v1, v2 in obtenir(env):
                    vars_[nom] = v1
                    vars_[nom2] = v2
                    try:
                        corps(env)
                    except _Continue:
                        continue
                    except _Arret:
                        break
            return pour2

        if not utilise_controle:
            def pour(env):
                vars_ = env.vars
                for v in obtenir(env):
                    vars_[nom] = v
                    corps(env)
            return pour

        def pour_controle(env):
            vars_ = env.vars
            for v in obtenir(env):
                vars_[nom] = v
                try:
                    corps(env)
                except _Continue:
                    continue
                except _Arret:
                    break
        return pour_controle

    def i_DeclClasse(self, c: DeclClasse) -> Fn:
        info = c.info  # type: ignore[attr-defined]
        nom = c.nom
        parent_nom = c.parent
        defauts = {ch.nom: self.expression(ch.defaut) for ch in c.champs if ch.defaut is not None}
        types_champs = {ch.nom: ch.type for ch in c.champs}  # type: ignore[attr-defined]
        fabriques = {m.nom: self.fabrique_fonction(m, methode=True)
                     for m in c.methodes if m.corps is not None and not getattr(m, "statique", False)}
        statiques = {m.nom: self.fabrique_fonction(m) for m in c.methodes if getattr(m, "statique", False)}
        constantes = [(cst.nom, self.expression(cst.valeur)) for cst in getattr(c, "constantes", [])]
        abstraites = set(info.abstraites)
        erreur = self.erreur

        def decl(env):
            classe = ClasseNck(nom, info.type.ancetres)
            if parent_nom is not None:
                parent: ClasseNck = env.chercher(parent_nom)
                classe.parent = parent
                classe.champs = list(parent.champs)
                classe.types_champs = dict(parent.types_champs)
                classe.defauts = dict(parent.defauts)
                classe.methodes = dict(parent.methodes)
                classe.statiques = dict(parent.statiques)
                classe.constantes = dict(parent.constantes)
            classe.abstraites = abstraites
            classe.champs += [ch.nom for ch in c.champs]
            classe.types_champs.update(types_champs)
            for k, f in defauts.items():
                classe.defauts[k] = (lambda f=f: f(env))
            for k, f in constantes:
                classe.constantes[k] = f(env)
            for k, fab in fabriques.items():
                classe.methodes[k] = self._appelable(fab(env, classe), k, c)
            for k, fab in statiques.items():
                classe.statiques[k] = fab(env, classe)
            champs = classe.champs
            tchamps = classe.types_champs
            dflt = classe.defauts
            valider = classe.methodes.get("valider")

            def construire(*args, **nommes):
                if abstraites:
                    raise ErreurExecution(f"'{nom}' est abstraite (méthodes non implémentées : {', '.join(sorted(abstraites))})")
                valeurs = dict(zip(champs, args))
                valeurs.update(nommes)
                obj = {}
                for k in champs:
                    if k in valeurs:
                        v = valeurs[k]
                    elif k in dflt:
                        v = dflt[k]()
                    else:
                        raise ErreurExecution(f"il manque le champ obligatoire '{k}' pour créer un '{nom}'")
                    if not valeur_compatible(v, tchamps[k]):
                        raise ErreurExecution(
                            f"champ '{k}' de '{nom}' : {tchamps[k]} attendu, mais {nom_type_valeur(v)} reçu ({vers_texte(v)})")
                    obj[k] = v
                o = ObjetNck(classe, obj)
                if valider is not None:
                    valider(o)
                return o

            classe.construire = construire
            env.vars[nom] = classe
        return decl

    def i_DeclEnum(self, e: DeclEnum) -> Fn:
        nom, valeurs = e.nom, list(e.valeurs)

        def decl(env):
            env.vars[nom] = EnumNck(nom, valeurs)
        return decl

    def _valeurs_multiples(self, valeurs, n: int, noeud):
        erreur = self.erreur
        if len(valeurs) == n:
            fns = [self.expression(v) for v in valeurs]
            return lambda env: [f(env) for f in fns]
        f0 = self.expression(valeurs[0])

        def depuis_liste(env):
            v = f0(env)
            if not isinstance(v, list):
                raise erreur(f"pour déstructurer, la valeur doit être une liste, mais c'est un {nom_type_valeur(v)}", noeud)
            if len(v) != n:
                raise erreur(f"déstructuration impossible : {n} variable(s) mais la liste contient {len(v)} élément(s)", noeud)
            return v
        return depuis_liste

    def i_DeclMultiple(self, d: DeclMultiple) -> Fn:
        noms = list(d.noms)
        types = d.types  # type: ignore[attr-defined]
        valeurs = self._valeurs_multiples(d.valeurs, len(noms), d)
        erreur = self.erreur

        def decl(env):
            vs = valeurs(env)
            for nom, t, v in zip(noms, types, vs):
                if t != QUELCONQUE and not valeur_compatible(v, t):
                    raise erreur(f"'{nom}' est de type {t}, mais reçoit un {nom_type_valeur(v)} ({vers_texte(v)})", d)
                env.vars[nom] = v
        return decl

    def i_AffectationMultiple(self, a: AffectationMultiple) -> Fn:
        valeurs = self._valeurs_multiples(a.valeurs, len(a.cibles), a)
        types = a.types  # type: ignore[attr-defined]
        affecteurs = [self._affecteur(c) for c in a.cibles]
        erreur = self.erreur

        def affecter(env):
            vs = valeurs(env)
            for aff, t, v, c in zip(affecteurs, types, vs, a.cibles):
                if t != QUELCONQUE and not valeur_compatible(v, t):
                    raise erreur(f"impossible d'affecter un {nom_type_valeur(v)} ({vers_texte(v)}) à une cible de type {t}", a)
                aff(env, v)
        return affecter

    def _affecteur(self, cible):
        """Retourne fn(env, valeur) qui range la valeur dans la cible (variable, champ ou élément)."""
        erreur = self.erreur
        if isinstance(cible, Identifiant):
            nom = cible.nom

            def aff_var(env, v):
                e = env
                while e is not None:
                    if nom in e.vars:
                        e.vars[nom] = v
                        return
                    e = e.parent
                raise KeyError(nom)
            return aff_var
        if isinstance(cible, Membre):
            objet, champ = self.expression(cible.objet), cible.nom

            def aff_champ(env, v):
                o = objet(env)
                if not isinstance(o, ObjetNck) or champ not in o.champs:
                    raise erreur(f"un {nom_type_valeur(o)} n'a pas de champ '{champ}'", cible)
                o.champs[champ] = v
            return aff_champ
        conteneur, index = self.expression(cible.cible), self.expression(cible.index)

        def aff_index(env, v):
            c, i = conteneur(env), index(env)
            if isinstance(c, dict):
                c[i] = v
                return
            if not isinstance(c, list):
                raise erreur(f"impossible de modifier un élément d'un {nom_type_valeur(c)}", cible)
            if not isinstance(i, int) or isinstance(i, bool):
                raise erreur(f"l'index doit être un entier, mais c'est un {nom_type_valeur(i)}", cible.index)
            if not -len(c) <= i < len(c):
                raise erreur(f"index {i} hors limites (liste de {len(c)} éléments)", cible.index)
            c[i] = v
        return aff_index

    def e_Conditionnelle(self, c: Conditionnelle) -> Fn:
        cond, alors, sinon = self.expression(c.condition), self.expression(c.alors), self.expression(c.sinon)
        return lambda env: alors(env) if cond(env) else sinon(env)

    def i_DeclFonction(self, f: DeclFonction) -> Fn:
        fabriquer = self.fabrique_fonction(f)
        nom = f.nom

        def decl(env):
            env.vars[nom] = fabriquer(env)
        return decl

    @staticmethod
    def _appelable(v, nom: str, noeud):
        """Transforme une valeur (FonctionNck ou callable) en callable Python pour les méthodes."""
        if isinstance(v, FonctionNck):
            return v.appeler
        return v

    def e_FonctionAnonyme(self, fa: FonctionAnonyme) -> Fn:
        if fa.expression is not None:
            if getattr(fa, "corps_est_instruction", False):
                corps = Bloc([ExprInstr(fa.expression, ligne=fa.ligne, colonne=fa.colonne)], ligne=fa.ligne, colonne=fa.colonne)
            else:
                r = Retourner(fa.expression, ligne=fa.ligne, colonne=fa.colonne)
                r.verif_runtime = False  # type: ignore[attr-defined]
                corps = Bloc([r], ligne=fa.ligne, colonne=fa.colonne)
        else:
            corps = fa.corps
        decl = DeclFonction("fonction anonyme", fa.parametres, fa.type_retour, corps, ligne=fa.ligne, colonne=fa.colonne)
        fabriquer = self.fabrique_fonction(decl)
        return lambda env: fabriquer(env)

    def fabrique_fonction(self, f: DeclFonction, methode: bool = False):
        """Retourne `fabriquer(env_def, classe=None) -> FonctionNck`. Une méthode reçoit l'objet (`soi`) en premier argument.
        Les décorateurs (`@deco`) sont appliqués à la définition : `f = deco(f)`."""
        corps = self.compiler_instructions(f.corps.instructions)
        variadique = bool(f.parametres) and f.parametres[-1].variadique
        noms = (["soi"] if methode else []) + [p.nom for p in f.parametres]
        defauts = [(p.nom, self.expression(p.defaut)) for p in f.parametres if p.defaut is not None]
        n_fixes = len(noms) - (1 if variadique else 0)
        minimum = n_fixes - len(defauts)
        nom = f.nom
        a_retour = _contient_retour(f.corps)
        limite = self.limite_recursion
        profondeur = [0]
        decorateurs = [self.expression(d) for d in reversed(getattr(f, "decorateurs", []))]
        noeud_f = f

        def fabriquer(env_def: Env, classe: ClasseNck | None = None) -> FonctionNck:
            a_parent = methode and classe is not None and classe.parent is not None

            def appeler(*args):
                env = Env(env_def)
                if variadique:
                    env.vars.update(zip(noms, args))
                    env.vars[noms[-1]] = list(args[n_fixes:])
                else:
                    env.vars.update(zip(noms, args))
                    if len(args) > len(noms):
                        raise self.erreur(f"'{nom}' attend au plus {len(noms) - (1 if methode else 0)} argument(s), mais {len(args) - (1 if methode else 0)} fourni(s)", f)
                if len(args) < n_fixes:
                    if len(args) < minimum:
                        raise self.erreur(f"'{nom}' attend au moins {minimum - (1 if methode else 0)} argument(s), mais {len(args) - (1 if methode else 0)} fourni(s)", f)
                    for pn, pd in defauts[len(args) - minimum:]:
                        env.vars[pn] = pd(env_def)
                if a_parent:
                    env.vars["parent"] = ParentNck(args[0], classe.parent)
                profondeur[0] += 1
                if profondeur[0] > limite:
                    profondeur[0] = 0
                    raise self.erreur(f"récursion trop profonde dans '{nom}' (plus de {limite} appels imbriqués)", f)
                try:
                    if a_retour:
                        try:
                            corps(env)
                        except _Retour as r:
                            return r.valeur
                        return None
                    corps(env)
                    return None
                finally:
                    profondeur[0] -= 1
            fn = FonctionNck(nom, -1 if variadique else len(noms), appeler)
            fn.arite_min = minimum
            if decorateurs:
                resultat = fn
                for d in decorateurs:
                    deco = d(env_def)
                    resultat = self._appeler_valeur(deco, [resultat], noeud_f, "décorateur")
                    if not (isinstance(resultat, FonctionNck) or callable(resultat)):
                        raise self.erreur(f"le décorateur de '{nom}' doit retourner une fonction, mais a retourné un {nom_type_valeur(resultat)}", noeud_f)
                if not isinstance(resultat, FonctionNck):
                    resultat = FonctionNck(nom, -1, resultat)
                return resultat
            return fn

        return fabriquer

    def i_Retourner(self, r: Retourner) -> Fn:
        if r.valeur is None:
            def ret_vide(env):
                raise _Retour(None)
            return ret_vide
        val = self.expression(r.valeur)
        if r.verif_runtime:  # type: ignore[attr-defined]
            verif = self._verif(r.type_attendu, r, "valeur de retour")  # type: ignore[attr-defined]
            val0 = val
            val = lambda env: verif(val0(env))  # noqa: E731

        def ret(env):
            raise _Retour(val(env))
        return ret

    def i_Importer(self, imp: Importer) -> Fn:
        m = imp.module  # type: ignore[attr-defined]
        alias, noms = imp.alias, imp.noms
        chargeur, base_env = self.chargeur, self.base_env

        def importer(env):
            if not m.execute:
                m.execute = True
                sous = Interpreteur(m.chemin, self.limite_recursion, chargeur, base_env)
                sous.executer(m.programme)
                m.env = sous.global_env
            if noms is not None:
                for n in noms:
                    env.vars[n] = m.env.vars[n]
            else:
                env.vars[alias] = ModuleNck(m.nom, m.env)
        return importer

    def i_Selon(self, s: Selon) -> Fn:
        sujet = self.expression(s.sujet)
        cas = [([self.expression(v) for v in c.valeurs], self.compiler_instructions(c.corps.instructions)) for c in s.cas]
        sinon = self.compiler_instructions(s.sinon.instructions) if s.sinon is not None else None
        # Optimisation : si tous les cas sont des littéraux, table de correspondance.
        if all(isinstance(v, Litteral) and not isinstance(v.valeur, float) for c in s.cas for v in c.valeurs):
            table = {}
            for c, (_, bloc) in zip(s.cas, cas):
                for v in c.valeurs:
                    table.setdefault((type(v.valeur), v.valeur), bloc)

            def selon_table(env):
                v = sujet(env)
                bloc = table.get((type(v), v))
                if bloc is not None:
                    bloc(env)
                elif sinon is not None:
                    sinon(env)
            return selon_table

        def selon(env):
            v = sujet(env)
            for valeurs, bloc in cas:
                for f in valeurs:
                    if f(env) == v:
                        bloc(env)
                        return
            if sinon is not None:
                sinon(env)
        return selon

    def i_Lever(self, l: Lever) -> Fn:
        val = self.expression(l.valeur)
        classe_erreur = self.classe_erreur
        ligne, colonne = l.ligne, l.colonne
        erreur = self.erreur

        def lever(env):
            v = val(env)
            if isinstance(v, str):
                v = ObjetNck(classe_erreur, {"message": v})
            elif not (isinstance(v, ObjetNck) and (v.classe.nom == "Erreur" or "Erreur" in v.classe.ancetres)):
                raise erreur(f"'lever' attend un texte ou une Erreur, mais {nom_type_valeur(v)} fourni", l)
            raise Levee(v, ligne, colonne)
        return lever

    def i_Essayer(self, e: Essayer) -> Fn:
        corps = self.compiler_instructions(e.corps.instructions)
        clauses = [(cl.type.nom, cl.variable, self.compiler_instructions(cl.corps.instructions))  # type: ignore[attr-defined]
                   for cl in e.clauses]
        enfin = self.compiler_instructions(e.enfin.instructions) if e.enfin is not None else None
        classe_erreur = self.classe_erreur

        def attraper(env, objet: ObjetNck, exc: BaseException):
            for nom_type, var, bloc in clauses:
                if objet.classe.nom == nom_type or nom_type in objet.classe.ancetres:
                    env.vars[var] = objet
                    bloc(env)
                    return
            raise exc

        def essayer(env):
            try:
                try:
                    corps(env)
                except Levee as l:
                    attraper(env, l.objet, l)
                except ErreurExecution as ex:
                    attraper(env, ObjetNck(classe_erreur, {"message": ex.message}), ex)
            finally:
                if enfin is not None:
                    enfin(env)
        return essayer

    def i_Arreter(self, a: Arreter) -> Fn:
        def arreter(env):
            raise _Arret()
        return arreter

    def i_Continuer(self, c: Continuer) -> Fn:
        def continuer(env):
            raise _Continue()
        return continuer

    # ----- expressions -----

    def expression(self, e: Expr) -> Fn:
        return getattr(self, "e_" + type(e).__name__)(e)

    def e_Litteral(self, l: Litteral) -> Fn:
        v = l.valeur
        return lambda env: v

    def e_TexteFormate(self, t: TexteFormate) -> Fn:
        parties = [(p if isinstance(p, str) else self.expression(p)) for p in t.parties]

        def formater(env):
            return "".join(p if isinstance(p, str) else vers_texte(p(env)) for p in parties)
        return formater

    def e_ListeLit(self, l: ListeLit) -> Fn:
        elems = [self.expression(x) for x in l.elements]
        return lambda env: [f(env) for f in elems]

    def e_DicoLit(self, d: DicoLit) -> Fn:
        entrees = [(self.expression(k), self.expression(v)) for k, v in d.entrees]
        return lambda env: {k(env): v(env) for k, v in entrees}

    def e_Identifiant(self, i: Identifiant) -> Fn:
        nom = i.nom

        def ident(env):
            e = env
            while e is not None:
                vars_ = e.vars
                if nom in vars_:
                    return vars_[nom]
                e = e.parent
            raise self.erreur(f"variable '{nom}' inconnue", i)
        return ident

    def e_Unaire(self, u: Unaire) -> Fn:
        op = self.expression(u.operande)
        if u.op == "non":
            def non(env):
                v = op(env)
                if v is True:
                    return False
                if v is False:
                    return True
                raise self.erreur(f"'non' attend un booleen, mais reçoit un {nom_type_valeur(v)}", u)
            return non

        def neg(env):
            v = op(env)
            if isinstance(v, bool) or not isinstance(v, (int, float)):
                raise self.erreur(f"'-' attend un nombre, mais reçoit un {nom_type_valeur(v)}", u)
            return -v
        return neg

    def e_Logique(self, l: Logique) -> Fn:
        g = self.expression(l.gauche)
        d = self.expression(l.droite)
        if l.op == "et":
            return lambda env: g(env) and d(env)
        return lambda env: g(env) or d(env)

    def e_Binaire(self, b: Binaire) -> Fn:
        g = self.expression(b.gauche)
        d = self.expression(b.droite)
        tg = b.gauche.type  # type: ignore[attr-defined]
        td = b.droite.type  # type: ignore[attr-defined]
        op = b.op
        if op == "??":
            def sinon_nul(env):
                v = g(env)
                return d(env) if v is None else v
            return sinon_nul
        if op == "..":
            erreur = self.erreur

            def plage(env):
                a, z = g(env), d(env)
                if not isinstance(a, int) or not isinstance(z, int) or isinstance(a, bool) or isinstance(z, bool):
                    raise erreur(f"'..' attend deux entiers, mais reçoit un {nom_type_valeur(a)} et un {nom_type_valeur(z)}", b)
                return list(range(a, z))
            return plage
        if isinstance(tg, TypeClasse) or isinstance(td, TypeClasse):
            fn = self.operateur_objet(op, b)
            return lambda env: fn(g(env), d(env))
        # Chemins rapides quand les types sont connus statiquement.
        if op == "+" and tg == ENTIER and td == ENTIER:
            return lambda env: g(env) + d(env)
        if op == "-" and tg == ENTIER and td == ENTIER:
            return lambda env: g(env) - d(env)
        if op == "*" and tg == ENTIER and td == ENTIER:
            return lambda env: g(env) * d(env)
        if op == "<" and tg == ENTIER and td == ENTIER:
            return lambda env: g(env) < d(env)
        if op == "<=" and tg == ENTIER and td == ENTIER:
            return lambda env: g(env) <= d(env)
        if op == ">" and tg == ENTIER and td == ENTIER:
            return lambda env: g(env) > d(env)
        if op == ">=" and tg == ENTIER and td == ENTIER:
            return lambda env: g(env) >= d(env)
        if op == "==":
            return lambda env: g(env) == d(env)
        if op == "!=":
            return lambda env: g(env) != d(env)
        if op == "+" and tg == TEXTE and td == TEXTE:
            return lambda env: g(env) + d(env)
        fn = self.operateur_binaire(op, b, tg, td)
        return lambda env: fn(g(env), d(env))

    def operateur_objet(self, op: str, noeud):
        """`a + b` sur des objets : appelle `a.plus(b)` ; `a < b` : `a.inferieur(b)` ; `a == b` : `a.egal(b)`…"""
        erreur = self.erreur
        nom = OPERATEURS_CLASSE.get(op)
        generique = self.operateur_binaire(op, noeud, QUELCONQUE, QUELCONQUE) if op not in ("==", "!=") else None

        def methode(o, nom_m):
            m = o.classe.methodes.get(nom_m) if isinstance(o, ObjetNck) else None
            if m is None:
                raise erreur(f"'{op}' n'est pas défini pour un {nom_type_valeur(o)} : ajoutez une méthode '{nom_m}' à la classe", noeud)
            return m

        if op == "==":
            return lambda a, b: a == b
        if op == "!=":
            return lambda a, b: a != b
        if op == "<":
            return lambda a, b: bool(methode(a, "inferieur")(a, b))
        if op == ">":
            return lambda a, b: bool(methode(b, "inferieur")(b, a))
        if op == "<=":
            return lambda a, b: bool(methode(a, "inferieur")(a, b)) or a == b
        if op == ">=":
            return lambda a, b: bool(methode(b, "inferieur")(b, a)) or a == b

        def operation(a, b):
            if isinstance(a, ObjetNck):
                return methode(a, nom)(a, b)
            return generique(a, b)
        return operation

    def operateur_binaire(self, op: str, noeud, tg: Type, td: Type):
        """Opérateur binaire générique avec vérifications à l'exécution."""
        erreur = self.erreur

        def est_nombre(v):
            return isinstance(v, (int, float)) and not isinstance(v, bool)

        if op == "+":
            def plus(a, b):
                if est_nombre(a) and est_nombre(b):
                    return a + b
                if isinstance(a, str) and isinstance(b, str):
                    return a + b
                if isinstance(a, list) and isinstance(b, list):
                    return a + b
                raise erreur(f"impossible d'additionner un {nom_type_valeur(a)} et un {nom_type_valeur(b)}", noeud)
            return plus
        if op == "-":
            def moins(a, b):
                if est_nombre(a) and est_nombre(b):
                    return a - b
                raise erreur(f"'-' attend deux nombres, mais reçoit un {nom_type_valeur(a)} et un {nom_type_valeur(b)}", noeud)
            return moins
        if op == "*":
            def fois(a, b):
                if est_nombre(a) and est_nombre(b):
                    return a * b
                if (isinstance(a, (str, list)) and isinstance(b, int)) or (isinstance(a, int) and isinstance(b, (str, list))):
                    return a * b
                raise erreur(f"impossible de multiplier un {nom_type_valeur(a)} et un {nom_type_valeur(b)}", noeud)
            return fois
        if op == "/":
            def div(a, b):
                if est_nombre(a) and est_nombre(b):
                    if b == 0:
                        raise erreur("division par zéro", noeud)
                    return a / b
                raise erreur(f"'/' attend deux nombres, mais reçoit un {nom_type_valeur(a)} et un {nom_type_valeur(b)}", noeud)
            return div
        if op == "%":
            def mod(a, b):
                if est_nombre(a) and est_nombre(b):
                    if b == 0:
                        raise erreur("modulo par zéro", noeud)
                    return a % b
                raise erreur(f"'%' attend deux nombres, mais reçoit un {nom_type_valeur(a)} et un {nom_type_valeur(b)}", noeud)
            return mod
        comparaisons = {
            "<": lambda a, b: a < b, ">": lambda a, b: a > b,
            "<=": lambda a, b: a <= b, ">=": lambda a, b: a >= b,
        }
        if op in comparaisons:
            cmp = comparaisons[op]

            def comparer(a, b):
                if (est_nombre(a) and est_nombre(b)) or (isinstance(a, str) and isinstance(b, str)):
                    return cmp(a, b)
                if isinstance(a, ValeurEnum) and isinstance(b, ValeurEnum) and a.enum == b.enum:
                    return cmp(a.indice, b.indice)
                raise erreur(f"'{op}' ne peut pas comparer un {nom_type_valeur(a)} et un {nom_type_valeur(b)}", noeud)
            return comparer
        if op == "==":
            return lambda a, b: a == b
        if op == "!=":
            return lambda a, b: a != b
        raise erreur(f"opérateur inconnu '{op}'", noeud)

    def e_Index(self, i: Index) -> Fn:
        cible = self.expression(i.cible)
        index = self.expression(i.index)
        erreur = self.erreur

        def indexer(env):
            c = cible(env)
            k = index(env)
            if isinstance(c, dict):
                try:
                    return c[k]
                except KeyError:
                    raise erreur(f"clé {_repr_cle(k)} introuvable dans le dictionnaire", i.index) from None
                except TypeError:
                    raise erreur(f"une clé de dictionnaire ne peut pas être un {nom_type_valeur(k)}", i.index) from None
            if not isinstance(c, (list, str)):
                raise erreur(f"impossible d'indexer un {nom_type_valeur(c)}", i)
            if isinstance(k, bool) or not isinstance(k, int):
                raise erreur(f"l'index doit être un entier, mais c'est un {nom_type_valeur(k)}", i.index)
            try:
                return c[k]
            except IndexError:
                genre = "la liste" if isinstance(c, list) else "le texte"
                raise erreur(f"index {k} hors limites ({genre} a {len(c)} élément(s))", i.index) from None
        return indexer

    def e_Membre(self, m: Membre) -> Fn:
        objet = self.expression(m.objet)
        nom = m.nom
        erreur = self.erreur

        def membre(env):
            o = objet(env)
            if isinstance(o, ObjetNck):
                champs = o.champs
                if nom in champs:
                    return champs[nom]
                meth = o.classe.methodes.get(nom)
                if meth is not None:
                    return FonctionNck(f"{o.classe.nom}.{nom}", -1, lambda *args: meth(o, *args))
                raise erreur(f"la classe '{o.classe.nom}' n'a pas de champ ni de méthode '{nom}'", m)
            if isinstance(o, ModuleNck):
                try:
                    return o.env.vars[nom]
                except KeyError:
                    raise erreur(f"le module '{o.nom}' ne définit pas '{nom}'", m) from None
            if isinstance(o, EnumNck):
                if nom in o.par_nom:
                    return o.par_nom[nom]
                if nom == "valeurs":
                    return list(o.valeurs)
                raise erreur(f"l'énumération '{o.nom}' n'a pas de valeur '{nom}'", m)
            if isinstance(o, ValeurEnum):
                if nom == "nom":
                    return o.nom
                if nom == "indice":
                    return o.indice
                raise erreur(f"une valeur de '{o.enum}' n'a pas de champ '{nom}'", m)
            if isinstance(o, ClasseNck):
                if nom in o.statiques:
                    return o.statiques[nom]
                if nom in o.constantes:
                    return o.constantes[nom]
                raise erreur(f"la classe '{o.nom}' n'a pas de méthode statique ni de constante '{nom}'", m)
            if isinstance(o, ParentNck):
                meth = o.classe.methodes.get(nom)
                if meth is not None:
                    obj = o.objet
                    return FonctionNck(f"{o.classe.nom}.{nom}", -1, lambda *args: meth(obj, *args))
                if nom in o.objet.champs:
                    return o.objet.champs[nom]
                raise erreur(f"la classe parente '{o.classe.nom}' n'a pas de champ ni de méthode '{nom}'", m)
            raise erreur(f"un {nom_type_valeur(o)} n'a pas de champ ni de méthode '{nom}'", m)
        return membre

    def _compiler_arguments(self, arguments):
        """Retourne (liste de fonctions par argument ou None si étalement, fonction env -> liste de valeurs)."""
        if not any(isinstance(x, Etalement) for x in arguments):
            args = [self.expression(x) for x in arguments]
            return args, (lambda env: [g(env) for g in args])
        parties = [(isinstance(x, Etalement), self.expression(x.valeur if isinstance(x, Etalement) else x)) for x in arguments]
        erreur = self.erreur

        def evaluer(env):
            valeurs = []
            for etale, g in parties:
                v = g(env)
                if etale:
                    if not isinstance(v, list):
                        raise erreur(f"'...' attend une liste, mais reçoit un {nom_type_valeur(v)}", arguments[0])
                    valeurs.extend(v)
                else:
                    valeurs.append(v)
            return valeurs
        return None, evaluer

    def e_Appel(self, a: Appel) -> Fn:
        args, evaluer_args = self._compiler_arguments(a.arguments)
        natif = a.natif  # type: ignore[attr-defined]
        erreur = self.erreur

        classe_nom = getattr(a, "classe", None)
        if classe_nom is not None:
            nommes = [(n, self.expression(e)) for n, e in a.nommes]
            cible_classe = self.expression(a.cible)

            def construire(env):
                classe = cible_classe(env)
                try:
                    return classe.construire(*[f(env) for f in args], **{n: f(env) for n, f in nommes})
                except ErreurNck as exc:
                    if exc.ligne == 0:
                        exc.ligne, exc.colonne, exc.fichier = a.ligne, a.colonne, self.fichier
                    raise
            return construire

        if isinstance(a.cible, Membre) and getattr(a, "methode_native", False):
            # `liste.ajouter(x)` ≡ `ajouter(liste, x)`
            objet = self.expression(a.cible.objet)
            fn = natif.fn

            def appel_methode_native(env):
                try:
                    return fn(objet(env), *[g(env) for g in args])
                except ErreurNck as exc:
                    if exc.ligne == 0:
                        exc.ligne, exc.colonne, exc.fichier = a.ligne, a.colonne, self.fichier
                    raise
            return appel_methode_native

        if isinstance(a.cible, Membre):
            # Appel de méthode : évite de créer une fonction liée à chaque appel.
            objet = self.expression(a.cible.objet)
            nom_m = a.cible.nom
            noeud_m = a.cible

            def appel_methode(env):
                o = objet(env)
                if isinstance(o, ObjetNck):
                    meth = o.classe.methodes.get(nom_m)
                    if meth is not None:
                        return meth(o, *evaluer_args(env))
                    f = o.champs.get(nom_m)
                    if f is not None:
                        return self._appeler_valeur(f, evaluer_args(env), a, nom_m)
                    raise erreur(f"la classe '{o.classe.nom}' n'a pas de méthode '{nom_m}'", noeud_m)
                if isinstance(o, ModuleNck):
                    f = o.env.vars.get(nom_m)
                    if f is None:
                        raise erreur(f"le module '{o.nom}' ne définit pas '{nom_m}'", noeud_m)
                    return self._appeler_valeur(f, evaluer_args(env), a, nom_m)
                if isinstance(o, ClasseNck):
                    f = o.statiques.get(nom_m)
                    if f is None:
                        raise erreur(f"la classe '{o.nom}' n'a pas de méthode statique '{nom_m}'", noeud_m)
                    return self._appeler_valeur(f, evaluer_args(env), a, nom_m)
                if isinstance(o, ParentNck):
                    meth = o.classe.methodes.get(nom_m)
                    if meth is None:
                        raise erreur(f"la classe parente '{o.classe.nom}' n'a pas de méthode '{nom_m}'", noeud_m)
                    return meth(o.objet, *evaluer_args(env))
                if nom_m in NATIFS:   # valeur 'quelconque' : notation méthode résolue à l'exécution
                    try:
                        return NATIFS[nom_m].fn(o, *evaluer_args(env))
                    except ErreurNck as exc:
                        if exc.ligne == 0:
                            exc.ligne, exc.colonne, exc.fichier = a.ligne, a.colonne, self.fichier
                        raise
                raise erreur(f"un {nom_type_valeur(o)} n'a pas de méthode '{nom_m}'", noeud_m)
            return appel_methode

        def enrichir(exc: ErreurNck):
            if exc.ligne == 0:
                exc.ligne, exc.colonne, exc.fichier = a.ligne, a.colonne, self.fichier
            return exc

        if natif is not None:
            fn = natif.fn
            n = len(args)
            if n == 0:
                def appel0(env):
                    try:
                        return fn()
                    except ErreurNck as exc:
                        raise enrichir(exc)
                return appel0
            if n == 1:
                a0 = args[0]

                def appel1(env):
                    try:
                        return fn(a0(env))
                    except ErreurNck as exc:
                        raise enrichir(exc)
                return appel1
            if n == 2:
                a0, a1 = args

                def appel2(env):
                    try:
                        return fn(a0(env), a1(env))
                    except ErreurNck as exc:
                        raise enrichir(exc)
                return appel2

            def appel_natif(env):
                try:
                    return fn(*[f(env) for f in args])
                except ErreurNck as exc:
                    raise enrichir(exc)
            return appel_natif

        cible = self.expression(a.cible)
        verifs = a.verifs_runtime  # type: ignore[attr-defined]
        nom = a.cible.nom if isinstance(a.cible, Identifiant) else "fonction"

        def appel(env):
            return self._appeler_valeur(cible(env), evaluer_args(env), a, nom)
        return appel

    def _appeler_valeur(self, f, valeurs: list, noeud, nom: str):
        if isinstance(f, FonctionNck):
            if f.arite >= 0 and not (f.arite_min <= len(valeurs) <= f.arite):
                attendu = f"{f.arite}" if f.arite_min == f.arite else f"entre {f.arite_min} et {f.arite}"
                raise self.erreur(f"'{f.nom}' attend {attendu} argument(s), mais {len(valeurs)} fourni(s)", noeud)
            return f.appeler(*valeurs)
        if callable(f):
            try:
                return f(*valeurs)
            except ErreurNck as exc:
                if exc.ligne == 0:
                    exc.ligne, exc.colonne, exc.fichier = noeud.ligne, noeud.colonne, self.fichier
                raise
        raise self.erreur(f"'{nom}' n'est pas une fonction (c'est un {nom_type_valeur(f)})", noeud)


# ---------- analyses auxiliaires ----------

def _contient_controle(bloc: Bloc) -> bool:
    """Le bloc contient-il arreter/continuer (hors boucles et fonctions imbriquées) ?"""
    def visiter(instrs) -> bool:
        for i in instrs:
            if isinstance(i, (Arreter, Continuer)):
                return True
            if isinstance(i, Si):
                if visiter(i.alors.instructions):
                    return True
                if i.sinon is not None:
                    if isinstance(i.sinon, Si):
                        if visiter([i.sinon]):
                            return True
                    elif visiter(i.sinon.instructions):
                        return True
            elif isinstance(i, Essayer) and _visiter_essayer(i, visiter):
                return True
            elif isinstance(i, Selon) and _visiter_selon(i, visiter):
                return True
            elif isinstance(i, Bloc) and visiter(i.instructions):
                return True
        return False
    return visiter(bloc.instructions)


def _visiter_selon(s: Selon, visiter) -> bool:
    if any(visiter(c.corps.instructions) for c in s.cas):
        return True
    return s.sinon is not None and visiter(s.sinon.instructions)


def _visiter_essayer(e: Essayer, visiter) -> bool:
    if visiter(e.corps.instructions):
        return True
    if any(visiter(cl.corps.instructions) for cl in e.clauses):
        return True
    return e.enfin is not None and visiter(e.enfin.instructions)


def _contient_retour(bloc: Bloc) -> bool:
    def visiter(instrs) -> bool:
        for i in instrs:
            if isinstance(i, Retourner):
                return True
            if isinstance(i, Si):
                if visiter(i.alors.instructions):
                    return True
                if i.sinon is not None:
                    if isinstance(i.sinon, Si):
                        if visiter([i.sinon]):
                            return True
                    elif visiter(i.sinon.instructions):
                        return True
            elif isinstance(i, (TantQue, Pour)):
                if visiter(i.corps.instructions):
                    return True
            elif isinstance(i, Essayer) and _visiter_essayer(i, visiter):
                return True
            elif isinstance(i, Selon) and _visiter_selon(i, visiter):
                return True
            elif isinstance(i, Bloc) and visiter(i.instructions):
                return True
        return False
    return visiter(bloc.instructions)
