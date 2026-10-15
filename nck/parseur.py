"""Analyseur syntaxique : transforme les jetons en arbre syntaxique."""

from .arbre import (
    Affectation, Appel, Arreter, Attraper, Binaire, Bloc, Cas, Champ, Continuer, DeclClasse, DeclFonction,
    DeclVariable, DicoLit, Essayer, ExprInstr, Expr, Identifiant, Importer, Index, Instr, Lever, ListeLit, Litteral,
    Logique, Membre, Parametre, Pour, Programme, Retourner, Selon, Si, TantQue, TexteFormate, TypeAnnot, Unaire,
)
from .erreurs import ErreurSyntaxe
from .lexeur import Jeton, lexer

AFFECTATIONS_COMPOSEES = {"=", "+=", "-=", "*=", "/="}


class Parseur:
    def __init__(self, jetons: list[Jeton], fichier: str = "<entrée>"):
        self.jetons = jetons
        self.pos = 0
        self.fichier = fichier
        self.profondeur = 0  # > 0 à l'intérieur de ( ) ou [ ] : les retours à la ligne sont ignorés

    # ----- utilitaires -----

    def _sauter_nl_si_imbrique(self) -> None:
        if self.profondeur > 0:
            while self.jetons[self.pos].genre == "nl":
                self.pos += 1

    def courant(self) -> Jeton:
        self._sauter_nl_si_imbrique()
        return self.jetons[self.pos]

    def avancer(self) -> Jeton:
        j = self.courant()
        if j.genre != "fin_fichier":
            self.pos += 1
        return j

    def est(self, genre: str, valeur: object = None) -> bool:
        j = self.courant()
        return j.genre == genre and (valeur is None or j.valeur == valeur)

    def est_op(self, *valeurs: str) -> bool:
        j = self.courant()
        return j.genre == "op" and j.valeur in valeurs

    def est_motcle(self, *valeurs: str) -> bool:
        j = self.courant()
        return j.genre == "motcle" and j.valeur in valeurs

    def erreur(self, message: str, jeton: Jeton | None = None) -> ErreurSyntaxe:
        j = jeton or self.courant()
        return ErreurSyntaxe(message, j.ligne, j.colonne, self.fichier)

    def attendre_op(self, valeur: str, message: str | None = None) -> Jeton:
        if not self.est_op(valeur):
            raise self.erreur(message or f"'{valeur}' attendu, mais {self._decrire(self.courant())} trouvé")
        return self.avancer()

    def attendre_motcle(self, valeur: str) -> Jeton:
        if not self.est_motcle(valeur):
            raise self.erreur(f"mot-clé '{valeur}' attendu, mais {self._decrire(self.courant())} trouvé")
        return self.avancer()

    def attendre_ident(self, message: str = "identifiant attendu") -> Jeton:
        if not self.est("ident"):
            raise self.erreur(f"{message}, mais {self._decrire(self.courant())} trouvé")
        return self.avancer()

    @staticmethod
    def _decrire(j: Jeton) -> str:
        if j.genre == "fin_fichier":
            return "la fin du fichier"
        if j.genre == "nl":
            return "une fin de ligne"
        if j.genre == "texte":
            return f"le texte {j.valeur!r}"
        return f"'{j.valeur}'"

    def sauter_nl(self) -> None:
        while self.jetons[self.pos].genre == "nl" or (self.jetons[self.pos].genre == "op" and self.jetons[self.pos].valeur == ";"):
            self.pos += 1

    def fin_instruction(self) -> None:
        """Une instruction se termine par ';', une fin de ligne, la fin du fichier, ou un mot-clé de fermeture."""
        j = self.jetons[self.pos]
        if j.genre == "op" and j.valeur == ";":
            self.pos += 1
            return
        if j.genre in ("nl", "fin_fichier"):
            return
        if j.genre == "motcle" and j.valeur in ("fin", "sinon", "attraper", "enfin", "cas"):
            return
        raise self.erreur(f"fin d'instruction attendue, mais {self._decrire(j)} trouvé", j)

    # ----- programme -----

    def programme(self) -> Programme:
        instructions: list[Instr] = []
        self.sauter_nl()
        while not self.est("fin_fichier"):
            instructions.append(self.instruction())
            self.sauter_nl()
        return Programme(instructions, ligne=1, colonne=1)

    def bloc_jusqua(self, *terminateurs: str) -> Bloc:
        """Lit des instructions jusqu'à rencontrer un des mots-clés terminateurs (non consommé)."""
        debut = self.courant()
        instructions: list[Instr] = []
        self.sauter_nl()
        while not self.est_motcle(*terminateurs):
            if self.est("fin_fichier"):
                raise self.erreur(f"'fin' attendu pour fermer le bloc commencé ligne {debut.ligne}")
            instructions.append(self.instruction())
            self.sauter_nl()
        return Bloc(instructions, ligne=debut.ligne, colonne=debut.colonne)

    def corps(self, *terminateurs: str) -> tuple[Bloc, bool]:
        """Après ':' : soit un bloc multi-lignes (retourne (bloc, True)),
        soit une seule instruction sur la même ligne (retourne (bloc, False))."""
        self.attendre_op(":", f"':' attendu pour ouvrir le bloc, mais {self._decrire(self.courant())} trouvé")
        if self.jetons[self.pos].genre == "nl":
            return self.bloc_jusqua(*terminateurs), True
        j = self.courant()
        instr = self.instruction()
        return Bloc([instr], ligne=j.ligne, colonne=j.colonne), False

    # ----- instructions -----

    def instruction(self) -> Instr:
        j = self.courant()
        if j.genre == "motcle":
            mot = j.valeur
            if mot in ("variable", "constante"):
                return self.decl_variable()
            if mot == "fonction":
                return self.decl_fonction()
            if mot == "classe":
                return self.decl_classe()
            if mot == "si":
                return self.instr_si()
            if mot == "essayer":
                return self.instr_essayer()
            if mot == "selon":
                return self.instr_selon()
            if mot == "cas":
                raise self.erreur("'cas' inattendu : il doit se trouver dans un bloc 'selon'")
            if mot in ("importer", "depuis"):
                return self.instr_importer()
            if mot == "comme":
                raise self.erreur("'comme' inattendu : il s'utilise après importer \"fichier.nck\"")
            if mot == "lever":
                self.avancer()
                valeur = self.expression()
                self.fin_instruction()
                return Lever(valeur, ligne=j.ligne, colonne=j.colonne)
            if mot in ("attraper", "enfin"):
                raise self.erreur(f"'{mot}' inattendu : il doit suivre un bloc 'essayer:'")
            if mot == "tantque":
                return self.instr_tantque()
            if mot == "pour":
                return self.instr_pour()
            if mot == "retourner":
                self.avancer()
                valeur = None
                nxt = self.jetons[self.pos]
                if not (nxt.genre in ("nl", "fin_fichier") or (nxt.genre == "op" and nxt.valeur == ";")
                        or (nxt.genre == "motcle" and nxt.valeur in ("fin", "sinon", "attraper", "enfin", "cas"))):
                    valeur = self.expression()
                self.fin_instruction()
                return Retourner(valeur, ligne=j.ligne, colonne=j.colonne)
            if mot == "arreter":
                self.avancer()
                self.fin_instruction()
                return Arreter(ligne=j.ligne, colonne=j.colonne)
            if mot == "continuer":
                self.avancer()
                self.fin_instruction()
                return Continuer(ligne=j.ligne, colonne=j.colonne)
            if mot in ("fin", "sinon"):
                raise self.erreur(f"'{mot}' inattendu : aucun bloc n'est ouvert ici")
            if mot == "dans":
                raise self.erreur("'dans' inattendu")

        expr = self.expression()
        if self.est_op(*AFFECTATIONS_COMPOSEES):
            op = self.avancer()
            if not isinstance(expr, (Identifiant, Index, Membre)):
                raise self.erreur("on ne peut affecter qu'à une variable, un élément de liste ou un champ", op)
            valeur = self.expression()
            self.fin_instruction()
            return Affectation(expr, valeur, op.valeur, ligne=j.ligne, colonne=j.colonne)
        self.fin_instruction()
        return ExprInstr(expr, ligne=j.ligne, colonne=j.colonne)

    def decl_variable(self) -> DeclVariable:
        mot = self.avancer()
        constante = mot.valeur == "constante"
        nom = self.attendre_ident("nom de variable attendu")
        type_annot = None
        if self.est_op(":"):
            self.avancer()
            type_annot = self.type_annot()
        valeur = None
        if self.est_op("="):
            self.avancer()
            valeur = self.expression()
        elif constante:
            raise self.erreur(f"la constante '{nom.valeur}' doit recevoir une valeur avec '='")
        elif type_annot is None:
            raise self.erreur(f"la variable '{nom.valeur}' doit avoir un type (': entier') ou une valeur ('= ...')")
        self.fin_instruction()
        return DeclVariable(nom.valeur, type_annot, valeur, constante, ligne=mot.ligne, colonne=mot.colonne)

    def type_annot(self) -> TypeAnnot:
        if self.est_motcle("fonction"):
            j = self.avancer()
        else:
            j = self.attendre_ident("nom de type attendu")
        params: list[TypeAnnot] = []
        if self.est_op("<"):
            self.avancer()
            params.append(self.type_annot())
            while self.est_op(","):
                self.avancer()
                params.append(self.type_annot())
            self.attendre_op(">")
        return TypeAnnot(j.valeur, params, ligne=j.ligne, colonne=j.colonne)

    def decl_fonction(self) -> DeclFonction:
        mot = self.avancer()
        nom = self.attendre_ident("nom de fonction attendu")
        self.attendre_op("(")
        self.profondeur += 1
        parametres: list[Parametre] = []
        if not self.est_op(")"):
            while True:
                pnom = self.attendre_ident("nom de paramètre attendu")
                self.attendre_op(":", f"':' attendu après le paramètre '{pnom.valeur}' pour indiquer son type")
                ptype = self.type_annot()
                defaut = None
                if self.est_op("="):
                    self.avancer()
                    defaut = self.expression()
                elif parametres and parametres[-1].defaut is not None:
                    raise self.erreur(f"le paramètre '{pnom.valeur}' doit avoir une valeur par défaut car il suit un paramètre qui en a une", pnom)
                parametres.append(Parametre(pnom.valeur, ptype, defaut, ligne=pnom.ligne, colonne=pnom.colonne))
                if self.est_op(","):
                    self.avancer()
                    continue
                break
        self.profondeur -= 1
        self.attendre_op(")")
        if self.est_op("->"):
            self.avancer()
            type_retour = self.type_annot()
        else:
            type_retour = TypeAnnot("rien", ligne=nom.ligne, colonne=nom.colonne)
        corps, multi = self.corps("fin")
        if multi:
            self.attendre_motcle("fin")
        return DeclFonction(nom.valeur, parametres, type_retour, corps, ligne=mot.ligne, colonne=mot.colonne)

    def decl_classe(self) -> DeclClasse:
        mot = self.avancer()
        nom = self.attendre_ident("nom de classe attendu")
        parent = None
        if self.est_motcle("herite"):
            self.avancer()
            parent = self.attendre_ident("nom de la classe parente attendu").valeur
        self.attendre_op(":", f"':' attendu après le nom de la classe '{nom.valeur}'")
        champs: list[Champ] = []
        methodes: list[DeclFonction] = []
        self.sauter_nl()
        while not self.est_motcle("fin"):
            if self.est("fin_fichier"):
                raise self.erreur(f"'fin' attendu pour fermer la classe '{nom.valeur}' (ligne {mot.ligne})")
            if self.est_motcle("fonction"):
                methodes.append(self.decl_fonction())
            elif self.est("ident"):
                cnom = self.avancer()
                self.attendre_op(":", f"':' attendu après le champ '{cnom.valeur}' pour indiquer son type")
                ctype = self.type_annot()
                defaut = None
                if self.est_op("="):
                    self.avancer()
                    defaut = self.expression()
                self.fin_instruction()
                champs.append(Champ(cnom.valeur, ctype, defaut, ligne=cnom.ligne, colonne=cnom.colonne))
            else:
                raise self.erreur(
                    f"dans une classe, seuls des champs ('nom: type') et des méthodes ('fonction ...') sont "
                    f"autorisés, mais {self._decrire(self.courant())} trouvé")
            self.sauter_nl()
        self.attendre_motcle("fin")
        return DeclClasse(nom.valeur, parent, champs, methodes, ligne=mot.ligne, colonne=mot.colonne)

    def instr_si(self) -> Si:
        mot = self.avancer()
        condition = self.expression()
        alors, multi = self.corps("fin", "sinon")
        sinon = None
        if multi:
            if self.est_motcle("sinon"):
                sinon = self._branche_sinon()
            else:
                self.attendre_motcle("fin")
        else:
            # Forme courte : `si (c): instr` éventuellement suivie de `sinon: instr` (même ligne ou ligne suivante)
            sauvegarde = self.pos
            self.sauter_nl()
            if self.est_motcle("sinon"):
                sinon = self._branche_sinon()
            else:
                self.pos = sauvegarde
        return Si(condition, alors, sinon, ligne=mot.ligne, colonne=mot.colonne)

    def _branche_sinon(self) -> "Bloc | Si":
        self.attendre_motcle("sinon")
        if self.est_motcle("si"):
            return self.instr_si()
        bloc, multi = self.corps("fin")
        if multi:
            self.attendre_motcle("fin")
        return bloc

    def instr_importer(self) -> Importer:
        mot = self.avancer()
        if mot.valeur == "depuis":
            # depuis "fichier.nck" importer a, b
            if not self.est("texte"):
                raise self.erreur(f"chemin du fichier attendu entre guillemets après 'depuis', mais {self._decrire(self.courant())} trouvé")
            chemin = self.avancer().valeur
            self.attendre_motcle("importer")
            noms = [self.attendre_ident("nom à importer attendu").valeur]
            while self.est_op(","):
                self.avancer()
                noms.append(self.attendre_ident("nom à importer attendu").valeur)
            self.fin_instruction()
            return Importer(chemin, None, noms, ligne=mot.ligne, colonne=mot.colonne)
        # importer "fichier.nck" [comme alias]
        if not self.est("texte"):
            raise self.erreur(f"chemin du fichier attendu entre guillemets après 'importer' (ex : importer \"maths.nck\"), "
                              f"mais {self._decrire(self.courant())} trouvé")
        chemin = self.avancer().valeur
        alias = None
        if self.est_motcle("comme"):
            self.avancer()
            alias = self.attendre_ident("nom d'alias attendu après 'comme'").valeur
        self.fin_instruction()
        return Importer(chemin, alias, None, ligne=mot.ligne, colonne=mot.colonne)

    def instr_essayer(self) -> Essayer:
        mot = self.avancer()
        self.attendre_op(":", "':' attendu après 'essayer'")
        corps = self.bloc_jusqua("attraper", "enfin", "fin")
        clauses: list[Attraper] = []
        while self.est_motcle("attraper"):
            ja = self.avancer()
            # `attraper e:` ou `attraper TypeErreur e:`
            premier = self.attendre_ident("nom de la variable d'erreur attendu après 'attraper' (ex : attraper e:)")
            type_annot = None
            if self.est("ident"):
                type_annot = TypeAnnot(premier.valeur, ligne=premier.ligne, colonne=premier.colonne)
                var = self.avancer()
            else:
                var = premier
            self.attendre_op(":", f"':' attendu après 'attraper {var.valeur}'")
            bloc = self.bloc_jusqua("attraper", "enfin", "fin")
            clauses.append(Attraper(var.valeur, type_annot, bloc, ligne=ja.ligne, colonne=ja.colonne))
        enfin = None
        if self.est_motcle("enfin"):
            self.avancer()
            self.attendre_op(":", "':' attendu après 'enfin'")
            enfin = self.bloc_jusqua("fin")
        if not clauses and enfin is None:
            raise self.erreur("un bloc 'essayer' doit avoir au moins un 'attraper' ou un 'enfin'", mot)
        self.attendre_motcle("fin")
        return Essayer(corps, clauses, enfin, ligne=mot.ligne, colonne=mot.colonne)

    def instr_selon(self) -> Selon:
        mot = self.avancer()
        sujet = self.expression()
        self.attendre_op(":", "':' attendu après la valeur de 'selon'")
        self.sauter_nl()
        cas: list[Cas] = []
        sinon = None
        while not self.est_motcle("fin"):
            if self.est("fin_fichier"):
                raise self.erreur(f"'fin' attendu pour fermer le 'selon' de la ligne {mot.ligne}")
            if self.est_motcle("cas"):
                jc = self.avancer()
                valeurs = [self.expression()]
                while self.est_op(","):
                    self.avancer()
                    valeurs.append(self.expression())
                bloc, multi = self.corps("cas", "sinon", "fin")
                cas.append(Cas(valeurs, bloc, ligne=jc.ligne, colonne=jc.colonne))
            elif self.est_motcle("sinon"):
                js = self.avancer()
                if sinon is not None:
                    raise self.erreur("un seul 'sinon' est autorisé dans un 'selon'", js)
                sinon, multi = self.corps("cas", "fin")
                if self.est_motcle("cas"):
                    raise self.erreur("'sinon' doit être le dernier cas du 'selon'")
            else:
                raise self.erreur(f"'cas' ou 'sinon' attendu dans le 'selon', mais {self._decrire(self.courant())} trouvé")
            self.sauter_nl()
        self.attendre_motcle("fin")
        if not cas:
            raise self.erreur("un 'selon' doit avoir au moins un 'cas'", mot)
        return Selon(sujet, cas, sinon, ligne=mot.ligne, colonne=mot.colonne)

    def instr_tantque(self) -> TantQue:
        mot = self.avancer()
        condition = self.expression()
        corps, multi = self.corps("fin")
        if multi:
            self.attendre_motcle("fin")
        return TantQue(condition, corps, ligne=mot.ligne, colonne=mot.colonne)

    def instr_pour(self) -> Pour:
        mot = self.avancer()
        var = self.attendre_ident("nom de variable de boucle attendu")
        var2 = None
        if self.est_op(","):
            self.avancer()
            var2 = self.attendre_ident("deuxième nom de variable attendu après ','").valeur
        self.attendre_motcle("dans")
        iterable = self.expression()
        corps, multi = self.corps("fin")
        if multi:
            self.attendre_motcle("fin")
        return Pour(var.valeur, iterable, corps, var2, ligne=mot.ligne, colonne=mot.colonne)

    # ----- expressions (par précédence croissante) -----

    def expression(self) -> Expr:
        return self.expr_ou()

    def expr_ou(self) -> Expr:
        g = self.expr_et()
        while self.est_motcle("ou"):
            j = self.avancer()
            d = self.expr_et()
            g = Logique("ou", g, d, ligne=j.ligne, colonne=j.colonne)
        return g

    def expr_et(self) -> Expr:
        g = self.expr_non()
        while self.est_motcle("et"):
            j = self.avancer()
            d = self.expr_non()
            g = Logique("et", g, d, ligne=j.ligne, colonne=j.colonne)
        return g

    def expr_non(self) -> Expr:
        if self.est_motcle("non"):
            j = self.avancer()
            return Unaire("non", self.expr_non(), ligne=j.ligne, colonne=j.colonne)
        return self.expr_comparaison()

    def expr_comparaison(self) -> Expr:
        g = self.expr_additive()
        while self.est_op("==", "!=", "<", ">", "<=", ">="):
            j = self.avancer()
            d = self.expr_additive()
            g = Binaire(j.valeur, g, d, ligne=j.ligne, colonne=j.colonne)
        return g

    def expr_additive(self) -> Expr:
        g = self.expr_multiplicative()
        while self.est_op("+", "-"):
            j = self.avancer()
            d = self.expr_multiplicative()
            g = Binaire(j.valeur, g, d, ligne=j.ligne, colonne=j.colonne)
        return g

    def expr_multiplicative(self) -> Expr:
        g = self.expr_unaire()
        while self.est_op("*", "/", "%"):
            j = self.avancer()
            d = self.expr_unaire()
            g = Binaire(j.valeur, g, d, ligne=j.ligne, colonne=j.colonne)
        return g

    def expr_unaire(self) -> Expr:
        if self.est_op("-"):
            j = self.avancer()
            return Unaire("-", self.expr_unaire(), ligne=j.ligne, colonne=j.colonne)
        if self.est_op("+"):
            self.avancer()
            return self.expr_unaire()
        return self.expr_postfixe()

    def expr_postfixe(self) -> Expr:
        e = self.expr_primaire()
        while True:
            if self.est_op("("):
                j = self.avancer()
                self.profondeur += 1
                args: list[Expr] = []
                nommes: list[tuple[str, Expr]] = []
                if not self.est_op(")"):
                    while True:
                        self._argument(args, nommes)
                        if self.est_op(","):
                            self.avancer()
                            if self.est_op(")"):
                                break
                            continue
                        break
                self.profondeur -= 1
                self.attendre_op(")", "')' attendu pour fermer l'appel")
                e = Appel(e, args, nommes, ligne=j.ligne, colonne=j.colonne)
            elif self.est_op("."):
                self.avancer()
                nom = self.attendre_ident("nom de champ ou de méthode attendu après '.'")
                e = Membre(e, nom.valeur, ligne=nom.ligne, colonne=nom.colonne)
            elif self.est_op("["):
                j = self.avancer()
                self.profondeur += 1
                idx = self.expression()
                self.profondeur -= 1
                self.attendre_op("]", "']' attendu")
                e = Index(e, idx, ligne=j.ligne, colonne=j.colonne)
            else:
                return e

    def _argument(self, args: list[Expr], nommes: list[tuple[str, Expr]]) -> None:
        j = self.courant()
        suivant = self.jetons[self.pos + 1] if self.pos + 1 < len(self.jetons) else None
        if j.genre == "ident" and suivant is not None and suivant.genre == "op" and suivant.valeur == "=":
            self.avancer()
            self.avancer()
            nommes.append((j.valeur, self.expression()))
            return
        if nommes:
            raise self.erreur("un argument positionnel ne peut pas suivre un argument nommé", j)
        args.append(self.expression())

    def expr_primaire(self) -> Expr:
        j = self.courant()
        if j.genre == "nombre":
            self.avancer()
            return Litteral(j.valeur, ligne=j.ligne, colonne=j.colonne)
        if j.genre == "texte":
            self.avancer()
            return Litteral(j.valeur, ligne=j.ligne, colonne=j.colonne)
        if j.genre == "ftexte":
            self.avancer()
            parties: list = []
            for partie in j.valeur:
                if isinstance(partie, str):
                    parties.append(partie)
                    continue
                code, lc, cc = partie
                jetons = lexer(code, self.fichier)
                for jt in jetons:
                    jt.ligne = lc
                    jt.colonne += cc - 1
                sous = Parseur(jetons, self.fichier)
                sous.profondeur = 1
                expr = sous.expression()
                if not sous.est("fin_fichier"):
                    raise sous.erreur(f"fin de l'expression attendue dans le texte formaté, mais {self._decrire(sous.courant())} trouvé")
                parties.append(expr)
            return TexteFormate(parties, ligne=j.ligne, colonne=j.colonne)
        if j.genre == "motcle":
            if j.valeur == "vrai":
                self.avancer()
                return Litteral(True, ligne=j.ligne, colonne=j.colonne)
            if j.valeur == "faux":
                self.avancer()
                return Litteral(False, ligne=j.ligne, colonne=j.colonne)
            if j.valeur == "nul":
                self.avancer()
                return Litteral(None, ligne=j.ligne, colonne=j.colonne)
            raise self.erreur(f"le mot-clé '{j.valeur}' ne peut pas être utilisé ici")
        if j.genre == "ident":
            self.avancer()
            return Identifiant(j.valeur, ligne=j.ligne, colonne=j.colonne)
        if j.genre == "op" and j.valeur == "(":
            self.avancer()
            self.profondeur += 1
            e = self.expression()
            self.profondeur -= 1
            self.attendre_op(")", "')' attendu")
            return e
        if j.genre == "op" and j.valeur == "[":
            self.avancer()
            self.profondeur += 1
            elements: list[Expr] = []
            if not self.est_op("]"):
                elements.append(self.expression())
                while self.est_op(","):
                    self.avancer()
                    if self.est_op("]"):
                        break
                    elements.append(self.expression())
            self.profondeur -= 1
            self.attendre_op("]", "']' attendu pour fermer la liste")
            return ListeLit(elements, ligne=j.ligne, colonne=j.colonne)
        if j.genre == "op" and j.valeur == "{":
            self.avancer()
            self.profondeur += 1
            entrees: list[tuple[Expr, Expr]] = []
            if not self.est_op("}"):
                while True:
                    cle = self.expression()
                    self.attendre_op(":", "':' attendu entre la clé et la valeur du dictionnaire")
                    entrees.append((cle, self.expression()))
                    if self.est_op(","):
                        self.avancer()
                        if self.est_op("}"):
                            break
                        continue
                    break
            self.profondeur -= 1
            self.attendre_op("}", "'}' attendu pour fermer le dictionnaire")
            return DicoLit(entrees, ligne=j.ligne, colonne=j.colonne)
        raise self.erreur(f"expression attendue, mais {self._decrire(j)} trouvé")


def parser(source: str, fichier: str = "<entrée>") -> Programme:
    return Parseur(lexer(source, fichier), fichier).programme()
