# Venir de Python ou JavaScript

Si vous connaissez déjà un langage, cette table vous donne les équivalences en un coup d'œil.

| Notion | Python | JavaScript / TypeScript | NCK |
|---|---|---|---|
| Afficher | `print(x)` | `console.log(x)` | `ecrire(x)` |
| Lire au clavier | `input("? ")` | — | `lire("? ")` |
| Variable | `x = 1` | `let x = 1` | `variable x = 1` |
| Variable typée | `x: int = 1` | `let x: number = 1` | `variable x: entier = 1` |
| Constante | — | `const PI = 3.14` | `constante PI = 3.14` |
| Commentaire | `# …` | `// …` | `// …` ou `# …` |
| Texte formaté | `f"{a} et {b}"` | `` `${a} et ${b}` `` | `f"{a} et {b}"` |
| Condition | `if a: … elif b: … else: …` | `if (a) {…} else if (b) {…} else {…}` | `si a: … sinon si b: … sinon: … fin` |
| Expression conditionnelle | `x if c else y` | `c ? x : y` | `si c alors x sinon y` |
| Boucle sur liste | `for x in l:` | `for (const x of l)` | `pour x dans l: … fin` |
| Avec indice | `for i, x in enumerate(l):` | `l.forEach((x, i) => …)` | `pour i, x dans l: … fin` |
| Intervalle | `range(1, 10)` | — | `1..10` ou `intervalle(1, 10)` |
| Tant que | `while c:` | `while (c) {…}` | `tantque c: … fin` |
| Sortir / continuer | `break` / `continue` | `break` / `continue` | `arreter` / `continuer` |
| Fonction | `def f(a: int) -> int:` | `function f(a: number): number` | `fonction f(a: entier) -> entier:` |
| Lambda | `lambda x: x * 2` | `x => x * 2` | `fonction(x): x * 2` |
| Liste | `[1, 2]` / `list[int]` | `[1, 2]` / `number[]` | `[1, 2]` / `liste<entier>` |
| Ajouter | `l.append(x)` | `l.push(x)` | `l.ajouter(x)` |
| Longueur | `len(l)` | `l.length` | `l.longueur()` ou `longueur(l)` |
| map / filter / reduce | `map`, `filter`, `functools.reduce` | `.map`, `.filter`, `.reduce` | `.appliquer`, `.filtrer`, `.reduire` |
| Dictionnaire | `{"a": 1}` / `dict[str, int]` | `{a: 1}` / `Record<string, number>` | `{"a": 1}` / `dico<texte, entier>` |
| Clé absente | `d.get("a", 0)` | `d["a"] ?? 0` | `d.obtenir("a", 0)` ou `d.obtenir("a") ?? 0` |
| Valeur nulle | `None` / `Optional[str]` | `null` / `string \| null` | `nul` / `texte?` |
| Repli si nul | `x or y` | `x ?? y` | `x ?? y` |
| Classe | `class P:` + `__init__` | `class P { constructor() }` | `classe P:` (constructeur automatique) |
| Champs | dataclass / Pydantic | propriétés | `nom: texte`, `age: entier = 0` |
| this | `self` | `this` | `soi` |
| Héritage | `class A(B):` | `class A extends B` | `classe A herite B:` |
| super | `super().m()` | `super.m()` | `parent.m()` |
| Méthode statique | `@staticmethod` | `static m()` | `statique fonction m()` |
| Test de type | `isinstance(x, P)` | `x instanceof P` | `est_un(x, P)` |
| Exceptions | `try / except E as e / finally` | `try / catch (e) / finally` | `essayer / attraper E e / enfin / fin` |
| Lever | `raise ValueError("m")` | `throw new Error("m")` | `lever "m"` ou `lever MonErreur("m")` |
| Import | `import m` / `from m import f` | `import { f } from "./m"` | `importer "m.nck"` / `depuis "m.nck" importer f` |
| Énumération | `class C(Enum):` | `enum C {}` | `enumeration C: A, B fin` |
| switch | `match x:` | `switch (x) {}` | `selon x: cas 1: … sinon: … fin` |
| Vérité | `0`, `""`, `[]` sont faux | idem + coercition | **seuls** `vrai` / `faux` sont des booléens |
| Égalité | `1 == 1.0` vrai | `1 == "1"` vrai | `1 == 1.0` vrai, `vrai == 1` faux, pas de coercition |
| Division | `7 / 2 = 3.5`, `7 // 2 = 3` | `7 / 2 = 3.5` | `7 / 2 = 3.5`, `division_entiere(7, 2) = 3` |

## Différences importantes

!!! warning "Pas de vérité implicite"
    `si liste:` est une erreur de type. Écrivez `si liste.longueur() > 0:`.

!!! warning "Les blocs se terminent par `fin`"
    L'indentation est recommandée mais ce n'est pas elle qui délimite les blocs. Un bloc d'une seule instruction
    peut tenir sur la ligne : `si x > 0: ecrire("positif")` (sans `fin`).

!!! info "Typage statique"
    Une variable garde son type toute sa vie. `variable x = 1` puis `x = "un"` est refusé **avant** l'exécution.
    `quelconque` existe pour les cas dynamiques (JSON, par exemple), mais son usage est contrôlé.
