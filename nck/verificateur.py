import os

"""Vérificateur de types statique : annote l'AST et signale les erreurs avant l'exécution."""

from .arbre import (
    Affectation, Appel, Arreter, Binaire, Bloc, Continuer, DeclClasse, DeclFonction, DeclVariable,
    DicoLit, Essayer, ExprInstr, Expr, Identifiant, Importer, Index, Instr, Lever, ListeLit, Litteral, Logique, Membre,
    Pour, Programme, Retourner, Selon, Si, TantQue, TexteFormate, TypeAnnot, Unaire,
)
from .erreurs import ErreurType
from .modules import Chargeur, Module
from .natifs import NATIFS
from .types_nck import (
    BOOLEEN, DICO_VIDE, ENTIER, LISTE_VIDE, NUL, QUELCONQUE, REEL, RIEN, TEXTE, TYPES_CLES, TYPES_SIMPLES,
    Type, TypeClasse, TypeFonction, TypeModule, cle_de, compatible, dico_de, element_de, est_dico, est_liste,
    est_numerique, liste_de, unifier, valeur_de,
)

TYPE_META_CLASSE = Type("classe")   # type du symbole qui désigne une classe (ex : `Personne`)
TYPE_ERREUR = TypeClasse("Erreur")  # classe intégrée


