import lark
import sys

grammaire = lark.Lark("""
variables : "(" var (","  var)* ")" | "(" ")"
expr : IDENTIFIANT -> variable | NUMBER -> nombre
| expr OP expr -> binexpr | "(" expr ")" -> parenexpr
| "!" expr -> not
cmd : shortcmd ";" -> short |"while" "(" expr ")" "{" bloc "}" -> while
    | "if" "(" expr ")" "{" bloc "}" -> if | "printf" "(" expr ")" ";"-> printf
    | "if" "(" expr ")" "{" bloc "}" "else" "{" bloc "}" -> ifelse
    | "for" "(" shortcmd ";" expr ";" shortcmd ")" "{" bloc "}" -> for
    | COMMENT -> comment
shortcmd : var "=" expr -> declaration | var -> shortdeclaration
    | IDENTIFIANT "=" expr -> assignment | IDENTIFIANT "+=" expr -> add | IDENTIFIANT "-=" expr -> sub
    | IDENTIFIANT "++" -> incr | IDENTIFIANT "--" -> decr
bloc : (cmd)*
func : RETURNTYPE NOM variables "{" bloc "return" "(" expr ")" ";" "}"
prog : (func | COMMENT)* func
var : TYPE IDENTIFIANT
COMMENT : "//" LINE | "/*" MULTILINE "*/"
NUMBER : /[0-9]+/
OP : /[+\*\/><-]/ | /[!<>=](=)/ | "**" | "&&" | "||"
IDENTIFIANT : /[a-zA-Z][a-zA-Z0-9]*/
TYPE : "int" | "string"
RETURNTYPE : TYPE | "void"
LINE : /.*/
MULTILINE : /[^\*]*((\*)+[^\/\*][^\*]*)*/s
NOM : /[a-zA-Z0-9\_]+/
%import common.WS
%ignore WS
""", start = "prog")

cpt = iter(range(10000))
intop2asm = {'+': "add", '-': "sub", '*': "imul", '/' : "idiv"}
cmpop2asm = {"==" : "je","!=" : "jne", '>' : "jg", '<' : "jl", ">=" : "jge", "<=" : "jle"}

def pp_variables(vars):
    return ", ".join([f"{t.children[0].value} {t.children[1].value}" for t in vars.children])

def pp_expr(expr):
    if expr.data in {"variable", "nombre"}:
        return expr.children[0].value
    elif expr.data == "binexpr" :
        e1 = pp_expr(expr.children[0])
        e2 = pp_expr(expr.children[2])
        op = expr.children[1].value
        return f"{e1} {op} {e2}"
    elif expr.data == "parenexpr":
        return f"({ pp_expr( expr.children[0] ) }) "
    else :
        raise Exception("Not implemented")

def pp_short(cmd):
    if cmd.data == "assignment" :
        lhs = cmd.children[0].value
        rhs = pp_expr(cmd.children[1])
        return f"{lhs} = {rhs}"
    elif cmd.data == "declaration" :
        lhs = f"{cmd.children[0].children[0].value} {cmd.children[0].children[1].value}"
        rhs = pp_expr(cmd.children[1])
        return f"{lhs} = {rhs}"
    elif cmd.data == "shortdeclaration" :
        lhs = f"{cmd.children[0].children[0].value} {cmd.children[0].children[1].value}"
        return f"{lhs}"
    elif cmd.data == "add" :
        lhs = cmd.children[0].value
        rhs = pp_expr(cmd.children[1])
        return f"{lhs} += {rhs}"
    elif cmd.data == "sub" :
        lhs = cmd.children[0].value
        rhs = pp_expr(cmd.children[1])
        return f"{lhs} += {rhs}"
    elif cmd.data == "incr" :
        lhs = cmd.children[0].value
        return f"{lhs}++"
    elif cmd.data == "decr" :
        lhs = cmd.children[0].value
        return f"{lhs}--"
    else :
        raise Exception("Not implemented")

