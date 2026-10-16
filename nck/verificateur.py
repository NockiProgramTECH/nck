import os

"""Vérificateur de types statique : annote l'AST et signale les erreurs avant l'exécution."""

from .arbre import (
    Affectation, Appel, Arreter, Binaire, Bloc, Continuer, DeclClasse, DeclFonction, DeclVariable,
    DicoLit, Essayer, Etalement, ExprInstr, Expr, FonctionAnonyme, Identifiant, DeclMultiple, AffectationMultiple, DeclEnum, Conditionnelle, Importer, Index, Instr, Lever, ListeLit, Litteral, Logique, Membre,
    Pour, Programme, Retourner, Selon, Si, TantQue, TexteFormate, TypeAnnot, Unaire,
)
from .erreurs import ErreurType
from .modules import Chargeur, Module
from .natifs import NATIFS
from .documentation import METHODES_PAR_TYPE
from .types_nck import (
    BOOLEEN, DICO_VIDE, ENTIER, LISTE_VIDE, NUL, QUELCONQUE, REEL, RIEN, TEXTE, TYPES_CLES, TYPES_SIMPLES,
    Type, TypeClasse, TypeEnum, TypeFonction, TypeModule, cle_de, compatible, dico_de, element_de, est_dico, est_liste,
    est_numerique, est_optionnel, liste_de, optionnel_de, sans_nul, unifier, valeur_de,
)

TYPE_META_CLASSE = Type("classe")   # type du symbole qui désigne une classe (ex : `Personne`)
TYPE_ERREUR = TypeClasse("Erreur")  # classe intégrée
INFERER = Type("<à déduire>")
TYPE_META_ENUM = Type("enumeration")   # type du symbole qui désigne une énumération (ex : `Couleur`)        # type de retour en cours de déduction (fonction anonyme sans annotation)


class InfoClasse:
    def __init__(self, nom: str, type_: TypeClasse, parent: "InfoClasse | None", noeud: "DeclClasse | None"):
        self.nom = nom
        self.type = type_
        self.parent = parent
        self.noeud = noeud
        self.champs: dict[str, Type] = {}
        self.defauts: set[str] = set()
        self.methodes: dict[str, TypeFonction] = {}
        self.statiques: dict[str, TypeFonction] = {}
        self.constantes: dict[str, Type] = {}
        self.abstraites: set[str] = set()
        self.descriptions: dict[str, str] = {}             # membre -> signature / description
        self.positions: dict[str, tuple[str, int, int]] = {}   # membre -> (fichier, ligne, colonne)
        self.prete = False

    def signature(self) -> str:
        params = []
        for n, t in self.champs.items():
            params.append(f"{n}: {t}" + (" = …" if n in self.defauts else ""))
        base = f"classe {self.nom}" + (f" herite {self.parent.nom}" if self.parent else "")
        suffixe = "  (abstraite)" if self.abstraites else ""
        return f"{base}({', '.join(params)}){suffixe}"


