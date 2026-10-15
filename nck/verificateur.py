"""Vérificateur de types statique : annote l'AST et signale les erreurs avant l'exécution."""

from .arbre import (
    Affectation, Appel, Arreter, Binaire, Bloc, Continuer, DeclFonction, DeclVariable,
    ExprInstr, Expr, Identifiant, Index, Instr, ListeLit, Litteral, Logique, Pour,
    Programme, Retourner, Si, TantQue, TypeAnnot, Unaire,
)
from .erreurs import ErreurType
from .natifs import NATIFS
from .types_nck import (
    BOOLEEN, ENTIER, LISTE_VIDE, NUL, QUELCONQUE, REEL, RIEN, TEXTE, TYPES_SIMPLES,
    Type, TypeFonction, compatible, element_de, est_liste, est_numerique, liste_de, unifier,
)


class Symbole:
    __slots__ = ("type", "constante", "initialisee")

    def __init__(self, type_: Type, constante: bool = False, initialisee: bool = True):
        self.type = type_
        self.constante = constante
        self.initialisee = initialisee


class Portee:
    def __init__(self, parent: "Portee | None" = None, fonction: "Portee | None" = None):
        self.symboles: dict[str, Symbole] = {}
        self.parent = parent
        # portée racine de la fonction englobante (pour interdire les redéclarations ambiguës)
        self.fonction = fonction if fonction is not None else self

    def chercher(self, nom: str) -> Symbole | None:
        p: Portee | None = self
        while p is not None:
            s = p.symboles.get(nom)
            if s is not None:
                return s
            p = p.parent
        return None

    def visible_dans_fonction(self, nom: str) -> bool:
        p: Portee | None = self
        while p is not None:
            if nom in p.symboles:
                return True
            if p is p.fonction:
                break
            p = p.parent
        return False