class InfoClasse:
    def __init__(self, nom: str, type_: TypeClasse, parent: "InfoClasse | None", noeud: "DeclClasse | None"):
        self.nom = nom
        self.type = type_
        self.parent = parent
        self.noeud = noeud
        self.champs: dict[str, Type] = {}
        self.defauts: set[str] = set()
        self.methodes: dict[str, TypeFonction] = {}
        self.prete = False


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
    def __init__(self, fichier: str = "<entrée>", mode_repl: bool = False,
                 chargeur: Chargeur | None = None, classes: "dict[str, InfoClasse] | None" = None):
        self.fichier = fichier
        self.mode_repl = mode_repl  # en mode interactif, une expression seule est autorisée (sa valeur est affichée)
        self.portee = Portee()
        self.racine = self.portee
        self.type_retour_attendu: Type | None = None
        self.profondeur_boucle = 0
        self.chargeur = chargeur if chargeur is not None else Chargeur()
        self.classes: dict[str, InfoClasse] = classes if classes is not None else {}
        self.classe_fichier: dict[str, str] = {}   # nom de classe -> fichier qui la définit
        for nom in NATIFS:
            self.portee.symboles[nom] = Symbole(Type("natif"), constante=True)
        # Classe intégrée `Erreur` (base de toutes les erreurs levées / attrapées)
        if "Erreur" not in self.classes:
            erreur = InfoClasse("Erreur", TYPE_ERREUR, None, None)
            erreur.champs["message"] = TEXTE
            erreur.prete = True
            self.classes["Erreur"] = erreur
        self.portee.symboles["Erreur"] = Symbole(TYPE_META_CLASSE, constante=True)

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
        if nom == "dico":
            if len(annot.params) == 0:
                return dico_de(QUELCONQUE, QUELCONQUE)
            if len(annot.params) != 2:
                raise self.erreur("'dico' prend deux paramètres, ex : dico<texte, entier>", annot)
            k = self.resoudre_type(annot.params[0])
            if k not in TYPES_CLES and k != QUELCONQUE:
                raise self.erreur(f"une clé de dictionnaire doit être un texte, un entier ou un booleen, pas un {k}",
                                  annot.params[0])
            return dico_de(k, self.resoudre_type(annot.params[1]))
        if nom in self.classes:
            if annot.params:
                raise self.erreur(f"la classe '{nom}' ne prend pas de paramètre de type", annot)
            return self.classes[nom].type
        if nom == "fonction":
            if not annot.params:
                raise self.erreur("un type fonction s'écrit fonction<param1, param2, retour>", annot)
            types = [self.resoudre_type(p) for p in annot.params]
            return TypeFonction("fonction", (), tuple(types[:-1]), types[-1])
        suggestion = {
            "int": "entier", "float": "reel", "str": "texte", "string": "texte", "bool": "booleen",
            "number": "reel", "void": "rien", "any": "quelconque", "list": "liste", "chaine": "texte",
            "dict": "dico", "map": "dico", "dictionnaire": "dico", "object": "dico ou classe",
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
        if self.portee.visible_dans_fonction(nom) and not (self.portee is self.racine and nom in NATIFS):
            raise self.erreur(f"'{nom}' est déjà déclaré dans cette portée", noeud)
        self.portee.symboles[nom] = Symbole(type_, constante, initialisee)

    # ----- programme -----

    def verifier_programme(self, prog: Programme) -> None:
        self.pre_declarer_fonctions(prog.instructions)
        for instr in prog.instructions:
            self.instruction(instr)

    def pre_declarer_fonctions(self, instructions: list[Instr]) -> None:
        """Les fonctions et classes sont visibles dans tout leur bloc, même avant leur définition."""
        # 1. noms des classes (une classe parente doit être déclarée avant ses enfants)
        for instr in instructions:
            if isinstance(instr, DeclClasse):
                if instr.nom in self.classes:
                    autre = self.classe_fichier.get(instr.nom)
                    if autre is None:
                        raise self.erreur(f"la classe '{instr.nom}' existe déjà (classe intégrée)", instr)
                    if autre == self.fichier:
                        raise self.erreur(f"la classe '{instr.nom}' est définie deux fois", instr)
                    raise self.erreur(
                        f"la classe '{instr.nom}' est définie à la fois dans {os.path.basename(autre)} et dans "
                        f"{os.path.basename(self.fichier)} : les noms de classes doivent être uniques entre modules", instr)
                parent = None
                if instr.parent is not None:
                    parent = self.classes.get(instr.parent)
                    if parent is None:
                        raise self.erreur(
                            f"classe parente '{instr.parent}' inconnue (elle doit être déclarée avant '{instr.nom}')", instr)
                ancetres = (parent.nom, *parent.type.ancetres) if parent else ()
                info = InfoClasse(instr.nom, TypeClasse(instr.nom, (), ancetres), parent, instr)
                self.declarer(instr.nom, TYPE_META_CLASSE, instr, constante=True)
                self.classes[instr.nom] = info
                self.classe_fichier[instr.nom] = self.fichier
                instr.info = info  # type: ignore[attr-defined]
        # 2. champs et signatures des méthodes (peuvent référencer n'importe quelle classe du bloc)
        for instr in instructions:
            if isinstance(instr, DeclClasse):
                self._signatures_classe(instr)
        # 3. signatures des fonctions
        for instr in instructions:
            if isinstance(instr, DeclFonction):
                t = self._type_fonction(instr)
                instr.type = t  # type: ignore[attr-defined]
                self.declarer(instr.nom, t, instr, constante=True)

    def _type_fonction(self, f: DeclFonction) -> TypeFonction:
        obligatoires = sum(1 for p in f.parametres if p.defaut is None)
        return TypeFonction(
            "fonction", (),
            tuple(self.resoudre_type(p.type_annot) for p in f.parametres),
            self.resoudre_type(f.type_retour),
            obligatoires,
        )

    def _signatures_classe(self, c: DeclClasse) -> None:
        info: InfoClasse = c.info  # type: ignore[attr-defined]
        if info.parent is not None:
            info.champs = dict(info.parent.champs)
            info.defauts = set(info.parent.defauts)
            info.methodes = dict(info.parent.methodes)
        for champ in c.champs:
            if champ.nom in info.champs:
                origine = "la classe parente" if info.parent and champ.nom in info.parent.champs else "cette classe"
                raise self.erreur(f"le champ '{champ.nom}' est déjà défini dans {origine}", champ)
            if champ.nom in info.methodes:
                raise self.erreur(f"'{champ.nom}' est déjà une méthode de la classe parente", champ)
            t = self.resoudre_type(champ.type_annot)
            if t == RIEN:
                raise self.erreur("un champ ne peut pas être de type 'rien'", champ.type_annot)
            info.champs[champ.nom] = t
            champ.type = t  # type: ignore[attr-defined]
            if champ.defaut is not None:
                info.defauts.add(champ.nom)
        noms = set()
        for m in c.methodes:
            if m.nom in noms:
                raise self.erreur(f"la méthode '{m.nom}' est définie deux fois", m)
            if m.nom in info.champs:
                raise self.erreur(f"'{m.nom}' est déjà un champ : impossible d'avoir une méthode du même nom", m)
            noms.add(m.nom)
            t = self._type_fonction(m)
            if m.nom == "valider" and (t.parametres or t.retour != RIEN):
                raise self.erreur("la méthode spéciale 'valider' ne prend aucun paramètre et ne retourne rien", m)
            ancienne = info.methodes.get(m.nom)
            if ancienne is not None and not compatible(t, ancienne):
                raise self.erreur(
                    f"la méthode '{m.nom}' ({t}) n'est pas compatible avec celle de la classe parente ({ancienne})", m)
            info.methodes[m.nom] = t
            m.type = t  # type: ignore[attr-defined]
        info.prete = True

    # ----- instructions -----

    def i_DeclClasse(self, c: DeclClasse) -> bool:
        info: InfoClasse = c.info  # type: ignore[attr-defined]
        for champ in c.champs:
            if champ.defaut is not None:
                t = self.expression(champ.defaut)
                if not compatible(t, champ.type):  # type: ignore[attr-defined]
                    raise self.erreur(
                        f"le champ '{champ.nom}' est de type {champ.type}, mais sa valeur par défaut est un {t}",  # type: ignore[attr-defined]
                        champ.defaut)
        for m in c.methodes:
            self._verifier_fonction(m, soi=info.type)
        return False

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
                if t_val == LISTE_VIDE:
                    t_annot = liste_de(QUELCONQUE)
                elif t_val == DICO_VIDE:
                    t_annot = dico_de(QUELCONQUE, QUELCONQUE)
                else:
                    t_annot = t_val
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
        elif isinstance(a.cible, Membre):
            t_cible = self.expression(a.cible)
            t_obj = a.cible.objet.type  # type: ignore[attr-defined]
            if isinstance(t_obj, TypeModule):
                raise self.erreur(f"impossible de modifier '{a.cible.nom}' depuis l'extérieur du module '{t_obj.nom}'", a.cible)
            if isinstance(t_obj, TypeClasse) and a.cible.nom in self.classes[t_obj.nom].methodes:
                raise self.erreur(f"'{a.cible.nom}' est une méthode : impossible de la modifier", a.cible)
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
        elif est_dico(t_it):
            t_var = cle_de(t_it)       # on parcourt les clés
        elif t_it == QUELCONQUE:
            t_var = QUELCONQUE
        elif t_it == ENTIER:
            t_var = ENTIER  # `pour i dans 10` équivaut à intervalle(10)
        else:
            raise self.erreur(f"impossible de parcourir une valeur de type {t_it}", p.iterable)
        p.type_iterable = t_it  # type: ignore[attr-defined]
        self.ouvrir()
        if p.variable2 is not None:
            if est_dico(t_it):
                t1, t2 = cle_de(t_it), valeur_de(t_it)       # pour cle, valeur dans dico
            elif t_it == QUELCONQUE:
                t1, t2 = QUELCONQUE, QUELCONQUE
            else:
                t1, t2 = ENTIER, t_var                         # pour indice, element dans liste/texte
            if p.variable == p.variable2:
                raise self.erreur(f"les deux variables de la boucle ont le même nom '{p.variable}'", p)
            self.declarer(p.variable, t1, p)
            self.declarer(p.variable2, t2, p)
        else:
            self.declarer(p.variable, t_var, p)
        self.profondeur_boucle += 1
        self.bloc(p.corps)
        self.profondeur_boucle -= 1
        self.fermer()
        return False

    def i_DeclFonction(self, f: DeclFonction) -> bool:
        if getattr(f, "type", None) is None:  # fonction non pré-déclarée (ne devrait pas arriver)
            self.pre_declarer_fonctions([f])
        return self._verifier_fonction(f)

    def _verifier_fonction(self, f: DeclFonction, soi: TypeClasse | None = None) -> bool:
        t: TypeFonction = f.type  # type: ignore[attr-defined]
        for p, tp in zip(f.parametres, t.parametres):
            if p.defaut is not None:
                td = self.expression(p.defaut)
                if not compatible(td, tp):
                    raise self.erreur(f"la valeur par défaut du paramètre '{p.nom}' doit être un {tp}, mais c'est un {td}", p.defaut)
        ancien_retour, ancienne_boucle = self.type_retour_attendu, self.profondeur_boucle
        self.type_retour_attendu = t.retour
        self.profondeur_boucle = 0
        self.ouvrir(nouvelle_fonction=True)
        noms = set()
        if soi is not None:
            self.declarer("soi", soi, f, constante=True)
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

    def i_Importer(self, imp: Importer) -> bool:
        if self.portee is not self.racine:
            raise self.erreur("'importer' doit être placé au niveau principal du fichier (pas dans une fonction ou un bloc)", imp)
        m = self.chargeur.resoudre(imp.chemin, self.fichier, imp)
        if m.chemin in self.chargeur.en_cours:
            cycle = " -> ".join(os.path.basename(c) for c in self.chargeur.en_cours + [m.chemin])
            raise self.erreur(f"import circulaire : {cycle}", imp)
        if not m.verifie:
            prog = self.chargeur.charger_programme(m)
            self.chargeur.en_cours.append(m.chemin)
            try:
                sous = Verificateur(m.chemin, chargeur=self.chargeur, classes=self.classes)
                sous.classe_fichier = self.classe_fichier
                sous.verifier_programme(prog)
            finally:
                self.chargeur.en_cours.pop()
            m.exports = {n: sym for n, sym in sous.racine.symboles.items() if n not in NATIFS and n != "Erreur"}
            m.verifie = True
        imp.module = m  # type: ignore[attr-defined]
        if imp.noms is not None:
            for nom in imp.noms:
                if nom not in m.exports:
                    dispo = ", ".join(sorted(m.exports)) or "aucun"
                    raise self.erreur(f"le module \"{imp.chemin}\" ne définit pas '{nom}' (disponibles : {dispo})", imp)
                sym = m.exports[nom]
                if not sym.initialisee:
                    raise self.erreur(f"'{nom}' n'a pas de valeur dans le module \"{imp.chemin}\"", imp)
                self.declarer(nom, sym.type, imp, constante=True)
        else:
            alias = imp.alias or m.nom
            imp.alias = alias
            self.declarer(alias, TypeModule(m.nom, (), m.chemin), imp, constante=True)
        return False

    def i_Selon(self, s: Selon) -> bool:
        t = self.expression(s.sujet)
        if t == RIEN:
            raise self.erreur("'selon' ne peut pas porter sur une valeur de type 'rien'", s.sujet)
        termine = True
        for c in s.cas:
            for v in c.valeurs:
                tv = self.expression(v)
                if t != QUELCONQUE and tv != QUELCONQUE and not compatible(tv, t) and not compatible(t, tv):
                    raise self.erreur(f"ce 'cas' ({tv}) ne peut jamais correspondre à un {t}", v)
            termine = self.bloc(c.corps) and termine
        if s.sinon is None:
            return False
        return self.bloc(s.sinon) and termine

    def i_Essayer(self, e: Essayer) -> bool:
        termine = self.bloc(e.corps)
        for cl in e.clauses:
            t = self.resoudre_type(cl.type_annot) if cl.type_annot else TYPE_ERREUR
            if not (isinstance(t, TypeClasse) and t.herite_de("Erreur")):
                raise self.erreur(f"'attraper' attend une classe d'erreur (héritant de Erreur), mais {t} fourni",
                                  cl.type_annot)
            cl.type = t  # type: ignore[attr-defined]
            self.ouvrir()
            self.declarer(cl.variable, t, cl)
            termine = self.bloc(cl.corps) and termine
            self.fermer()
        if e.enfin is not None:
            if self.bloc(e.enfin):
                termine = True
        return termine

    def i_Lever(self, l: Lever) -> bool:
        t = self.expression(l.valeur)
        if t == TEXTE or t == QUELCONQUE or (isinstance(t, TypeClasse) and t.herite_de("Erreur")):
            l.est_texte = (t == TEXTE)  # type: ignore[attr-defined]
            return True
        raise self.erreur(f"'lever' attend un texte ou une erreur (classe héritant de Erreur), mais {t} fourni", l.valeur)

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

    def e_TexteFormate(self, t: TexteFormate) -> Type:
        for partie in t.parties:
            if not isinstance(partie, str):
                if self.expression(partie) == RIEN:
                    raise self.erreur("cette expression ne produit aucune valeur (type 'rien')", partie)
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

    def e_DicoLit(self, d: DicoLit) -> Type:
        if not d.entrees:
            return DICO_VIDE
        tk = tv = None
        for cle, val in d.entrees:
            k = self.expression(cle)
            if k not in TYPES_CLES and k != QUELCONQUE:
                raise self.erreur(f"une clé de dictionnaire doit être un texte, un entier ou un booleen, pas un {k}", cle)
            v = self.expression(val)
            if v == RIEN or v == NUL:
                raise self.erreur("un dictionnaire ne peut pas contenir de valeurs 'rien' ou 'nul'", val)
            tk = k if tk is None else unifier(tk, k)
            tv = v if tv is None else unifier(tv, v)
        return dico_de(tk, tv)

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
        if est_dico(tc):
            if not compatible(ti, cle_de(tc)):
                raise self.erreur(f"la clé doit être un {cle_de(tc)}, mais c'est un {ti}", i.index)
            return valeur_de(tc)
        if tc == QUELCONQUE:
            return QUELCONQUE
        if ti != ENTIER and ti != QUELCONQUE:
            raise self.erreur(f"l'index doit être un entier, mais c'est un {ti}", i.index)
        if tc == TEXTE:
            return TEXTE
        if est_liste(tc):
            return element_de(tc)
        if tc == QUELCONQUE:
            return QUELCONQUE
        raise self.erreur(f"impossible d'indexer une valeur de type {tc}", i)

    def _module_de(self, t: Type) -> Module:
        return self.chargeur.modules[t.chemin]  # type: ignore[attr-defined]

    def e_Membre(self, m: Membre) -> Type:
        t = self.expression(m.objet)
        if t == QUELCONQUE:
            return QUELCONQUE
        if isinstance(t, TypeModule):
            mod = self._module_de(t)
            sym = mod.exports.get(m.nom)
            if sym is None:
                dispo = ", ".join(sorted(mod.exports)) or "aucun"
                raise self.erreur(f"le module '{t.nom}' ne définit pas '{m.nom}' (disponibles : {dispo})", m)
            return sym.type
        if not isinstance(t, TypeClasse):
            raise self.erreur(f"une valeur de type {t} n'a pas de champ ni de méthode ('.{m.nom}')", m)
        info = self.classes[t.nom]
        if m.nom in info.champs:
            return info.champs[m.nom]
        if m.nom in info.methodes:
            return info.methodes[m.nom]
        proches = [n for n in list(info.champs) + list(info.methodes) if n.lower() == m.nom.lower()]
        aide = f" (vouliez-vous dire '{proches[0]}' ?)" if proches else ""
        raise self.erreur(f"la classe '{t.nom}' n'a pas de champ ni de méthode '{m.nom}'{aide}", m)

    def e_Construction(self, a: Appel, info: InfoClasse) -> Type:
        a.cible.type = TYPE_META_CLASSE  # type: ignore[attr-defined]
        a.natif = None  # type: ignore[attr-defined]
        a.classe = info.nom  # type: ignore[attr-defined]
        noms_champs = list(info.champs)
        if len(a.arguments) > len(noms_champs):
            raise self.erreur(
                f"'{info.nom}' a {len(noms_champs)} champ(s), mais {len(a.arguments)} argument(s) fourni(s)", a)
        fournis: dict[str, Expr] = {}
        for nom, arg in zip(noms_champs, a.arguments):
            fournis[nom] = arg
        for nom, arg in a.nommes:
            if nom not in info.champs:
                raise self.erreur(f"la classe '{info.nom}' n'a pas de champ '{nom}'", arg)
            if nom in fournis:
                raise self.erreur(f"le champ '{nom}' est fourni deux fois", arg)
            fournis[nom] = arg
        manquants = [n for n in noms_champs if n not in fournis and n not in info.defauts]
        if manquants:
            raise self.erreur(
                f"il manque le(s) champ(s) obligatoire(s) {', '.join(repr(n) for n in manquants)} pour créer un '{info.nom}'", a)
        for nom, arg in fournis.items():
            t = self.expression(arg)
            if not compatible(t, info.champs[nom]):
                raise self.erreur(f"champ '{nom}' de '{info.nom}' : {info.champs[nom]} attendu, mais {t} fourni", arg)
        a.champs_fournis = fournis  # type: ignore[attr-defined]
        return info.type

    def e_Appel(self, a: Appel) -> Type:
        if isinstance(a.cible, Identifiant):
            sym = self.portee.chercher(a.cible.nom)
            if sym is not None and sym.type == TYPE_META_CLASSE and a.cible.nom in self.classes:
                return self.e_Construction(a, self.classes[a.cible.nom])
        if isinstance(a.cible, Membre):
            t_obj = self.expression(a.cible.objet)
            if isinstance(t_obj, TypeModule):
                sym = self._module_de(t_obj).exports.get(a.cible.nom)
                if sym is not None and sym.type == TYPE_META_CLASSE and a.cible.nom in self.classes:
                    return self.e_Construction(a, self.classes[a.cible.nom])
        if a.nommes:
            raise self.erreur("les arguments nommés ('nom = valeur') ne sont possibles que pour créer un objet "
                              "(ex : Personne(nom = \"Awa\"))", a.nommes[0][1])
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
        nom = a.cible.nom if isinstance(a.cible, Identifiant) else a.cible.nom if isinstance(a.cible, Membre) else "la fonction"
        if not (tc.minimum <= len(types) <= len(tc.parametres)):
            attendu = (f"{len(tc.parametres)}" if tc.minimum == len(tc.parametres)
                       else f"entre {tc.minimum} et {len(tc.parametres)}")
            raise self.erreur(f"'{nom}' attend {attendu} argument(s), mais {len(types)} fourni(s)", a)
        verifs = []
        for i, (arg, t, tp) in enumerate(zip(a.arguments, types, tc.parametres), 1):
            if not compatible(t, tp):
                raise self.erreur(f"argument {i} de '{nom}' : {tp} attendu, mais {t} fourni", arg)
            verifs.append(t == QUELCONQUE and tp != QUELCONQUE)
        a.verifs_runtime = tuple(verifs)  # type: ignore[attr-defined]
        return tc.retour


def verifier(prog: Programme, fichier: str = "<entrée>") -> None:
    Verificateur(fichier).verifier_programme(prog)