def pp_cmd(cmd):
    if cmd.data == "short" :
        e = pp_short(cmd.children[0])
        return f"{e};"
    elif cmd.data == "printf" :
        return f"printf({pp_expr(cmd.children[0])});"
    elif cmd.data in {"while", "if"} :
        e = pp_expr(cmd.children[0])
        b = pp_bloc(cmd.children[1])
        return f"{cmd.data}({e}){{\n{b}\n}}"
    elif cmd.data == "ifelse" :
        e = pp_expr(cmd.children[0])
        b1 = pp_bloc(cmd.children[1])
        b2 = pp_bloc(cmd.children[2])
        return f"if({e}){{\n{b1}\n}}else{{\n{b2}\n}}"
    elif cmd.data == "for" :
        c1 = pp_short(cmd.children[0])
        e = pp_expr(cmd.children[1])
        c2 = pp_short(cmd.children[2])
        bloc = pp_bloc(cmd.children[3])
        return f"for({c1};{e};{c2}){{\n{bloc}\n}}"
    elif cmd.data == "comment":
        return ""
    else :
        raise Exception("Not implemented")


def pp_bloc(bloc):
    b = "\n".join([pp_cmd(t) for t in bloc.children]).split("\n")
    a = []
    for i in range(len(b)):
        if len(b[i]) > 0:
            a+= ["    " + b[i]]
    return "\n".join(a)

def pp_func(func):
    type = func.children[0]
    name = func.children[1]
    vars = pp_variables(func.children[2])
    bloc = pp_bloc(func.children[3])
    ret = pp_expr(func.children[4])
    return f"{type} {name} ({vars}){{\n{bloc}\n    return({ret}); \n}} "

def pp_prog(prog):
    s = ""
    for func in prog.children:
        if not isinstance(func, lark.Token):
            if func.data == "func":
                s += f"{pp_func(func)}\n\n"
            else:
                raise Exception("Not implemented")
    return s

def var_list(ast):
    if isinstance(ast, lark.Token):
        return set()
    elif ast.data == "var":
            return {ast}

    s = set()
    for c in ast.children:
        s.update(var_list(c))
    return s

def type_expr(expr, typelist):
    if expr.data == "variable":
        e = expr.children[0].value
        if e in typelist.keys():
            return typelist[e]
        else:
            raise Exception(f"{e} not declared")
    elif expr.data == "nombre":
        return "int"
    elif expr.data == "binexpr":
        e1 = type_expr(expr.children[0], typelist)
        e2 = type_expr(expr.children[2], typelist)
        if e1 != e2:
            raise Exception("Type error")
        else:
            return e1
    elif expr.data in {"parenexpr", "not"}:
        return type_expr(expr.children[0], typelist)
    else:
        raise Exception("Not implemented")