class Verificateur:
    def __init__(self, fichier: str = "<entrée>", mode_repl: bool = False):
        self.fichier = fichier
        self.mode_repl = mode_repl  # en mode interactif, une expression seule est autorisée (sa valeur est affichée)
        self.portee = Portee()
        self.type_retour_attendu: Type | None = None
        self.profondeur_boucle = 0
        for nom in NATIFS:
            self.portee.symboles[nom] = Symbole(Type("natif"), constante=True)

    # ----- aides -----

    def erreur(self, message: str, noeud) -> ErreurType:
        return ErreurType(message, noeud.ligne, noeud.colonne, self.fichier)

    def resoudre_type(self, annot: TypeAnnot) -> Type:
        nom = annot.nom
        if nom in TYPES_SIMPLES:
            if annot.params:
                raise self.erreur(f"le type '{nom}' ne prend pas de paramètre", annot)
            return TYPES_SIMPLES[nom]
        if nom == "liste":
            if len(annot.params) == 0:
                return liste_de(QUELCONQUE)
            if len(annot.params) != 1:
                raise self.erreur("'liste' prend exactement un paramètre, ex : liste<entier>", annot)
            return liste_de(self.resoudre_type(annot.params[0]))
        if nom == "fonction":
            if not annot.params:
                raise self.erreur("un type fonction s'écrit fonction<param1, param2, retour>", annot)
            types = [self.resoudre_type(p) for p in annot.params]
            return TypeFonction("fonction", (), tuple(types[:-1]), types[-1])
        suggestion = {
            "int": "entier", "float": "reel", "str": "texte", "string": "texte", "bool": "booleen",
            "number": "reel", "void": "rien", "any": "quelconque", "list": "liste", "chaine": "texte",
            "nombre": "entier ou reel", "double": "reel",
        }.get(nom.lower())
        aide = f" (vouliez-vous dire '{suggestion}' ?)" if suggestion else ""
        raise self.erreur(f"type inconnu '{nom}'{aide}", annot)

    def ouvrir(self, nouvelle_fonction: bool = False) -> None:
        self.portee = Portee(self.portee, None if nouvelle_fonction else self.portee.fonction)

    def fermer(self) -> None:
        assert self.portee.parent is not None
        self.portee = self.portee.parent

    def declarer(self, nom: str, type_: Type, noeud, constante: bool = False, initialisee: bool = True) -> None:
        if nom in NATIFS:
            raise self.erreur(f"'{nom}' est une fonction native, impossible de la redéfinir", noeud)
        if self.portee.visible_dans_fonction(nom):
            raise self.erreur(f"'{nom}' est déjà déclaré dans cette portée", noeud)
        self.portee.symboles[nom] = Symbole(type_, constante, initialisee)

    # ----- programme -----

    def verifier_programme(self, prog: Programme) -> None:
        self.pre_declarer_fonctions(prog.instructions)
        for instr in prog.instructions:
            self.instruction(instr)

    def pre_declarer_fonctions(self, instructions: list[Instr]) -> None:
        """Les fonctions sont visibles dans tout leur bloc, même avant leur définition."""
        for instr in instructions:
            if isinstance(instr, DeclFonction):
                t = TypeFonction(
                    "fonction", (),
                    tuple(self.resoudre_type(p.type_annot) for p in instr.parametres),
                    self.resoudre_type(instr.type_retour),
                )
                instr.type = t  # type: ignore[attr-defined]
                self.declarer(instr.nom, t, instr, constante=True)

    # ----- instructions -----

    def bloc(self, bloc: Bloc) -> bool:
        """Vérifie un bloc. Retourne True si le bloc termine toujours (retourner/arreter/continuer)."""
        self.ouvrir()
        self.pre_declarer_fonctions(bloc.instructions)
        termine = False
        for instr in bloc.instructions:
            if termine:
                raise self.erreur("code inatteignable : l'instruction précédente quitte toujours le bloc", instr)
            termine = self.instruction(instr)
        self.fermer()
        return termine

    def instruction(self, instr: Instr) -> bool:
        m = getattr(self, "i_" + type(instr).__name__)
        return bool(m(instr))

    def i_DeclVariable(self, d: DeclVariable) -> bool:
        t_annot = self.resoudre_type(d.type_annot) if d.type_annot else None
        if t_annot == RIEN:
            raise self.erreur("une variable ne peut pas être de type 'rien'", d.type_annot)
        if d.valeur is not None:
            t_val = self.expression(d.valeur)
            if t_val == RIEN:
                raise self.erreur(f"la variable '{d.nom}' reçoit le résultat d'une fonction qui ne retourne rien", d.valeur)
            if t_annot is None:
                if t_val == NUL:
                    raise self.erreur(f"impossible de déduire le type de '{d.nom}' depuis 'nul' : précisez le type", d)
                t_annot = liste_de(QUELCONQUE) if t_val == LISTE_VIDE else t_val
            elif not compatible(t_val, t_annot):
                raise self.erreur(f"'{d.nom}' est de type {t_annot}, mais reçoit un {t_val}", d.valeur)
            d.verif_runtime = (t_val == QUELCONQUE and t_annot != QUELCONQUE)  # type: ignore[attr-defined]
        else:
            d.verif_runtime = False  # type: ignore[attr-defined]
        assert t_annot is not None
        d.type = t_annot  # type: ignore[attr-defined]
        self.declarer(d.nom, t_annot, d, d.constante, initialisee=d.valeur is not None)
        return False

    def i_Affectation(self, a: Affectation) -> bool:
        if isinstance(a.cible, Identifiant):
            sym = self.portee.chercher(a.cible.nom)
            if sym is None:
                raise self.erreur(f"variable '{a.cible.nom}' inconnue", a.cible)
            if sym.constante:
                raise self.erreur(f"'{a.cible.nom}' est une constante : impossible de la modifier", a.cible)
            t_cible = sym.type
            a.cible.type = t_cible  # type: ignore[attr-defined]
            if a.op != "=" and not sym.initialisee:
                raise self.erreur(f"'{a.cible.nom}' est utilisée avant d'avoir reçu une valeur", a.cible)
            sym.initialisee = True
        else:
            assert isinstance(a.cible, Index)
            t_cible = self.expression(a.cible)
            t_conteneur = a.cible.cible.type  # type: ignore[attr-defined]
            if t_conteneur == TEXTE:
                raise self.erreur("un texte ne peut pas être modifié caractère par caractère", a.cible)
        t_val = self.expression(a.valeur)
        if a.op == "=":
            t_res = t_val
        else:
            t_res = self.type_binaire(a.op[0], t_cible, t_val, a)
        if t_res == RIEN:
            raise self.erreur("affectation d'une valeur de type 'rien'", a.valeur)
        if not compatible(t_res, t_cible):
            raise self.erreur(f"impossible d'affecter un {t_res} à une cible de type {t_cible}", a.valeur)
        a.verif_runtime = (t_res == QUELCONQUE and t_cible != QUELCONQUE)  # type: ignore[attr-defined]
        a.type = t_cible  # type: ignore[attr-defined]
        return False

    def i_ExprInstr(self, e: ExprInstr) -> bool:
        if not isinstance(e.expr, Appel) and not self.mode_repl:
            t = self.expression(e.expr)
            raise self.erreur(
                f"cette expression de type {t} n'a aucun effet (oubli d'une affectation ou d'un appel ?)", e)
        self.expression(e.expr)
        return False

    def i_Bloc(self, b: Bloc) -> bool:
        return self.bloc(b)

    def i_Si(self, s: Si) -> bool:
        self.condition(s.condition, "si")
        t1 = self.bloc(s.alors)
        if s.sinon is None:
            return False
        t2 = self.instruction(s.sinon) if isinstance(s.sinon, Si) else self.bloc(s.sinon)
        return t1 and t2

    def i_TantQue(self, t: TantQue) -> bool:
        self.condition(t.condition, "tantque")
        self.profondeur_boucle += 1
        self.bloc(t.corps)
        self.profondeur_boucle -= 1
        return False

    def i_Pour(self, p: Pour) -> bool:
        t_it = self.expression(p.iterable)
        if t_it == TEXTE:
            t_var = TEXTE
        elif est_liste(t_it):
            t_var = element_de(t_it)
        elif t_it == QUELCONQUE:
            t_var = QUELCONQUE
        elif t_it == ENTIER:
            t_var = ENTIER  # `pour i dans 10` équivaut à intervalle(10)
        else:
            raise self.erreur(f"impossible de parcourir une valeur de type {t_it}", p.iterable)
        p.type_iterable = t_it  # type: ignore[attr-defined]
        self.ouvrir()
        self.declarer(p.variable, t_var, p)
        self.profondeur_boucle += 1
        self.bloc(p.corps)
        self.profondeur_boucle -= 1
        self.fermer()
        return False

    def i_DeclFonction(self, f: DeclFonction) -> bool:
        t: TypeFonction = getattr(f, "type", None)  # type: ignore[assignment]
        if t is None:  # fonction non pré-déclarée (ne devrait pas arriver)
            self.pre_declarer_fonctions([f])
            t = f.type  # type: ignore[attr-defined]
        ancien_retour, ancienne_boucle = self.type_retour_attendu, self.profondeur_boucle
        self.type_retour_attendu = t.retour
        self.profondeur_boucle = 0
        self.ouvrir(nouvelle_fonction=True)
        noms = set()
        for p, tp in zip(f.parametres, t.parametres):
            if p.nom in noms:
                raise self.erreur(f"paramètre '{p.nom}' en double", p)
            if tp == RIEN:
                raise self.erreur("un paramètre ne peut pas être de type 'rien'", p)
            noms.add(p.nom)
            self.declarer(p.nom, tp, p)
        termine = self.bloc(f.corps)
        self.fermer()
        if t.retour != RIEN and not termine:
            raise self.erreur(
                f"la fonction '{f.nom}' doit retourner un {t.retour} dans tous les cas "
                f"(il manque un 'retourner' à la fin ?)", f)
        self.type_retour_attendu, self.profondeur_boucle = ancien_retour, ancienne_boucle
        return False

    def i_Retourner(self, r: Retourner) -> bool:
        if self.type_retour_attendu is None:
            raise self.erreur("'retourner' en dehors d'une fonction", r)
        attendu = self.type_retour_attendu
        if r.valeur is None:
            if attendu != RIEN:
                raise self.erreur(f"cette fonction doit retourner un {attendu}, mais 'retourner' est vide", r)
            r.verif_runtime = False  # type: ignore[attr-defined]
            return True
        t = self.expression(r.valeur)
        if attendu == RIEN:
            raise self.erreur("cette fonction ne retourne rien ('rien') : utilisez 'retourner' sans valeur", r.valeur)
        if not compatible(t, attendu):
            raise self.erreur(f"la fonction doit retourner un {attendu}, mais retourne un {t}", r.valeur)
        r.verif_runtime = (t == QUELCONQUE and attendu != QUELCONQUE)  # type: ignore[attr-defined]
        r.type_attendu = attendu  # type: ignore[attr-defined]
        return True

    def i_Arreter(self, a: Arreter) -> bool:
        if self.profondeur_boucle == 0:
            raise self.erreur("'arreter' en dehors d'une boucle", a)
        return True

    def i_Continuer(self, c: Continuer) -> bool:
        if self.profondeur_boucle == 0:
            raise self.erreur("'continuer' en dehors d'une boucle", c)
        return True

    def condition(self, e: Expr, mot: str) -> None:
        t = self.expression(e)
        if t != BOOLEEN and t != QUELCONQUE:
            raise self.erreur(f"la condition de '{mot}' doit être un booleen, mais c'est un {t}", e)

    # ----- expressions -----

    def expression(self, e: Expr) -> Type:
        t = getattr(self, "e_" + type(e).__name__)(e)
        e.type = t  # type: ignore[attr-defined]
        return t

    def e_Litteral(self, l: Litteral) -> Type:
        v = l.valeur
        if v is None:
            return NUL
        if isinstance(v, bool):
            return BOOLEEN
        if isinstance(v, int):
            return ENTIER
        if isinstance(v, float):
            return REEL
        return TEXTE

    def e_ListeLit(self, l: ListeLit) -> Type:
        if not l.elements:
            return LISTE_VIDE
        t = self.expression(l.elements[0])
        for el in l.elements[1:]:
            t = unifier(t, self.expression(el))
        if t == RIEN or t == NUL:
            raise self.erreur("une liste ne peut pas contenir de valeurs 'rien' ou 'nul'", l)
        return liste_de(t)

    def e_Identifiant(self, i: Identifiant) -> Type:
        sym = self.portee.chercher(i.nom)
        if sym is None:
            raise self.erreur(f"variable '{i.nom}' inconnue", i)
        if not sym.initialisee:
            raise self.erreur(f"'{i.nom}' est utilisée avant d'avoir reçu une valeur", i)
        return sym.type

    def e_Unaire(self, u: Unaire) -> Type:
        t = self.expression(u.operande)
        if u.op == "non":
            if t != BOOLEEN and t != QUELCONQUE:
                raise self.erreur(f"'non' attend un booleen, mais reçoit un {t}", u)
            return BOOLEEN
        if t == QUELCONQUE:
            return QUELCONQUE
        if not est_numerique(t):
            raise self.erreur(f"'-' attend un nombre, mais reçoit un {t}", u)
        return t

    def e_Binaire(self, b: Binaire) -> Type:
        tg = self.expression(b.gauche)
        td = self.expression(b.droite)
        return self.type_binaire(b.op, tg, td, b)

    def type_binaire(self, op: str, tg: Type, td: Type, noeud) -> Type:
        if op in ("==", "!="):
            if tg != QUELCONQUE and td != QUELCONQUE and not compatible(tg, td) and not compatible(td, tg):
                raise self.erreur(f"comparaison impossible entre {tg} et {td} (toujours {'faux' if op == '==' else 'vrai'})", noeud)
            return BOOLEEN
        if op in ("<", ">", "<=", ">="):
            if tg == QUELCONQUE or td == QUELCONQUE:
                return BOOLEEN
            if (est_numerique(tg) and est_numerique(td)) or (tg == TEXTE and td == TEXTE):
                return BOOLEEN
            raise self.erreur(f"'{op}' ne peut pas comparer un {tg} et un {td}", noeud)
        if tg == QUELCONQUE or td == QUELCONQUE:
            return QUELCONQUE
        if op == "+":
            if est_numerique(tg) and est_numerique(td):
                return REEL if REEL in (tg, td) else ENTIER
            if tg == TEXTE and td == TEXTE:
                return TEXTE
            if est_liste(tg) and est_liste(td):
                return unifier(tg, td)
            if TEXTE in (tg, td):
                raise self.erreur(
                    f"impossible d'additionner un {tg} et un {td} : utilisez texte(...) pour convertir", noeud)
            raise self.erreur(f"impossible d'additionner un {tg} et un {td}", noeud)
        if op == "*":
            if est_numerique(tg) and est_numerique(td):
                return REEL if REEL in (tg, td) else ENTIER
            if (tg == TEXTE and td == ENTIER) or (tg == ENTIER and td == TEXTE):
                return TEXTE
            if (est_liste(tg) and td == ENTIER):
                return tg
            raise self.erreur(f"impossible de multiplier un {tg} et un {td}", noeud)
        if op in ("-", "%"):
            if est_numerique(tg) and est_numerique(td):
                return REEL if REEL in (tg, td) else ENTIER
            raise self.erreur(f"'{op}' attend deux nombres, mais reçoit un {tg} et un {td}", noeud)
        if op == "/":
            if est_numerique(tg) and est_numerique(td):
                return REEL
            raise self.erreur(f"'/' attend deux nombres, mais reçoit un {tg} et un {td}", noeud)
        raise self.erreur(f"opérateur inconnu '{op}'", noeud)

    def e_Logique(self, l: Logique) -> Type:
        for cote in (l.gauche, l.droite):
            t = self.expression(cote)
            if t != BOOLEEN and t != QUELCONQUE:
                raise self.erreur(f"'{l.op}' attend des booleens, mais reçoit un {t}", cote)
        return BOOLEEN

    def e_Index(self, i: Index) -> Type:
        tc = self.expression(i.cible)
        ti = self.expression(i.index)
        if ti != ENTIER and ti != QUELCONQUE:
            raise self.erreur(f"l'index doit être un entier, mais c'est un {ti}", i.index)
        if tc == TEXTE:
            return TEXTE
        if est_liste(tc):
            return element_de(tc)
        if tc == QUELCONQUE:
            return QUELCONQUE
        raise self.erreur(f"impossible d'indexer une valeur de type {tc}", i)

    def e_Appel(self, a: Appel) -> Type:
        if isinstance(a.cible, Identifiant) and a.cible.nom in NATIFS and self.portee.chercher(a.cible.nom).type == Type("natif"):
            natif = NATIFS[a.cible.nom]
            a.cible.type = Type("natif")  # type: ignore[attr-defined]
            types = [self.expression(arg) for arg in a.arguments]
            for arg, t in zip(a.arguments, types):
                if t == RIEN:
                    raise self.erreur("cet argument est le résultat d'une fonction qui ne retourne rien", arg)
            a.natif = natif  # type: ignore[attr-defined]
            a.verifs_runtime = ()  # type: ignore[attr-defined]
            return natif.verifier(types, lambda msg: self.erreur(msg, a))
        tc = self.expression(a.cible)
        types = [self.expression(arg) for arg in a.arguments]
        a.natif = None  # type: ignore[attr-defined]
        if tc == QUELCONQUE:
            a.verifs_runtime = ()  # type: ignore[attr-defined]
            return QUELCONQUE
        if not isinstance(tc, TypeFonction):
            raise self.erreur(f"une valeur de type {tc} ne peut pas être appelée comme une fonction", a)
        nom = a.cible.nom if isinstance(a.cible, Identifiant) else "la fonction"
        if len(types) != len(tc.parametres):
            raise self.erreur(
                f"'{nom}' attend {len(tc.parametres)} argument(s), mais {len(types)} fourni(s)", a)
        verifs = []
        for i, (arg, t, tp) in enumerate(zip(a.arguments, types, tc.parametres), 1):
            if not compatible(t, tp):
                raise self.erreur(f"argument {i} de '{nom}' : {tp} attendu, mais {t} fourni", arg)
            verifs.append(t == QUELCONQUE and tp != QUELCONQUE)
        a.verifs_runtime = tuple(verifs)  # type: ignore[attr-defined]
        return tc.retour


def verifier(prog: Programme, fichier: str = "<entrée>") -> None:
    Verificateur(fichier).verifier_programme(prog)
