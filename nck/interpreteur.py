"""Interpréteur : compile l'AST (déjà vérifié) en fermetures Python puis l'exécute.

Chaque nœud est transformé une seule fois en une fonction Python `fn(env)`, ce qui évite
le coût d'une traversée de l'arbre à chaque exécution (bien plus rapide qu'un « tree-walker »).
"""

import sys
from typing import Callable

from .arbre import (
    Affectation, Appel, Arreter, Binaire, Bloc, Continuer, DeclFonction, DeclVariable,
    ExprInstr, Expr, Identifiant, Index, Instr, ListeLit, Litteral, Logique, Pour,
    Programme, Retourner, Si, TantQue, Unaire,
)
from .erreurs import ErreurExecution, ErreurNck
from .natifs import NATIFS, FonctionNck, nom_type_valeur, vers_texte
from .types_nck import ENTIER, QUELCONQUE, TEXTE, Type, est_liste, valeur_compatible


# ---------- signaux de contrôle ----------

class _Retour(Exception):
    __slots__ = ("valeur",)

    def __init__(self, valeur):
        self.valeur = valeur


class _Arret(Exception):
    pass


class _Continue(Exception):
    pass


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
    def __init__(self, fichier: str = "<entrée>", limite_recursion: int = 2000):
        self.fichier = fichier
        self.limite_recursion = limite_recursion
        self.global_env = Env()
        for nom, natif in NATIFS.items():
            self.global_env.vars[nom] = natif

    def erreur(self, message: str, noeud) -> ErreurExecution:
        return ErreurExecution(message, noeud.ligne, noeud.colonne, self.fichier)

    # ----- point d'entrée -----

    def executer(self, prog: Programme) -> None:
        corps = self.compiler_instructions(prog.instructions)
        ancienne_limite = sys.getrecursionlimit()
        sys.setrecursionlimit(max(ancienne_limite, self.limite_recursion * 6))
        try:
            corps(self.global_env)
        except RecursionError:
            raise ErreurExecution("récursion trop profonde (dépassement de pile)", 0, 0, self.fichier) from None
        finally:
            sys.setrecursionlimit(ancienne_limite)

    # ----- instructions -----

    def compiler_instructions(self, instructions: list[Instr]) -> Fn:
        # Les fonctions sont « hissées » : elles existent dès le début de leur bloc,
        # ce qui permet de les appeler avant leur définition (comme l'autorise le vérificateur).
        ordonnees = ([i for i in instructions if isinstance(i, DeclFonction)]
                     + [i for i in instructions if not isinstance(i, DeclFonction)])
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

        assert isinstance(a.cible, Index)
        conteneur = self.expression(a.cible.cible)
        index = self.expression(a.cible.index)
        noeud = a.cible

        def indexer(env):
            c = conteneur(env)
            i = index(env)
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

        def obtenir(env):
            it = iterable(env)
            if isinstance(it, bool) or not isinstance(it, (list, str, int)):
                raise self.erreur(f"impossible de parcourir un {nom_type_valeur(it)}", noeud)
            return range(it) if isinstance(it, int) else it

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

    def i_DeclFonction(self, f: DeclFonction) -> Fn:
        corps = self.compiler_instructions(f.corps.instructions)
        noms = [p.nom for p in f.parametres]
        nom = f.nom
        a_retour = _contient_retour(f.corps)
        limite = self.limite_recursion
        profondeur = [0]

        def fabriquer(env_def: Env) -> FonctionNck:
            def appeler(*args):
                env = Env(env_def)
                env.vars.update(zip(noms, args))
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
            return FonctionNck(nom, len(noms), appeler)

        def decl(env):
            env.vars[nom] = fabriquer(env)
        return decl

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

    def e_ListeLit(self, l: ListeLit) -> Fn:
        elems = [self.expression(x) for x in l.elements]
        return lambda env: [f(env) for f in elems]

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

    def e_Appel(self, a: Appel) -> Fn:
        args = [self.expression(x) for x in a.arguments]
        natif = a.natif  # type: ignore[attr-defined]
        erreur = self.erreur

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
            f = cible(env)
            valeurs = [g(env) for g in args]
            if isinstance(f, FonctionNck):
                if f.arite != len(valeurs):
                    raise erreur(f"'{f.nom}' attend {f.arite} argument(s), mais {len(valeurs)} fourni(s)", a)
                return f.appeler(*valeurs)
            if callable(f):
                try:
                    return f(*valeurs)
                except ErreurNck as exc:
                    raise enrichir(exc)
            raise erreur(f"'{nom}' n'est pas une fonction (c'est un {nom_type_valeur(f)})", a)
        return appel


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
            elif isinstance(i, Bloc) and visiter(i.instructions):
                return True
        return False
    return visiter(bloc.instructions)


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
            elif isinstance(i, Bloc) and visiter(i.instructions):
                return True
        return False
    return visiter(bloc.instructions)