def compile_expr(expr, typelist):
    if expr.data == "variable":
        return f"  mov rax, [{expr.children[0].value}]"
    elif expr.data == "nombre":
        return f"  mov rax, {expr.children[0].value}"
    elif expr.data == "binexpr":
        t1 = type_expr(expr.children[0], typelist)
        t2 = type_expr(expr.children[2], typelist)
        if t1 != t2:
            raise Exception("Type error")
        else:
            if t1 == "int":
                e1 = compile_expr(expr.children[0], typelist)
                e2 = compile_expr(expr.children[2], typelist)
                op = expr.children[1].value
                index = cpt.__next__()
                if op == '/':
                    return f"  mov rdx, 0\n{e2}\npush rax\n{e1}\n  pop rbx\n  {intop2asm[op]} qword rbx"
                elif op == "**":
                    return f"{e1}\n  push rax\n{e2}\n  mov rbx, rax\n  pop rcx\n  mov rdx, 0\n  mov rax, 1\nbegin{index}:\n  cmp rbx, 0\n  je end{index}\n  jl mid{index}\n  imul rax, rcx\n  sub rbx, 1\n  jmp begin{index}\nmid{index}:\n  idiv rcx\n  add rbx, 1\n  jmp begin{index}\nend{index}:"
                elif op in {'+','-','*','/'}:
                    return f"{e2}\n  push rax\n{e1}\n  pop rbx\n  {intop2asm[op]} rax, rbx"
                elif op in {"==", "!=", '<', '>', "<=", ">="}:
                    return f"{e2}\n  push rax\n{e1}\n  pop rbx\n  cmp rax, rbx\n  {cmpop2asm[op]} mid{index}\n  mov rax, 0\n  jmp end{index}\nmid{index}:\n  mov rax, 1\nend{index}:"
                elif op == "&&":
                    return f"{e2}\n  push rax\n{e1}\n  pop rbx\n  imul rax, rbx"
                elif op == "||":
                    return f"{e1}\n  cmp rax, 0\n  jne mid{index}\n{e2}\n  cmp rax, 0\n  jne mid{index}\n  mov rax, 0\n  jmp end{index}\nmid{index}:\n  mov rax, 1\n  end{index}:"
                else:
                    raise Exception("Not implemented")
            else:
                raise Exception("Not implemented")
    elif expr.data == "parenexpr":
        return compile_expr(expr.children[0], typelist)
    elif expr.data =="not":
        e = compile_expr(expr.children[0], typelist)
        index = cpt.__next__()
        return f"{e}\n  cmp rax, 0\n  je mid{index}\n  mov rax, 0\n  jmp end{index}\nmid{index}:\n  mov rax, 1\nend{index}:"
    else:
        raise Exception("Not implemented")

def compile_short(cmd, typelist):
    if cmd.data == "assignment":
        lhs = cmd.children[0].value
        if typelist[lhs] == type_expr(cmd.children[1], typelist):
            rhs = compile_expr(cmd.children[1], typelist)
            return f"{rhs}\n  mov [{lhs}], rax"
        else:
            raise Exception("Type error")
    elif cmd.data == "declaration":
        lhs = cmd.children[0].children[1].value
        if typelist[lhs] == type_expr(cmd.children[1], typelist):
            rhs = compile_expr(cmd.children[1], typelist)
            return f"{rhs}\n  mov [{lhs}], rax"
        else:
            raise Exception("Type error")
    elif cmd.data == "shortdeclaration":
        lhs = cmd.children[0].children[1].value
        if typelist[lhs] == "int":
            return f"  mov [{lhs}], dword ptr 0"
        else:
            raise Exception("Not implemented")
    elif cmd.data == "add":
        lhs = cmd.children[0].value
        if typelist[lhs] == type_expr(cmd.children[1], typelist):
            if typelist[lhs] == "int":
                rhs = compile_expr(cmd.children[1], typelist)
                return f"  mov rbx, [{lhs}]\n{rhs}\n  add rbx, rax\n  mov [{lhs}], rbx"
            else:
                raise Exception("Not implemented")
        else:
            raise Exception("Type error")
    elif cmd.data == "sub":
        lhs = cmd.children[0].value
        if typelist[lhs] == type_expr(cmd.children[1], typelist):
            if typelist[lhs] == "int":
                rhs = compile_expr(cmd.children[1], typelist)
                return f"  mov rbx, [{lhs}]\n{rhs}\n  sub rbx, rax\n  mov [{lhs}], rbx"
            else:
                raise Exception("Not implemented")
        else: 
            raise Exception("Type error")
    elif cmd.data == "incr":
        lhs = cmd.children[0].value
        if typelist[lhs] == "int":
            return f"  mov rax, [{lhs}]\n  add rax, 1\n  mov [{lhs}], rax"
        else:
            raise Exception("Not implemented")
    elif cmd.data == "decr":
        lhs = cmd.children[0].value
        if typelist[lhs] == "int":
            return f"  mov rax, [{lhs}]\n  sub rax, 1\n  mov [{lhs}], rax"
        else:
            raise Exception("Not implemented")
    else:
        raise Exception("Not implemented")

