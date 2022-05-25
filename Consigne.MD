### Function :

On veut une liste de fonction différente dans un même programme

f1(X, Y){ ... return}

f2(X, Z){ ... return}

Pour l'instant, on a globalement :

main(X,Y){ ... return}

En terme de grammaire :

Exp ::= f_identifier(Exp*)

De plus, il faudrait implémenter un instruction fct_list à la manière de var_list du programme python déjà écrit

Enfin, le programme principale devrait contenir une fonction fct_main de sorte à ce qu'on ait toujours : prog(fct_main)

L'arbre aurait ainsi un noeud à trois fils : Funct , Nom et Arguments

Pour le compilateur on utilisera uniquement la convention 32 bits (on met tout dans la pile)

### String :

Un string est bien evidemment de la forme X = "abcd"

On veut pouvoir implémenter l'égalité des char : X == "a"

On veut pouvoir trouver la taille d'une chaine de caractère len(X) qui renvoit l'entier correspondant au code ASCII

Z = X.charAt(3), Z est alors un entier 

X.setCharAt(4,Z) on a alors X un string, 4 la position du charactère à remplacer, Z un entier qui correspond au code ASCII de la lettre à placer

On veut pouvoir effectuer : X + Y
-> où X et Y sont deux string
-> où l'un est un string et l'autre non

### Typage C :

Tout doit être typé, exemple : int f(int X, int Z){...}

On peut avoir plusieurs types : int x ou string p

L'idée n'est pas pas de modifier le code final, juste de mettre des contraintes lors du build

Par exemple : "abc" + 3 => impossible ou encore 3.charAt(4) => impossible
