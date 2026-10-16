# Mots réservés et grammaire

## Mots réservés

Ces mots ne peuvent pas servir de nom de variable, de fonction ou de classe :

```text
variable  constante  fonction  classe  enumeration  herite  statique  abstraite
si  sinon  alors  selon  cas  tantque  pour  dans  fin  arreter  continuer  retourner
essayer  attraper  enfin  lever  importer  depuis  comme
et  ou  non  vrai  faux  nul
```

`soi` et `parent` sont définis automatiquement dans les méthodes. Les noms de types (`entier`, `reel`, `texte`,
`booleen`, `liste`, `dico`, `rien`, `quelconque`, `fonction`) et des fonctions natives (`ecrire`, `longueur`…)
peuvent être masqués par une variable locale, mais c'est déconseillé.

## Structure lexicale

| Élément | Forme |
|---|---|
| Commentaire | `// …` ou `# …` jusqu'à la fin de la ligne |
| Entier | `0`, `42`, `1000000` |
| Réel | `3.14`, `0.5` (point décimal) |
| Texte | `"…"`, `'…'`, `f"…{expr}…"`, `"""…"""` |
| Identifiant | lettre ou `_`, puis lettres, chiffres, `_` (pas d'accent) |
| Fin d'instruction | fin de ligne ou `;` |
| Bloc | `:` puis une instruction sur la ligne, **ou** plusieurs lignes terminées par `fin` |

## Grammaire (EBNF simplifiée)

```ebnf
programme      = { instruction } ;

instruction    = declaration | affectation | "constante" ident "=" expr
               | fonction | classe | enumeration | importation
               | si | selon | tantque | pour | essayer
               | "retourner" [ expr { "," expr } ] | "lever" expr
               | "arreter" | "continuer" | expr ;

declaration    = "variable" ident [ ":" type ] [ "=" expr ]
               | "variable" ident { "," ident } "=" expr { "," expr } ;
affectation    = cible ( "=" | "+=" | "-=" | "*=" | "/=" ) expr
               | cible { "," cible } "=" expr { "," expr } ;
cible          = ident | expr "[" expr "]" | expr "." ident ;

fonction       = [ "@" ident ] [ "statique" | "abstraite" ]
                 "fonction" ident "(" [ params ] ")" [ "->" type ] ( bloc | ) ;
params         = param { "," param } [ "," "..." ident [ ":" type ] ] ;
param          = ident ":" type [ "=" expr ] ;
fonction_anon  = "fonction" "(" [ params ] ")" [ "->" type ] ":" ( expr | instruction | lignes "fin" ) ;

classe         = "classe" ident [ "herite" ident ] ":" { champ | fonction | "constante" ident "=" expr } "fin" ;
champ          = ident ":" type [ "=" expr ] ;
enumeration    = "enumeration" ident ":" ident { [","] ident } "fin" ;

importation    = "importer" texte [ "comme" ident ]
               | "depuis" texte "importer" ident { "," ident } ;

si             = "si" expr bloc { "sinon" "si" expr bloc } [ "sinon" bloc ] [ "fin" ] ;
selon          = "selon" expr ":" { "cas" expr { "," expr } bloc } [ "sinon" bloc ] "fin" ;
tantque        = "tantque" expr bloc ;
pour           = "pour" ident [ "," ident ] "dans" expr bloc ;
essayer        = "essayer" ":" lignes { "attraper" [ ident ] ident ":" lignes } [ "enfin" ":" lignes ] "fin" ;

bloc           = ":" instruction            (* forme courte *)
               | ":" lignes "fin" ;         (* forme longue *)

type           = "entier" | "reel" | "texte" | "booleen" | "rien" | "quelconque"
               | "liste" "<" type ">" | "dico" "<" type "," type ">"
               | "fonction" "<" [ type { "," type } ] ">" | ident
               | type "?" ;

expr           = repli ;
repli          = ou { "??" ou } ;
ou             = et { "ou" et } ;
et             = non { "et" non } ;
non            = "non" non | comparaison ;
comparaison    = plage [ ( "==" | "!=" | "<" | ">" | "<=" | ">=" ) plage ] ;
plage          = somme [ ".." somme ] ;
somme          = produit { ( "+" | "-" ) produit } ;
produit        = unaire { ( "*" | "/" | "%" ) unaire } ;
unaire         = "-" unaire | postfixe ;
postfixe       = primaire { "(" [ args ] ")" | "[" expr "]" | "." ident } ;
primaire       = nombre | texte | "vrai" | "faux" | "nul" | ident
               | "[" [ expr { "," expr } ] "]" | "{" [ expr ":" expr { "," expr ":" expr } ] "}"
               | "(" expr ")" | fonction_anon
               | "si" expr "alors" expr "sinon" expr ;
args           = arg { "," arg } ;
arg            = expr | ident "=" expr | "..." expr ;
```

Cette grammaire est indicative ; le parseur de référence est `nck/parseur.py`.
