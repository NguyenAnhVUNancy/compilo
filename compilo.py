import lark

grammaire = lark.Lark("""
variables : IDENTIFIANT (","  IDENTIFIANT)*
expr : IDENTIFIANT -> variable | NUMBER -> nombre
| expr OP expr -> binexpr | "(" expr ")" -> parenexpr
cmd : IDENTIFIANT "=" expr ";"-> assignment|"while" "(" expr ")" "{" bloc "}" -> while
    | "if" "(" expr ")" "{" bloc "}" -> if | "printf" "(" expr ")" ";"-> printf
    | "if" "(" expr ")" "{" bloc "}" "else" "{" bloc "}" -> ifelse
    | COMMENT -> comment
bloc : (cmd)*
prog : "main" "(" variables ")" "{" bloc "return" "(" expr ")" ";" "}"
COMMENT : "//" LINE | "/*" MULTILINE "*/"
NUMBER : /[0-9]+/
OP : /[+\*\/>-]/
IDENTIFIANT : /[a-zA-Z][a-zA-Z0-9]*/
LINE : /.*/
MULTILINE : /[^\*]*((\*)[^\/][^\*]*)*/s
%import common.WS
%ignore WS
""", start = "prog")

cpt = iter(range(10000))
intop2asm = {'+': "add", '-': "sub", '*': "imul", '>' : "cmp", '/' : "idiv"}

def pp_variables(vars):
    return ", ".join([t.value for t in vars.children])

def pp_expr(expr):
    if expr.data in {"variable", "nombre"}:
        return expr.children[0].value
    elif expr.data == "binexpr" :
        e1 = pp_expr(expr.children[0])
        e2 = pp_expr(expr.children[2])
        op = expr.children[1].value
        return f"{e1} {op} {e2}"
    elif expr.data == "parenexpr":
        f"({ pp_expr( expr.children[0] ) }) "
    else :
        raise Exception("Not implemented")

def pp_cmd(cmd):
    if cmd.data == "assignment" :
        lhs = cmd.children[0].value
        rhs = pp_expr(cmd.children[1])
        return f"{lhs} = {rhs};"
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

def pp_prog(prog):
    vars = pp_variables(prog.children[0])
    bloc = pp_bloc(prog.children[1])
    ret = pp_expr(prog.children[2])
    return f"main ({vars}){{\n{bloc}\n    return({ret}); \n}} "


def var_list(ast):
    if isinstance(ast, lark.Token):
        if ast.type == "IDENTIFIANT":
            return {ast.value}
        else:
            return set()
    s = set()
    for c in ast.children:
        s.update(var_list(c))
    return s

def compile_expr(expr):
    if expr.data in "variable":
        return f"mov rax, [{expr.children[0].value}]"
    elif expr.data in "nombre":
        return f"mov rax, {expr.children[0].value}"
    elif expr.data == "binexpr":
        e1 = compile_expr(expr.children[0])
        e2 = compile_expr(expr.children[2])
        op = expr.children[1].value
        if op == '/':
            return f"\nmov rdx, 0\n{e2}\npush rax\n{e1}\npop rbx\n{intop2asm[op]} qword rbx\n"
        else:
            return f"\n{e2}\npush rax\n{e1}\npop rbx\n{intop2asm[op]} rax,rbx"
    elif expr.data == "parenexpr":
        return compile_expr(expr.children[0])
    else:
        raise Exception("Not implemented")

def compile_cmd(cmd):
    if cmd.data == "assignment":
        lhs = cmd.children[0].value
        rhs = compile_expr(cmd.children[1])
        return f"{rhs}\nmov [{lhs}], rax"
    elif cmd.data == "while":
        e = compile_expr(cmd.children[0])
        b = compile_bloc(cmd.children[1])
        index = cpt.__next__()
        return f"debut{index}:\n{e}\ncmp rax,0\njz fin{index}\n{b}\njmp debut{index}\nfin{index}:\n"
    elif cmd.data == "if":
        e = compile_expr(cmd.children[0])
        b = compile_bloc(cmd.children[1])
        index = cpt.__next__()
        return f"\n{e}\ncmp rax,0\njz fin{index}\n{b}\nfin{index}:\n"
    elif cmd.data == "ifelse":
        e = compile_expr(cmd.children[0])
        b1 = compile_bloc(cmd.children[1])
        b2 = compile_bloc(cmd.children[2])
        index = cpt.__next__()
        return f"\n{e}\ncmp rax,0\njz mid{index}\n{b1}\njmp fin{index}\nmid{index}:\n{b2}\nfin{index}:\n"
    elif cmd.data == "comment":
        return ""
    elif cmd.data == "printf":
        return f"{compile_expr(cmd.children[0])}\nmov rdi, fmt\nmov rsi,rax\nxor rax,rax\ncall printf"
    else:
        raise Exception("Not implemented")

def compile_bloc(bloc):
    b = [compile_cmd(t) for t in bloc.children]
    a = []
    for l in b:
        if len(l) > 0:
            a += [l] 
    return "\n".join(a)

def compile_vars(ast):
    s = ""
    for i in range(len(ast.children)):
        s+= f"mov rbx, [rbp-0x10]\nmov rdi, [rbx+{8*(i+1)}]\ncall atoi\nmov [{ast.children[i].value}], rax\n"
    return s

def compile(prg):
    with open("moule.asm") as f:
        code = f.read()
        var_decl =  "\n".join([f"{x}: dq 0" for x in var_list(prg)])
        code = code.replace("VAR_DECL", var_decl)
        code = code.replace("RETURN", compile_expr(prg.children[2]))
        code = code.replace("BODY", compile_bloc(prg.children[1]))
        code = code.replace("VAR_INIT", compile_vars(prg.children[0]))
        return code

code = open("test.sc").read()
prg = grammaire.parse(code)
#print(pp_prog(prg))
print(compile(prg))