class Symbole:
    __slots__ = ("type", "constante", "initialisee", "genre", "description", "position", "fichier", "type_declare")

    def __init__(self, type_: Type, constante: bool = False, initialisee: bool = True,
                 genre: str = "variable", description: str = "", position: tuple[int, int] = (0, 0), fichier: str = ""):
        self.type = type_
        self.constante = constante
        self.initialisee = initialisee
        self.genre = genre                # variable, constante, fonction, classe, module, parametre, natif
        self.description = description    # texte affiché au survol (signature…)
        self.position = position          # (ligne, colonne) de la déclaration
        self.fichier = fichier
        self.type_declare: Type | None = None   # type d'origine quand le symbole a été affiné (T? -> T)


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
        self.inference_retour: list[Type] = []
        self.profondeur_boucle = 0
        self.chargeur = chargeur if chargeur is not None else Chargeur()
        self.classes: dict[str, InfoClasse] = classes if classes is not None else {}
        if not hasattr(self.chargeur, "enums"):
            self.chargeur.enums = {}  # type: ignore[attr-defined]
        self.enums: dict[str, TypeEnum] = self.chargeur.enums  # type: ignore[attr-defined]  # partagées entre modules
        # Pour l'éditeur : liste de dicts {ligne, colonne, longueur, nom, symbole, genre}
        self.enregistrements: list[dict] = []
        self.pile_fonctions: list[tuple[int, int]] = []     # (ligne début, ligne fin) des fonctions englobantes
        self.classe_courante: TypeClasse | None = None
        self.classe_fichier: dict[str, str] = {}   # nom de classe -> fichier qui la définit
        for nom in NATIFS:
            self.portee.symboles[nom] = Symbole(Type("natif"), constante=True, genre="natif")
        # Classe intégrée `Erreur` (base de toutes les erreurs levées / attrapées)
        if "Erreur" not in self.classes:
            erreur = InfoClasse("Erreur", TYPE_ERREUR, None, None)
            erreur.champs["message"] = TEXTE
            erreur.prete = True
            self.classes["Erreur"] = erreur
        self.portee.symboles["Erreur"] = Symbole(TYPE_META_CLASSE, constante=True, genre="classe",
                                                 description="classe Erreur(message: texte)")

    # ----- aides -----

    def erreur(self, message: str, noeud) -> ErreurType:
        return ErreurType(message, noeud.ligne, noeud.colonne, self.fichier)

    def resoudre_type(self, annot: TypeAnnot) -> Type:
        nom = annot.nom
        if nom == "optionnel":
            interne = self.resoudre_type(annot.params[0])
            if interne in (RIEN, NUL, QUELCONQUE):
                raise self.erreur(f"'{interne}?' n'a pas de sens : seul un type précis peut être optionnel (ex : texte?)", annot)
            return optionnel_de(interne)
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
            if k not in TYPES_CLES and k != QUELCONQUE and not isinstance(k, TypeEnum):
                raise self.erreur(f"une clé de dictionnaire doit être un texte, un entier ou un booleen, pas un {k}",
                                  annot.params[0])
            return dico_de(k, self.resoudre_type(annot.params[1]))
        if nom in self.classes:
            if annot.params:
                raise self.erreur(f"la classe '{nom}' ne prend pas de paramètre de type", annot)
            return self.classes[nom].type
        if nom in self.enums:
            return self.enums[nom]
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

    def declarer(self, nom: str, type_: Type, noeud, constante: bool = False, initialisee: bool = True,
                 genre: str | None = None, description: str = "") -> Symbole:
        if self.portee.visible_dans_fonction(nom) and not (self.portee is self.racine and nom in NATIFS):
            raise self.erreur(f"'{nom}' est déjà déclaré dans cette portée", noeud)
        if genre is None:
            genre = "constante" if constante else "variable"
        if not description:
            description = f"{genre} {nom}: {type_}"
        pos = getattr(noeud, "position_nom", None) or (noeud.ligne, noeud.colonne)
        sym = Symbole(type_, constante, initialisee, genre, description, pos, self.fichier)
        self.portee.symboles[nom] = sym
        self.enregistrer(noeud, nom, sym, declaration=True, position=pos)
        return sym

    def enregistrer(self, noeud, nom: str, sym: "Symbole | None", declaration: bool = False,
                    position: tuple[int, int] | None = None) -> None:
        """Note une déclaration ou une utilisation (pour l'autocomplétion et le survol)."""
        portee = self.pile_fonctions[-1] if self.pile_fonctions else None
        ligne, colonne = position if position is not None else (noeud.ligne, noeud.colonne)
        self.enregistrements.append({
            "ligne": ligne, "colonne": colonne,
            "longueur": len(nom), "nom": nom, "symbole": sym, "declaration": declaration,
            "portee": portee, "classe": self.classe_courante,
        })

    # ----- programme -----

    def verifier_programme(self, prog: Programme) -> None:
        # Les imports sont traités en premier : une classe importée peut servir de type ou de parent (E1).
        for instr in prog.instructions:
            if isinstance(instr, Importer):
                self.instruction(instr)
        self.pre_declarer_fonctions(prog.instructions)
        for instr in prog.instructions:
            if not isinstance(instr, Importer):
                self.instruction(instr)

    def pre_declarer_fonctions(self, instructions: list[Instr]) -> None:
        """Les fonctions et classes sont visibles dans tout leur bloc, même avant leur définition."""
        # 0. énumérations
        for instr in instructions:
            if isinstance(instr, DeclEnum):
                if instr.nom in self.enums or instr.nom in self.classes:
                    raise self.erreur(f"'{instr.nom}' est déjà défini (énumération ou classe)", instr)
                t = TypeEnum(instr.nom, (), tuple(instr.valeurs))
                self.enums[instr.nom] = t
                self.declarer(instr.nom, TYPE_META_ENUM, instr, constante=True, genre="enumeration",
                              description=f"enumeration {instr.nom}: {', '.join(instr.valeurs)}")
                instr.type_enum = t  # type: ignore[attr-defined]
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
                sym = self.declarer(instr.nom, TYPE_META_CLASSE, instr, constante=True, genre="classe")
                self.classes[instr.nom] = info
                self.classe_fichier[instr.nom] = self.fichier
                info.symbole = sym  # type: ignore[attr-defined]
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
                self.declarer(instr.nom, t, instr, constante=True, genre="fonction", description=self.signature_fonction(instr, t))

    @staticmethod
    def signature_fonction(f: DeclFonction, t: TypeFonction, prefixe: str = "fonction ") -> str:
        params = []
        for p, tp in zip(f.parametres, t.parametres):
            prefixe_p = "..." if p.variadique else ""
            params.append(f"{prefixe_p}{p.nom}: {tp}" + (" = …" if p.defaut is not None else ""))
        retour = f" -> {t.retour}" if t.retour != RIEN else ""
        return f"{prefixe}{f.nom}({', '.join(params)}){retour}"

    def _type_fonction(self, f: DeclFonction) -> TypeFonction:
        variadique = bool(f.parametres) and f.parametres[-1].variadique
        obligatoires = sum(1 for p in f.parametres if p.defaut is None and not p.variadique)
        params = []
        for p in f.parametres:
            t = self.resoudre_type(p.type_annot)
            if p.variadique and not est_liste(t):
                raise self.erreur(f"le paramètre '...{p.nom}' doit être une liste (ex : ...{p.nom}: liste<entier>), pas un {t}", p)
            params.append(t)
        return TypeFonction("fonction", (), tuple(params), self.resoudre_type(f.type_retour), obligatoires, variadique)

    def _signatures_classe(self, c: DeclClasse) -> None:
        info: InfoClasse = c.info  # type: ignore[attr-defined]
        if info.parent is not None:
            info.champs = dict(info.parent.champs)
            info.defauts = set(info.parent.defauts)
            info.methodes = dict(info.parent.methodes)
            info.statiques = dict(info.parent.statiques)
            info.constantes = dict(info.parent.constantes)
            info.abstraites = set(info.parent.abstraites)
        for cst in getattr(c, "constantes", []):
            if cst.nom in info.constantes:
                raise self.erreur(f"la constante '{cst.nom}' est déjà définie dans la classe parente", cst)
            info.constantes[cst.nom] = self.resoudre_type(cst.type_annot) if cst.type_annot else None  # type: ignore[assignment]
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
            info.descriptions[champ.nom] = f"champ {champ.nom}: {t}" + (" = …" if champ.defaut is not None else "")
            info.positions[champ.nom] = (self.fichier, champ.ligne, champ.colonne)
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
            if getattr(m, "statique", False):
                if getattr(m, "abstraite", False):
                    raise self.erreur("une méthode ne peut pas être à la fois statique et abstraite", m)
                if m.nom in info.methodes:
                    raise self.erreur(f"'{m.nom}' est déjà une méthode d'objet dans la classe parente", m)
                info.statiques[m.nom] = t
                info.descriptions[m.nom] = self.signature_fonction(m, t, prefixe="statique ")
                pos = getattr(m, "position_nom", (m.ligne, m.colonne))
                info.positions[m.nom] = (self.fichier, pos[0], pos[1])
                m.type = t  # type: ignore[attr-defined]
                continue
            if m.nom in info.statiques:
                raise self.erreur(f"'{m.nom}' est déjà une méthode statique dans la classe parente", m)
            if getattr(m, "abstraite", False):
                info.abstraites.add(m.nom)
            else:
                info.abstraites.discard(m.nom)
            ancienne = info.methodes.get(m.nom)
            if ancienne is not None and not compatible(t, ancienne):
                raise self.erreur(
                    f"la méthode '{m.nom}' ({t}) n'est pas compatible avec celle de la classe parente ({ancienne})", m)
            info.methodes[m.nom] = t
            info.descriptions[m.nom] = self.signature_fonction(m, t, prefixe="abstraite " if getattr(m, "abstraite", False) else "méthode ")
            pos = getattr(m, "position_nom", (m.ligne, m.colonne))
            info.positions[m.nom] = (self.fichier, pos[0], pos[1])
            m.type = t  # type: ignore[attr-defined]
        info.prete = True
        if getattr(info, "symbole", None) is not None:
            info.symbole.description = info.signature()  # type: ignore[attr-defined]

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
        for cst in getattr(c, "constantes", []):
            t = self.expression(cst.valeur)
            attendu = info.constantes.get(cst.nom)
            if attendu is None:
                if t in (NUL, RIEN) or t == LISTE_VIDE:
                    raise self.erreur(f"impossible de déduire le type de la constante '{cst.nom}' : précisez-le", cst)
                info.constantes[cst.nom] = t
            elif not compatible(t, attendu):
                raise self.erreur(f"la constante '{cst.nom}' est de type {attendu}, mais reçoit un {t}", cst.valeur)
            info.descriptions[cst.nom] = f"constante {info.nom}.{cst.nom}: {info.constantes[cst.nom]}"
            info.positions[cst.nom] = (self.fichier, cst.ligne, cst.colonne)
        ancienne = self.classe_courante
        self.classe_courante = info.type
        for m in c.methodes:
            self._verifier_decorateurs(m)
            if getattr(m, "statique", False):
                self._verifier_fonction(m, soi=None)
            elif m.corps is not None:
                self._verifier_fonction(m, soi=info.type, parent=info.parent.type if info.parent else None)
        self.classe_courante = ancienne
        return False

    def _verifier_decorateurs(self, f: DeclFonction) -> None:
        for d in getattr(f, "decorateurs", []):
            td = self.expression(d)
            if td == QUELCONQUE:
                continue
            if not isinstance(td, TypeFonction):
                raise self.erreur(f"un décorateur doit être une fonction, mais '@' reçoit un {td}", d)
            if td.minimum > 1 or (td.maximum is not None and td.maximum < 1):
                raise self.erreur(f"un décorateur doit accepter exactement 1 argument (la fonction décorée), mais celui-ci : {td}", d)
            if td.retour == RIEN:
                raise self.erreur("un décorateur doit retourner une fonction (celle qui remplacera la fonction décorée)", d)
            if td.retour != QUELCONQUE and not isinstance(td.retour, TypeFonction):
                raise self.erreur(f"un décorateur doit retourner une fonction, mais celui-ci retourne un {td.retour}", d)

    def affinements(self, e: Expr) -> tuple[dict[str, Type], dict[str, Type]]:
        """Pour une condition, retourne (types affinés si vraie, types affinés si fausse).
        Reconnaît `x != nul`, `x == nul`, `non …`, `a et b`, `a ou b`."""
        if isinstance(e, Binaire) and e.op in ("==", "!="):
            g, d = e.gauche, e.droite
            if isinstance(d, Litteral) and d.valeur is None and isinstance(g, Identifiant):
                ident = g
            elif isinstance(g, Litteral) and g.valeur is None and isinstance(d, Identifiant):
                ident = d
            else:
                return {}, {}
            sym = self.portee.chercher(ident.nom)
            if sym is None or not est_optionnel(sym.type):
                return {}, {}
            precis = {ident.nom: sans_nul(sym.type)}
            return (precis, {}) if e.op == "!=" else ({}, precis)
        if isinstance(e, Unaire) and e.op == "non":
            v, f = self.affinements(e.operande)
            return f, v
        if isinstance(e, Logique):
            v1, f1 = self.affinements(e.gauche)
            v2, f2 = self.affinements(e.droite)
            if e.op == "et":
                return {**v1, **v2}, {k: t for k, t in f1.items() if k in f2 and f2[k] == t}
            return {k: t for k, t in v1.items() if k in v2 and v2[k] == t}, {**f1, **f2}
        return {}, {}

    def affiner(self, precis: dict[str, Type]) -> None:
        """Déclare dans la portée courante des copies affinées des symboles (T? devient T)."""
        for nom, t in precis.items():
            sym = self.portee.chercher(nom)
            if sym is None:
                continue
            copie = Symbole(t, sym.constante, True, sym.genre, sym.description, sym.position, sym.fichier)
            copie.type_declare = sym.type_declare or sym.type
            self.portee.symboles[nom] = copie

    def bloc(self, bloc: Bloc, precis: dict[str, Type] | None = None) -> bool:
        """Vérifie un bloc. Retourne True si le bloc termine toujours (retourner/arreter/continuer)."""
        self.ouvrir()
        if precis:
            self.affiner(precis)
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

    def i_DeclEnum(self, e: DeclEnum) -> bool:
        return False

    def _types_multiples(self, valeurs: list[Expr], n: int, noeud) -> list[Type]:
        """Types des n valeurs d'une affectation multiple (n expressions, ou une liste à déstructurer)."""
        if len(valeurs) == n:
            types = [self.expression(v) for v in valeurs]
            for v, t in zip(valeurs, types):
                if t == RIEN:
                    raise self.erreur("cette valeur est le résultat d'une fonction qui ne retourne rien", v)
            return types
        t = self.expression(valeurs[0])
        if t == QUELCONQUE:
            return [QUELCONQUE] * n
        if not est_liste(t):
            raise self.erreur(f"pour déstructurer, la valeur doit être une liste (de {n} éléments), mais c'est un {t}", valeurs[0])
        elem = element_de(t)
        return [elem if elem.nom != "?" else QUELCONQUE] * n

    def i_DeclMultiple(self, d: DeclMultiple) -> bool:
        types = self._types_multiples(d.valeurs, len(d.noms), d)
        d.types = types  # type: ignore[attr-defined]
        for nom, t, pos in zip(d.noms, types, d.positions):
            if t == NUL:
                raise self.erreur(f"impossible de déduire le type de '{nom}' depuis 'nul' : utilisez une déclaration simple avec un type", d)
            if t == LISTE_VIDE:
                t = liste_de(QUELCONQUE)
            elif t == DICO_VIDE:
                t = dico_de(QUELCONQUE, QUELCONQUE)
            faux = Identifiant(nom, ligne=pos[0], colonne=pos[1])
            faux.position_nom = pos  # type: ignore[attr-defined]
            self.declarer(nom, t, faux, d.constante)
        return False

    def i_AffectationMultiple(self, a: AffectationMultiple) -> bool:
        cibles_types = []
        for c in a.cibles:
            if isinstance(c, Identifiant):
                sym = self.portee.chercher(c.nom)
                if sym is None:
                    raise self.erreur(f"variable '{c.nom}' inconnue", c)
                if sym.constante:
                    raise self.erreur(f"'{c.nom}' est une constante : impossible de la modifier", c)
                self.enregistrer(c, c.nom, sym)
                sym.initialisee = True
                c.type = sym.type_declare or sym.type  # type: ignore[attr-defined]
                cibles_types.append(c.type)  # type: ignore[attr-defined]
            else:
                cibles_types.append(self.expression(c))
        types = self._types_multiples(a.valeurs, len(a.cibles), a)
        for c, tc, tv in zip(a.cibles, cibles_types, types):
            if not compatible(tv, tc):
                nom = c.nom if isinstance(c, (Identifiant, Membre)) else "cette cible"
                raise self.erreur(f"impossible d'affecter un {tv} à '{nom}' de type {tc}{self.aide_optionnel(tv)}", a)
        a.types = cibles_types  # type: ignore[attr-defined]
        return False

    def i_DeclVariable(self, d: DeclVariable) -> bool:
        t_annot = self.resoudre_type(d.type_annot) if d.type_annot else None
        if t_annot == RIEN:
            raise self.erreur("une variable ne peut pas être de type 'rien'", d.type_annot)
        if d.valeur is not None:
            t_val = self.typer(d.valeur, t_annot)
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
                raise self.erreur(f"'{d.nom}' est de type {t_annot}, mais reçoit un {t_val}{self.aide_optionnel(t_val)}", d.valeur)
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
            self.enregistrer(a.cible, a.cible.nom, sym)
            if sym.constante:
                raise self.erreur(f"'{a.cible.nom}' est une constante : impossible de la modifier", a.cible)
            t_cible = sym.type_declare or sym.type
            a.cible.type = t_cible  # type: ignore[attr-defined]
            sym_affine = sym if sym.type_declare is not None else None
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
        t_val = self.typer(a.valeur, t_cible)
        if a.op == "=":
            t_res = t_val
        else:
            t_res = self.type_binaire(a.op[0], t_cible, t_val, a)
        if t_res == RIEN:
            raise self.erreur("affectation d'une valeur de type 'rien'", a.valeur)
        if not compatible(t_res, t_cible):
            raise self.erreur(f"impossible d'affecter un {t_res} à une cible de type {t_cible}{self.aide_optionnel(t_res)}", a.valeur)
        if isinstance(a.cible, Identifiant) and sym_affine is not None and not compatible(t_res, sym_affine.type):
            sym_affine.type = sym_affine.type_declare   # l'affinement T? -> T ne tient plus (E3)
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
        si_vrai, si_faux = self.affinements(s.condition)
        t1 = self.bloc(s.alors, si_vrai)
        if s.sinon is None:
            if t1 and si_faux:
                self.affiner(si_faux)   # `si x == nul: retourner fin` → x est précis ensuite
            return False
        if isinstance(s.sinon, Si):
            self.ouvrir()
            self.affiner(si_faux)
            t2 = self.instruction(s.sinon)
            self.fermer()
        else:
            t2 = self.bloc(s.sinon, si_faux)
        if t1 and not t2 and si_faux:
            self.affiner(si_faux)
        if t2 and not t1 and si_vrai:
            self.affiner(si_vrai)
        return t1 and t2

    def i_TantQue(self, t: TantQue) -> bool:
        self.condition(t.condition, "tantque")
        si_vrai, _ = self.affinements(t.condition)
        self.profondeur_boucle += 1
        self.bloc(t.corps, si_vrai)
        self.profondeur_boucle -= 1
        # `tantque vrai:` sans 'arreter' ne rend jamais la main : ce qui suit est inatteignable
        if isinstance(t.condition, Litteral) and t.condition.valeur is True and not _contient_arret(t.corps):
            return True
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
            pos2 = getattr(p, "position_nom2", None)
            sym2 = self.declarer(p.variable2, t2, p)
            if pos2 is not None:
                sym2.position = pos2
                self.enregistrements[-1]["ligne"], self.enregistrements[-1]["colonne"] = pos2
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
        if f.corps is None:
            raise self.erreur("une fonction abstraite n'est possible que dans une classe", f)
        self._verifier_decorateurs(f)
        return self._verifier_fonction(f)

    def _verifier_fonction(self, f: DeclFonction, soi: TypeClasse | None = None,
                           parent: TypeClasse | None = None) -> bool:
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
        self.pile_fonctions.append((f.ligne, getattr(f, "ligne_fin", f.ligne)))
        noms = set()
        if soi is not None:
            self.declarer("soi", soi, f, constante=True, genre="soi", description=f"soi: {soi}")
        if parent is not None:
            self.declarer("parent", parent, f, constante=True, genre="parent", description=f"parent: {parent}")
        for p, tp in zip(f.parametres, t.parametres):
            if p.nom in noms:
                raise self.erreur(f"paramètre '{p.nom}' en double", p)
            if tp == RIEN:
                raise self.erreur("un paramètre ne peut pas être de type 'rien'", p)
            noms.add(p.nom)
            self.declarer(p.nom, tp, p, genre="paramètre")
        termine = self.bloc(f.corps)
        self.pile_fonctions.pop()
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
        if attendu is INFERER:
            if r.valeur is None:
                r.verif_runtime = False  # type: ignore[attr-defined]
                return True
            t = self.expression(r.valeur)
            if t == RIEN:
                raise self.erreur("'retourner' reçoit le résultat d'une fonction qui ne retourne rien", r.valeur)
            self.inference_retour.append(t)
            r.verif_runtime = False  # type: ignore[attr-defined]
            return True
        if r.valeur is None:
            if attendu != RIEN:
                raise self.erreur(f"cette fonction doit retourner un {attendu}, mais 'retourner' est vide", r)
            r.verif_runtime = False  # type: ignore[attr-defined]
            return True
        t = self.typer(r.valeur, attendu)
        if attendu == RIEN:
            raise self.erreur("cette fonction ne retourne rien ('rien') : utilisez 'retourner' sans valeur", r.valeur)
        if not compatible(t, attendu):
            raise self.erreur(f"la fonction doit retourner un {attendu}, mais retourne un {t}{self.aide_optionnel(t)}", r.valeur)
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
                self.declarer(nom, sym.type, imp, constante=True, genre=sym.genre, description=sym.description)
        else:
            alias = imp.alias or m.nom
            imp.alias = alias
            self.declarer(alias, TypeModule(m.nom, (), m.chemin), imp, constante=True, genre="module",
                          description=f"module {alias} (\"{imp.chemin}\")")
        return False

    def i_Selon(self, s: Selon) -> bool:
        t = self.expression(s.sujet)
        if t == RIEN:
            raise self.erreur("'selon' ne peut pas porter sur une valeur de type 'rien'", s.sujet)
        termine = True
        couverts: set[str] = set()
        for c in s.cas:
            for v in c.valeurs:
                tv = self.expression(v)
                if t != QUELCONQUE and tv != QUELCONQUE and not compatible(tv, t) and not compatible(t, tv):
                    raise self.erreur(f"ce 'cas' ({tv}) ne peut jamais correspondre à un {t}", v)
                if isinstance(t, TypeEnum) and isinstance(v, Membre):
                    if v.nom in couverts:
                        raise self.erreur(f"le cas '{t.nom}.{v.nom}' est traité deux fois", v)
                    couverts.add(v.nom)
            termine = self.bloc(c.corps) and termine
        if s.sinon is None:
            if isinstance(t, TypeEnum):
                manquants = [v for v in t.valeurs if v not in couverts]
                if manquants:
                    raise self.erreur(f"ce 'selon' sur {t.nom} n'est pas complet : il manque {', '.join(t.nom + '.' + m for m in manquants)} "
                                      f"(ajoutez les cas manquants ou un 'sinon')", s)
                return termine
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

    def typer(self, e: Expr, attendu: Type | None) -> Type:
        """Comme `expression`, mais transmet le type attendu (typage contextuel des fonctions anonymes)."""
        if isinstance(e, FonctionAnonyme) and isinstance(attendu, TypeFonction):
            e.attendu = attendu  # type: ignore[attr-defined]
        elif isinstance(e, Conditionnelle) and attendu is not None:
            e.attendu = attendu  # type: ignore[attr-defined]
        return self.expression(e)

    @staticmethod
    def aide_optionnel(t: Type) -> str:
        if est_optionnel(t):
            return f" (la valeur peut être nul : testez-la avec 'si x != nul' ou donnez une valeur de repli avec 'x ?? valeur')"
        return ""

    def e_Conditionnelle(self, c: Conditionnelle) -> Type:
        self.condition(c.condition, "si")
        si_vrai, si_faux = self.affinements(c.condition)
        attendu = getattr(c, "attendu", None)
        self.ouvrir()
        self.affiner(si_vrai)
        t1 = self.typer(c.alors, attendu)
        self.fermer()
        self.ouvrir()
        self.affiner(si_faux)
        t2 = self.typer(c.sinon, attendu)
        self.fermer()
        if t1 == RIEN or t2 == RIEN:
            raise self.erreur("les deux branches de 'si … alors … sinon …' doivent produire une valeur", c)
        if t1 == NUL and t2 != NUL:
            return optionnel_de(t2)
        if t2 == NUL and t1 != NUL:
            return optionnel_de(t1)
        if t1 == t2:
            return t1
        if compatible(t1, t2) and not compatible(t2, t1):
            return t2
        if compatible(t2, t1) and not compatible(t1, t2):
            return t1
        if compatible(t1, t2):
            return unifier(t1, t2)
        raise self.erreur(f"les deux branches de 'si … alors … sinon …' ont des types incompatibles : {t1} et {t2}", c)

    def e_FonctionAnonyme(self, fa: FonctionAnonyme) -> Type:
        attendu: TypeFonction | None = getattr(fa, "attendu", None)
        params: list[Type] = []
        variadique = bool(fa.parametres) and fa.parametres[-1].variadique
        for i, p in enumerate(fa.parametres):
            if p.type_annot is not None:
                t = self.resoudre_type(p.type_annot)
            elif attendu is not None and i < len(attendu.fixes):
                t = attendu.fixes[i]
            elif attendu is not None and attendu.variadique:
                t = attendu.parametres[-1]
            else:
                raise self.erreur(f"impossible de déduire le type du paramètre '{p.nom}' : précisez-le (ex : {p.nom}: entier)", p)
            if p.variadique and not est_liste(t):
                raise self.erreur(f"le paramètre '...{p.nom}' doit être une liste", p)
            params.append(t)
        obligatoires = sum(1 for p in fa.parametres if p.defaut is None and not p.variadique)
        retour_annot = self.resoudre_type(fa.type_retour) if fa.type_retour is not None else None
        # vérification du corps
        ancien_retour, ancienne_boucle, ancienne_inference = self.type_retour_attendu, self.profondeur_boucle, self.inference_retour
        self.type_retour_attendu = retour_annot if retour_annot is not None else INFERER
        self.inference_retour = []
        self.profondeur_boucle = 0
        self.ouvrir(nouvelle_fonction=True)
        self.pile_fonctions.append((fa.ligne, getattr(fa, "ligne_fin", fa.ligne)))
        noms = set()
        for p, tp in zip(fa.parametres, params):
            if p.nom in noms:
                raise self.erreur(f"paramètre '{p.nom}' en double", p)
            noms.add(p.nom)
            if p.defaut is not None:
                td = self.expression(p.defaut)
                if not compatible(td, tp):
                    raise self.erreur(f"la valeur par défaut du paramètre '{p.nom}' doit être un {tp}, mais c'est un {td}", p.defaut)
            self.declarer(p.nom, tp, p, genre="paramètre")
        if fa.expression is not None:
            t_expr = self.expression(fa.expression)
            if t_expr == RIEN:
                fa.corps_est_instruction = True  # type: ignore[attr-defined]
                retour = RIEN
                if retour_annot not in (None, RIEN):
                    raise self.erreur(f"cette fonction anonyme doit retourner un {retour_annot}, mais son expression ne retourne rien", fa.expression)
            else:
                fa.corps_est_instruction = False  # type: ignore[attr-defined]
                retour = retour_annot if retour_annot is not None else t_expr
                if retour_annot is not None and not compatible(t_expr, retour_annot):
                    raise self.erreur(f"cette fonction anonyme doit retourner un {retour_annot}, mais retourne un {t_expr}", fa.expression)
            termine = True
        else:
            termine = self.bloc(fa.corps)
            if retour_annot is not None:
                retour = retour_annot
            else:
                types = [t for t in self.inference_retour]
                retour = RIEN
                for t in types:
                    retour = t if retour == RIEN else unifier(retour, t)
            if retour != RIEN and not termine:
                raise self.erreur(f"cette fonction anonyme doit retourner un {retour} dans tous les cas (il manque un 'retourner' ?)", fa)
        self.pile_fonctions.pop()
        self.fermer()
        self.type_retour_attendu, self.profondeur_boucle, self.inference_retour = ancien_retour, ancienne_boucle, ancienne_inference
        t = TypeFonction("fonction", (), tuple(params), retour, obligatoires, variadique)
        if attendu is not None and not compatible(t, attendu):
            raise self.erreur(f"cette fonction anonyme ({t}) ne correspond pas au type attendu ({attendu})", fa)
        fa.type_fonction = t  # type: ignore[attr-defined]
        return t

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
            if k not in TYPES_CLES and k != QUELCONQUE and not isinstance(k, TypeEnum):
                raise self.erreur(f"une clé de dictionnaire doit être un texte, un entier ou un booleen, pas un {k}", cle)
            v = self.expression(val)
            if v == RIEN or v == NUL:
                raise self.erreur("un dictionnaire ne peut pas contenir de valeurs 'rien' ou 'nul'", val)
            tk = k if tk is None else unifier(tk, k)
            tv = v if tv is None else unifier(tv, v)
        return dico_de(tk, tv)

    def e_Identifiant(self, i: Identifiant) -> Type:
        sym = self.portee.chercher(i.nom)
        if sym is not None and sym.type_declare is not None and not self.portee.visible_dans_fonction(i.nom):
            # depuis une fermeture, la variable peut avoir changé : on revient au type déclaré (E3)
            self.enregistrer(i, i.nom, sym)
            return sym.type_declare
        if sym is None:
            if i.nom == "parent":
                raise self.erreur("'parent' ne s'utilise que dans une méthode d'une classe qui 'herite' d'une autre", i)
            raise self.erreur(f"variable '{i.nom}' inconnue", i)
        self.enregistrer(i, i.nom, sym)
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

    def _erreur_sinon_nul(self, base: Type, td: Type, noeud):
        raise self.erreur(f"'??' : la valeur de repli doit être un {base}, mais c'est un {td}", noeud)

    def e_Etalement(self, e) -> Type:
        t = self.expression(e.valeur)
        if t != QUELCONQUE and not est_liste(t):
            raise self.erreur(f"'...' s'applique à une liste, mais reçoit un {t}", e)
        return t

    def e_Binaire(self, b: Binaire) -> Type:
        tg = self.expression(b.gauche)
        td = self.expression(b.droite)
        return self.type_binaire(b.op, tg, td, b)

    OPERATEURS_CLASSE = {"+": "plus", "-": "moins", "*": "fois", "/": "divise", "%": "modulo",
                         "<": "inferieur", ">": "inferieur", "<=": "inferieur", ">=": "inferieur", "==": "egal", "!=": "egal"}

    def _operateur_classe(self, op: str, tg: Type, td: Type, noeud) -> Type | None:
        """Surcharge d'opérateur : `a + b` appelle `a.plus(b)` si la classe définit la méthode."""
        if op in (">", ">="):
            tg, td = td, tg
        if not isinstance(tg, TypeClasse):
            return None
        info = self.classes.get(tg.nom)
        nom = self.OPERATEURS_CLASSE.get(op)
        if info is None or nom is None or nom not in info.methodes:
            return None
        tm = info.methodes[nom]
        if len(tm.parametres) != 1 or tm.minimum > 1:
            raise self.erreur(f"la méthode d'opérateur '{nom}' de '{tg.nom}' doit prendre exactement 1 paramètre", noeud)
        if td != QUELCONQUE and not compatible(td, tm.parametres[0]):
            raise self.erreur(f"'{op}' sur un {tg.nom} attend un {tm.parametres[0]} à droite, mais reçoit un {td}", noeud)
        if nom in ("egal", "inferieur"):
            if tm.retour != BOOLEEN:
                raise self.erreur(f"la méthode '{nom}' de '{tg.nom}' doit retourner un booleen", noeud)
            return BOOLEEN
        return tm.retour

    def type_binaire(self, op: str, tg: Type, td: Type, noeud) -> Type:
        if op == "??":
            if tg == QUELCONQUE:
                return QUELCONQUE
            if not est_optionnel(tg):
                raise self.erreur(f"'??' est inutile : la valeur de gauche est un {tg}, elle ne peut jamais être nul", noeud)
            base = sans_nul(tg)
            if td == NUL or est_optionnel(td):
                return optionnel_de(base) if compatible(sans_nul(td), base) or td == NUL else self._erreur_sinon_nul(base, td, noeud)
            if compatible(td, base):
                return base
            if compatible(base, td):
                return td
            return self._erreur_sinon_nul(base, td, noeud)
        if op == "..":
            if tg != ENTIER and tg != QUELCONQUE:
                raise self.erreur(f"'..' attend deux entiers, mais la borne de gauche est un {tg}", noeud)
            if td != ENTIER and td != QUELCONQUE:
                raise self.erreur(f"'..' attend deux entiers, mais la borne de droite est un {td}", noeud)
            return liste_de(ENTIER)
        if isinstance(tg, TypeEnum) and isinstance(td, TypeEnum) and tg.nom == td.nom and op in ("<", ">", "<=", ">="):
            return BOOLEEN
        if op not in ("==", "!=") and (est_optionnel(tg) or est_optionnel(td)):
            t_opt = tg if est_optionnel(tg) else td
            raise self.erreur(f"'{op}' impossible sur un {t_opt}{self.aide_optionnel(t_opt)}", noeud)
        surcharge = self._operateur_classe(op, tg, td, noeud)
        if surcharge is not None:
            return surcharge
        if isinstance(tg, TypeClasse) and op in self.OPERATEURS_CLASSE and op not in ("==", "!="):
            raise self.erreur(f"'{op}' n'est pas défini pour un {tg.nom} : ajoutez une méthode "
                              f"'{self.OPERATEURS_CLASSE[op]}(autre: {tg.nom})' à la classe", noeud)
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
        t = self.expression(l.gauche)
        if t != BOOLEEN and t != QUELCONQUE:
            raise self.erreur(f"'{l.op}' attend des booleens, mais reçoit un {t}", l.gauche)
        # `x != nul et f(x)` : à droite de 'et', x est précis ; `x == nul ou f(x)` : idem à droite de 'ou'
        si_vrai, si_faux = self.affinements(l.gauche)
        precis = si_vrai if l.op == "et" else si_faux
        self.ouvrir()
        self.affiner(precis)
        t = self.expression(l.droite)
        self.fermer()
        if t != BOOLEEN and t != QUELCONQUE:
            raise self.erreur(f"'{l.op}' attend des booleens, mais reçoit un {t}", l.droite)
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
            self.enregistrer(m, m.nom, sym)
            return sym.type
        if t == TYPE_META_ENUM and isinstance(m.objet, (Identifiant, Membre)) and m.objet.nom in self.enums:
            te = self.enums[m.objet.nom]
            if m.nom in te.valeurs:
                sym = Symbole(te, constante=True, genre="constante", description=f"{te.nom}.{m.nom} (valeur {te.valeurs.index(m.nom)} de l'énumération)")
                self.enregistrer(m, m.nom, sym)
                return te
            if m.nom == "valeurs":
                return liste_de(te)
            raise self.erreur(f"l'énumération '{te.nom}' n'a pas de valeur '{m.nom}' (valeurs : {', '.join(te.valeurs)})", m)
        if isinstance(t, TypeEnum):
            if m.nom == "nom":
                return TEXTE
            if m.nom == "indice":
                return ENTIER
            raise self.erreur(f"une valeur de '{t.nom}' n'a que '.nom' (texte) et '.indice' (entier), pas '.{m.nom}'", m)
        if t == TYPE_META_CLASSE and isinstance(m.objet, Identifiant) and m.objet.nom in self.classes:
            info = self.classes[m.objet.nom]
            if m.nom in info.statiques or m.nom in info.constantes:
                pos = info.positions.get(m.nom, (self.fichier, 0, 0))
                sym = Symbole(info.statiques.get(m.nom) or info.constantes[m.nom], constante=True,
                              genre="statique" if m.nom in info.statiques else "constante",
                              description=info.descriptions.get(m.nom, m.nom), position=pos[1:], fichier=pos[0])
                self.enregistrer(m, m.nom, sym)
                return sym.type
            if m.nom in info.methodes or m.nom in info.champs:
                raise self.erreur(f"'{m.nom}' est un membre d'objet : il faut un objet '{info.nom}' pour y accéder "
                                  f"(ou déclarez la méthode 'statique')", m)
            dispo = ", ".join(sorted(list(info.statiques) + list(info.constantes))) or "aucun"
            raise self.erreur(f"la classe '{info.nom}' n'a pas de méthode statique ni de constante '{m.nom}' (disponibles : {dispo})", m)
        if not isinstance(t, TypeClasse):
            if m.nom in METHODES_PAR_TYPE.get(t.nom, ()):
                raise self.erreur(f"'{m.nom}' est une méthode : il faut l'appeler avec des parenthèses, ex : .{m.nom}()", m)
            raise self.erreur(f"une valeur de type {t} n'a pas de champ ni de méthode ('.{m.nom}'){self.aide_optionnel(t)}", m)
        info = self.classes[t.nom]
        if m.nom.startswith("_") and (m.nom in info.champs or m.nom in info.methodes):
            if not (isinstance(m.objet, Identifiant) and m.objet.nom in ("soi", "parent")):
                raise self.erreur(f"'{m.nom}' est privé (son nom commence par '_') : accessible seulement via 'soi.{m.nom}' "
                                  f"dans les méthodes de '{t.nom}'", m)
        if m.nom in info.champs or m.nom in info.methodes:
            pos = info.positions.get(m.nom, (self.fichier, 0, 0))
            sym = Symbole(info.champs.get(m.nom) or info.methodes[m.nom], genre="champ" if m.nom in info.champs else "méthode",
                          description=info.descriptions.get(m.nom, m.nom), position=pos[1:], fichier=pos[0])
            self.enregistrer(m, m.nom, sym)
        if m.nom in info.champs:
            return info.champs[m.nom]
        if m.nom in info.methodes:
            return info.methodes[m.nom]
        proches = [n for n in list(info.champs) + list(info.methodes) if n.lower() == m.nom.lower()]
        aide = f" (vouliez-vous dire '{proches[0]}' ?)" if proches else ""
        raise self.erreur(f"la classe '{t.nom}' n'a pas de champ ni de méthode '{m.nom}'{aide}", m)

    def e_MethodeNative(self, a: Appel, t_obj: Type) -> Type:
        """`liste.ajouter(x)` ≡ `ajouter(liste, x)` : notation méthode pour les fonctions natives."""
        nom = a.cible.nom
        dispo = METHODES_PAR_TYPE[t_obj.nom]
        if nom not in dispo or nom not in NATIFS:
            proches = [n for n in dispo if n.lower().startswith(nom.lower()[:3])]
            aide = f" (vouliez-vous dire '{proches[0]}' ?)" if proches else f" (disponibles : {', '.join(dispo)})"
            raise self.erreur(f"un {t_obj} n'a pas de méthode '{nom}'{aide}", a.cible)
        if a.nommes:
            raise self.erreur("les arguments nommés ne sont pas possibles ici", a.nommes[0][1])
        if any(isinstance(arg, Etalement) for arg in a.arguments):
            raise self.erreur(f"'...' n'est pas possible avec la méthode native '{nom}'", a)
        natif = NATIFS[nom]
        types = [t_obj]
        for i, arg in enumerate(a.arguments, 1):
            attendu = natif.attendu(i, types) if natif.attendu is not None else None
            types.append(self.typer(arg, attendu))
        for arg, t in zip(a.arguments, types[1:]):
            if t == RIEN:
                raise self.erreur("cet argument est le résultat d'une fonction qui ne retourne rien", arg)
        sym = self.portee.chercher(nom)
        if sym is None or sym.type != Type("natif"):
            sym = Symbole(Type("natif"), constante=True, genre="natif", description=nom)
        self.enregistrer(a.cible, nom, sym)
        a.natif = natif  # type: ignore[attr-defined]
        a.methode_native = True  # type: ignore[attr-defined]
        a.verifs_runtime = ()  # type: ignore[attr-defined]
        a.cible.type = Type("natif")  # type: ignore[attr-defined]
        return natif.verifier(types, lambda msg: self.erreur(msg, a))

    def e_Construction(self, a: Appel, info: InfoClasse) -> Type:
        a.cible.type = TYPE_META_CLASSE  # type: ignore[attr-defined]
        if isinstance(a.cible, Identifiant):
            self.enregistrer(a.cible, a.cible.nom, self.portee.chercher(a.cible.nom))
        else:
            self.enregistrer(a.cible, a.cible.nom, getattr(info, "symbole", None))
        a.natif = None  # type: ignore[attr-defined]
        a.classe = info.nom  # type: ignore[attr-defined]
        if info.abstraites:
            raise self.erreur(f"'{info.nom}' est abstraite : il manque l'implémentation de "
                              f"{', '.join(repr(n) for n in sorted(info.abstraites))}. Créez une classe enfant qui les implémente", a)
        if any(isinstance(arg, Etalement) for arg in a.arguments):
            raise self.erreur("'...' n'est pas possible pour créer un objet", a)
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
            t = self.typer(arg, info.champs[nom])
            if not compatible(t, info.champs[nom]):
                raise self.erreur(f"champ '{nom}' de '{info.nom}' : {info.champs[nom]} attendu, mais {t} fourni{self.aide_optionnel(t)}", arg)
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
            base = t_obj.nom if not isinstance(t_obj, (TypeClasse, TypeModule, TypeFonction, TypeEnum)) else None
            if base in METHODES_PAR_TYPE:
                return self.e_MethodeNative(a, t_obj)
        if a.nommes:
            raise self.erreur("les arguments nommés ('nom = valeur') ne sont possibles que pour créer un objet "
                              "(ex : Personne(nom = \"Awa\"))", a.nommes[0][1])
        if isinstance(a.cible, Identifiant) and a.cible.nom in NATIFS and self.portee.chercher(a.cible.nom).type == Type("natif"):
            natif = NATIFS[a.cible.nom]
            a.cible.type = Type("natif")  # type: ignore[attr-defined]
            self.enregistrer(a.cible, a.cible.nom, self.portee.chercher(a.cible.nom))
            if any(isinstance(arg, Etalement) for arg in a.arguments):
                raise self.erreur(f"'...' n'est pas possible avec la fonction native '{a.cible.nom}'", a)
            types = []
            for i, arg in enumerate(a.arguments):
                attendu = natif.attendu(i, types) if natif.attendu is not None else None
                types.append(self.typer(arg, attendu))
            for arg, t in zip(a.arguments, types):
                if t == RIEN:
                    raise self.erreur("cet argument est le résultat d'une fonction qui ne retourne rien", arg)
            a.natif = natif  # type: ignore[attr-defined]
            a.verifs_runtime = ()  # type: ignore[attr-defined]
            return natif.verifier(types, lambda msg: self.erreur(msg, a))
        tc = self.expression(a.cible)
        types = []
        for i, arg in enumerate(a.arguments):
            attendu = None
            if isinstance(tc, TypeFonction) and not isinstance(arg, Etalement):
                if i < len(tc.fixes):
                    attendu = tc.fixes[i]
                elif tc.variadique and tc.parametres[-1].params:
                    attendu = tc.parametres[-1].params[0]
            types.append(self.typer(arg, attendu))
        a.natif = None  # type: ignore[attr-defined]
        if tc == QUELCONQUE:
            a.verifs_runtime = ()  # type: ignore[attr-defined]
            return QUELCONQUE
        if not isinstance(tc, TypeFonction):
            raise self.erreur(f"une valeur de type {tc} ne peut pas être appelée comme une fonction{self.aide_optionnel(tc)}", a)
        nom = a.cible.nom if isinstance(a.cible, Identifiant) else a.cible.nom if isinstance(a.cible, Membre) else "la fonction"
        etale = any(isinstance(arg, Etalement) for arg in a.arguments)
        if etale:
            # le nombre d'arguments n'est connu qu'à l'exécution : on vérifie ce qu'on peut
            a.verifs_runtime = ()  # type: ignore[attr-defined]
            fixes = [(arg, t) for arg, t in zip(a.arguments, types) if not isinstance(arg, Etalement)]
            if tc.maximum is not None and len(fixes) > tc.maximum:
                raise self.erreur(f"'{nom}' attend au plus {tc.maximum} argument(s)", a)
            for i, (arg, t) in enumerate(fixes):
                if i < len(tc.fixes) and not compatible(t, tc.fixes[i]):
                    raise self.erreur(f"argument {i + 1} de '{nom}' : {tc.fixes[i]} attendu, mais {t} fourni", arg)
            return tc.retour
        if len(types) < tc.minimum or (tc.maximum is not None and len(types) > tc.maximum):
            if tc.maximum is None:
                attendu = f"au moins {tc.minimum}"
            else:
                attendu = (f"{tc.maximum}" if tc.minimum == tc.maximum else f"entre {tc.minimum} et {tc.maximum}")
            raise self.erreur(f"'{nom}' attend {attendu} argument(s), mais {len(types)} fourni(s)", a)
        verifs = []
        n_fixes = len(tc.fixes)
        t_reste = tc.parametres[-1].params[0] if tc.variadique and tc.parametres[-1].params else QUELCONQUE
        for i, (arg, t) in enumerate(zip(a.arguments, types), 1):
            tp = tc.parametres[i - 1] if i <= n_fixes else t_reste
            if not compatible(t, tp):
                raise self.erreur(f"argument {i} de '{nom}' : {tp} attendu, mais {t} fourni{self.aide_optionnel(t)}", arg)
            verifs.append(t == QUELCONQUE and tp != QUELCONQUE)
        a.verifs_runtime = tuple(verifs)  # type: ignore[attr-defined]
        return tc.retour


def verifier(prog: Programme, fichier: str = "<entrée>") -> None:
    Verificateur(fichier).verifier_programme(prog)


def _contient_arret(bloc) -> bool:
    """Le bloc contient-il un 'arreter' s'appliquant à la boucle courante (hors boucles et fonctions imbriquées) ?"""
    import dataclasses

    def visiter(n) -> bool:
        if isinstance(n, Arreter):
            return True
        if isinstance(n, (TantQue, Pour, DeclFonction, FonctionAnonyme, DeclClasse)):
            return False
        if isinstance(n, list):
            return any(visiter(x) for x in n)
        if dataclasses.is_dataclass(n) and not isinstance(n, type):
            return any(visiter(getattr(n, f.name)) for f in dataclasses.fields(n))
        return False
    return visiter(bloc.instructions)