def compile_cmd(cmd, typelist):
    if cmd.data == "short":
        return compile_short(cmd.children[0], typelist)
    if cmd.data in {"while", "if", "ifelse"}:
        if type_expr(cmd.children[0], typelist) == "int":
            if cmd.data == "while":
                e = compile_expr(cmd.children[0], typelist)
                b = compile_bloc(cmd.children[1], typelist)
                index = cpt.__next__()
                return f"begin{index}:\n{e}\n  cmp rax, 0\n  jz end{index}\n{b}\n  jmp begin{index}\nend{index}:"
            elif cmd.data == "if":
                e = compile_expr(cmd.children[0], typelist)
                b = compile_bloc(cmd.children[1], typelist)
                index = cpt.__next__()
                return f"{e}\n  cmp rax, 0\n  jz end{index}\n{b}\nend{index}:"
            elif cmd.data == "ifelse":
                e = compile_expr(cmd.children[0], typelist)
                b1 = compile_bloc(cmd.children[1], typelist)
                b2 = compile_bloc(cmd.children[2], typelist)
                index = cpt.__next__()
                return f"{e}\n  cmp rax, 0\n  jz mid{index}\n{b1}\n  jmp end{index}\nmid{index}:\n{b2}\nend{index}:"
        else:
            raise Exception("Type error")
    elif cmd.data == "for":
        if type_expr(cmd.children[1], typelist) == "int":
            c1 = compile_short(cmd.children[0], typelist)
            e = compile_expr(cmd.children[1], typelist)
            c2 = compile_short(cmd.children[2], typelist)
            b = compile_bloc(cmd.children[3], typelist)
            index = cpt.__next__()
            return f"{c1}\nbegin{index}:\n{e}\n  cmp rax,0\n  je end{index}\n{b}\n{c2}\n  jmp begin{index}\nend{index}:"
        else:
            raise Exception("Type error")
    elif cmd.data == "comment":
        return ""
    elif cmd.data == "printf":
        return f"{compile_expr(cmd.children[0], typelist)}\n  mov rdi, fmt\n  mov rsi, rax\n  xor rax, rax\n  call printf"
    else:
        raise Exception("Not implemented")

def compile_bloc(bloc, typelist):
    b = [compile_cmd(t, typelist) for t in bloc.children]
    a = []
    for l in b:
        if len(l) > 0:
            a += [l] 
    return "\n".join(a)

def compile_vars(ast):
    s = ""
    for i in range(len(ast.children)):
        s+= f"  mov rbx, [rbp-0x10]\n  mov rdi, [rbx+{8*(i+1)}]\n  call atoi\n  mov [{ast.children[i].children[1].value}], rax\n"
    return s

def type_list(varlist):
    dico = {}
    for e in varlist:
        dico[e.children[1].value] = e.children[0].value
    return dico

def compile(prg):
    with open("moule.asm") as f:
        main = prg.children[len(prg.children) - 1]
        code = f.read()
        varlist = var_list(main)
        typelist = type_list(varlist)
        var_decl =  "\n".join([f"{x.children[1]}: dq 0" for x in varlist])
        code = code.replace("VAR_DECL", var_decl)
        code = code.replace("RETURN", compile_expr(main.children[4], typelist))
        code = code.replace("BODY", compile_bloc(main.children[3], typelist))
        code = code.replace("VAR_INIT", compile_vars(main.children[2]))
        return code

mode = sys.argv[1]
filename = sys.argv[2]
code = open(filename).read()
prg = grammaire.parse(code)

if mode == "pp":
    print(pp_prog(prg))
elif mode == "cp":
    print(compile(prg))
else:
    raise Exception("Not implemented")

#python3.9 compilo.py cp test.nanoc > hum.asm
#nasm -felf64 hum.asm
#gcc -no-pie -fno-pie hum.o
