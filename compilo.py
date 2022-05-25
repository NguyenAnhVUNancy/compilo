import lark

grammaire = lark.Lark("""
variables : var (","  var)*
expr : IDENTIFIANT -> variable | NUMBER -> nombre
| expr OP expr -> binexpr | "(" expr ")" -> parenexpr
| "!" expr -> not
cmd : shortcmd ";" -> short |"while" "(" expr ")" "{" bloc "}" -> while
    | "if" "(" expr ")" "{" bloc "}" -> if | "printf" "(" expr ")" ";"-> printf
    | "if" "(" expr ")" "{" bloc "}" "else" "{" bloc "}" -> ifelse
    | "for" "(" shortcmd ";" expr ";" shortcmd ")" "{" bloc "}" -> for
    | COMMENT -> comment
shortcmd : var "=" expr -> declaration | IDENTIFIANT "=" expr -> assignment | IDENTIFIANT "+=" expr -> add | IDENTIFIANT "-=" expr -> sub
    | IDENTIFIANT "++" -> incr | IDENTIFIANT "--" -> decr
bloc : (cmd)*
func : TYPE NOM "(" variables ")" "{" bloc "return" "(" expr ")" ";" "}"
prog : TYPE "main" "(" variables ")" "{" bloc "return" "(" expr ")" ";" "}"
var : TYPE IDENTIFIANT
COMMENT : "//" LINE | "/*" MULTILINE "*/"
NUMBER : /[0-9]+/
OP : /[+\*\/><-]/ | /[!<>=](=)/ | "**" | "&&" | "||"
IDENTIFIANT : /[a-zA-Z][a-zA-Z0-9]*/
TYPE : "int" | "string"
LINE : /.*/
MULTILINE : /[^\*]*((\*)+[^\/\*][^\*]*)*/s
NOM : /[^]*/
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

def pp_prog(prog):
    type = prog.children[0]
    vars = pp_variables(prog.children[1])
    bloc = pp_bloc(prog.children[2])
    ret = pp_expr(prog.children[3])
    return f"{type} main ({vars}){{\n{bloc}\n    return({ret}); \n}} "


def var_list(ast):
    if isinstance(ast, lark.Token):
        if ast.type == "IDENTIFIANT":
            return {ast}
        else:
            return set()
    s = set()
    for c in ast.children:
        s.update(var_list(c))
    return s

def compile_expr(expr):
    if expr.data == "variable":
        return f"mov rax, [{expr.children[0].value}]"
    elif expr.data == "nombre":
        return f"mov rax, {expr.children[0].value}"
    elif expr.data == "binexpr":
        e1 = compile_expr(expr.children[0])
        e2 = compile_expr(expr.children[2])
        op = expr.children[1].value
        index = cpt.__next__()
        if op == '/':
            return f"mov rdx, 0\n{e2}\npush rax\n{e1}\npop rbx\n{intop2asm[op]} qword rbx"
        elif op == "**":
            return f"{e1}\npush rax\n{e2}\nmov rbx, rax\npop rcx\nmov rdx, 0\nmov rax, 1\nbegin{index}:\ncmp rbx, 0\nje end{index}\njl mid{index}\nimul rax, rcx\nsub rbx, 1\njmp begin{index}\nmid{index}:\nidiv rcx\nadd rbx, 1\njmp begin{index}\nend{index}:"
        elif op in {'+','-','*','/'}:
            return f"{e2}\npush rax\n{e1}\npop rbx\n{intop2asm[op]} rax, rbx"
        elif op in {"==", "!=", '<', '>', "<=", ">="}:
            return f"{e2}\npush rax\n{e1}\npop rbx\ncmp rax, rbx\n{cmpop2asm[op]} mid{index}\nmov rax, 0\njmp end{index}\nmid{index}:\nmov rax, 1\nend{index}:"
        elif op == "&&":
            return f"{e2}\npush rax\n{e1}\npop rbx\nimul rax, rbx"
        elif op == "||":
            return f"{e1}\ncmp rax, 0\njne mid{index}\n{e2}\ncmp rax, 0\njne mid{index}\nmov rax, 0\njmp end{index}\nmid{index}:\nmov rax, 1\nend{index}:"
        else:
            raise Exception("Not implemented")
    elif expr.data == "parenexpr":
        return compile_expr(expr.children[0])
    elif expr.data =="not":
        e = compile_expr(expr.children[0])
        index = cpt.__next__()
        return f"{e}\ncmp rax, 0\nje mid{index}\nmov rax, 0\njmp end{index}\nmid{index}:\nmov rax, 1\nend{index}:"
    else:
        raise Exception("Not implemented")

def compile_short(cmd):
    if cmd.data == "assignment":
        lhs = cmd.children[0].value
        rhs = compile_expr(cmd.children[1])
        return f"{rhs}\nmov [{lhs}], rax"
    elif cmd.data == "add":
        lhs = cmd.children[0].value
        rhs = compile_expr(cmd.children[1])
        return f"mov rbx, [{lhs}]\n{rhs}\nadd rbx, rax\nmov [{lhs}], rbx"
    elif cmd.data == "sub":
        lhs = cmd.children[0].value
        rhs = compile_expr(cmd.children[1])
        return f"mov rbx, [{lhs}]\n{rhs}\nsub rbx, rax\nmov [{lhs}], rbx"
    elif cmd.data == "incr":
        lhs = cmd.children[0].value
        return f"mov rax, [{lhs}]\nadd rax, 1\nmov [{lhs}], rax"
    elif cmd.data == "decr":
        lhs = cmd.children[0].value
        return f"mov rax, [{lhs}]\nsub rax, 1\nmov [{lhs}], rax"
    else:
        raise Exception("Not implemented")

def compile_cmd(cmd):
    if cmd.data == "short":
        return compile_short(cmd.children[0])
    elif cmd.data == "while":
        e = compile_expr(cmd.children[0])
        b = compile_bloc(cmd.children[1])
        index = cpt.__next__()
        return f"begin{index}:\n{e}\ncmp rax, 0\njz end{index}\n{b}\njmp begin{index}\nend{index}:"
    elif cmd.data == "if":
        e = compile_expr(cmd.children[0])
        b = compile_bloc(cmd.children[1])
        index = cpt.__next__()
        return f"{e}\ncmp rax, 0\njz end{index}\n{b}\nend{index}:"
    elif cmd.data == "ifelse":
        e = compile_expr(cmd.children[0])
        b1 = compile_bloc(cmd.children[1])
        b2 = compile_bloc(cmd.children[2])
        index = cpt.__next__()
        return f"{e}\ncmp rax, 0\njz mid{index}\n{b1}\njmp end{index}\nmid{index}:\n{b2}\nend{index}:"
    elif cmd.data == "for":
        c1 = compile_short(cmd.children[0])
        e = compile_expr(cmd.children[1])
        c2 = compile_short(cmd.children[2])
        b = compile_bloc(cmd.children[3])
        index = cpt.__next__()
        return f"{c1}\nbegin{index}:\n{e}\ncmp rax,0\nje end{index}\n{b}\n{c2}\njmp begin{index}\nend{index}:"
    elif cmd.data == "comment":
        return ""
    elif cmd.data == "printf":
        return f"{compile_expr(cmd.children[0])}\nmov rdi, fmt\nmov rsi, rax\nxor rax, rax\ncall printf"
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
print(pp_prog(prg))
#print(var_list(prg))
#print(compile(prg))
