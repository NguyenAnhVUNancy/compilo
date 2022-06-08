import lark
import sys

grammaire = lark.Lark("""
variables : "(" var (","  var)* ")" | "(" ")"
variablecall : "(" expr ("," expr)* ")" | "(" ")"
expr : IDENTIFIANT -> variable | NUMBER -> nombre | STRING -> string
| expr OP expr -> binexpr | "(" expr ")" -> parenexpr
| "!" expr -> not | "len(" expr ")" -> len
| NOM variablecall -> funcall
cmd : shortcmd ";" -> short |"while" "(" expr ")" "{" bloc "}" -> while
    | "if" "(" expr ")" "{" bloc "}" -> if | "printf" "(" expr ")" ";"-> printf
    | "if" "(" expr ")" "{" bloc "}" "else" "{" bloc "}" -> ifelse
    | "for" "(" shortcmd ";" expr ";" shortcmd ")" "{" bloc "}" -> for
    | COMMENT -> comment
shortcmd : var "=" expr -> declaration | var -> shortdeclaration
    | IDENTIFIANT "=" expr -> assignment | IDENTIFIANT "+=" expr -> add | IDENTIFIANT "-=" expr -> sub
    | IDENTIFIANT "++" -> incr | IDENTIFIANT "--" -> decr
bloc : (cmd)*
func : TYPE NOM variables "{" bloc "return" "(" expr ")" ";" "}"
prog : (func | COMMENT)* func COMMENT*
var : TYPE IDENTIFIANT
COMMENT : "//" LINE | "/*" MULTILINE "*/"
NUMBER : /[0-9]+/
STRING : /"([^"]*)"/
OP : /[+\*\/><-]/ | /[!<>=](=)/ | "**" | "&&" | "||"
IDENTIFIANT : /[a-zA-Z][a-zA-Z0-9]*/
TYPE : "int" | "string"
LINE : /.*/
MULTILINE : /[^\*]*((\*)+[^\/\*][^\*]*)*/s
NOM : /[a-zA-Z0-9\_]+/
%import common.WS
%ignore WS
""", start="prog")

cpt = iter(range(10000))
intop2asm = {'+': "add", '-': "sub", '*': "imul", '/': "idiv"}
cmpop2asm = {"==": "je", "!=": "jne", '>': "jg",
             '<': "jl", ">=": "jge", "<=": "jle"}
argsreg = ["rdi", "rsi", "rdx", "rcx", "r8", "r9"]


def pp_variables(vars):  # This is used to pretty print a variable
    return ", ".join([f"{t.children[0].value} {t.children[1].value}" for t in vars.children])


def pp_expr(expr):  # This is used to pretty print an expression
    if expr.data in {"variable", "nombre", "string"}:
        return expr.children[0].value
    elif expr.data == "funcall":
        s = f"{expr.children[0].value}("
        args = expr.children[1].children
        if len(args)>0:
            s += pp_expr(args[0])
            for i in range(1, len(args)):
                s += ", " + pp_expr(args[i])
        s += ")"
        return s
    elif expr.data == "binexpr":
        e1 = pp_expr(expr.children[0])
        e2 = pp_expr(expr.children[2])
        op = expr.children[1].value
        return f"{e1} {op} {e2}"
    elif expr.data == "parenexpr":
        return f"({ pp_expr( expr.children[0] ) }) "
    elif expr.data == "len":
        return f"len({pp_expr(expr.children[0])})"
    else:
        raise Exception("Not implemented")


def pp_short(cmd):  # This is used to pretty print a short command (assignement, declaration, ...), which itself is a command
    if cmd.data == "assignment":
        lhs = cmd.children[0].value
        rhs = pp_expr(cmd.children[1])
        return f"{lhs} = {rhs}"
    elif cmd.data == "declaration":
        lhs = f"{cmd.children[0].children[0].value} {cmd.children[0].children[1].value}"
        rhs = pp_expr(cmd.children[1])
        return f"{lhs} = {rhs}"
    elif cmd.data == "shortdeclaration":
        lhs = f"{cmd.children[0].children[0].value} {cmd.children[0].children[1].value}"
        return f"{lhs}"
    elif cmd.data == "add":
        lhs = cmd.children[0].value
        rhs = pp_expr(cmd.children[1])
        return f"{lhs} += {rhs}"
    elif cmd.data == "sub":
        lhs = cmd.children[0].value
        rhs = pp_expr(cmd.children[1])
        return f"{lhs} += {rhs}"
    elif cmd.data == "incr":
        lhs = cmd.children[0].value
        return f"{lhs}++"
    elif cmd.data == "decr":
        lhs = cmd.children[0].value
        return f"{lhs}--"
    else:
        raise Exception("Not implemented")


def pp_cmd(cmd):    # This is used to pretty print a command
    if cmd.data == "short":
        e = pp_short(cmd.children[0])
        return f"{e};"
    elif cmd.data == "printf":
        return f"printf({pp_expr(cmd.children[0])});"
    elif cmd.data in {"while", "if"}:
        e = pp_expr(cmd.children[0])
        b = pp_bloc(cmd.children[1])
        return f"{cmd.data}({e}){{\n{b}\n}}"
    elif cmd.data == "ifelse":
        e = pp_expr(cmd.children[0])
        b1 = pp_bloc(cmd.children[1])
        b2 = pp_bloc(cmd.children[2])
        return f"if({e}){{\n{b1}\n}}else{{\n{b2}\n}}"
    elif cmd.data == "for":
        c1 = pp_short(cmd.children[0])
        e = pp_expr(cmd.children[1])
        c2 = pp_short(cmd.children[2])
        bloc = pp_bloc(cmd.children[3])
        return f"for({c1};{e};{c2}){{\n{bloc}\n}}"
    elif cmd.data == "comment":
        return ""
    else:
        raise Exception("Not implemented")


def pp_bloc(bloc):  # This is used to pretty print a bloc
    b = "\n".join([pp_cmd(t) for t in bloc.children]).split("\n")
    a = []
    for i in range(len(b)):
        if len(b[i]) > 0:
            a += ["    " + b[i]]
    return "\n".join(a)


def pp_func(func):  # This is used to pretty print a function
    type = func.children[0]
    name = func.children[1]
    vars = pp_variables(func.children[2])
    bloc = pp_bloc(func.children[3])
    ret = pp_expr(func.children[4])
    return f"{type} {name} ({vars}){{\n{bloc}\n    return({ret}); \n}} "


def pp_prog(prog):  # This is used to pretty print a program
    s = ""
    for func in prog.children:
        if not isinstance(func, lark.Token):
            if func.data == "func":
                s += f"{pp_func(func)}\n\n"
            else:
                raise Exception("Not implemented")
    return s


def var_list(ast):  # This function will gather all the variables in a program
    if isinstance(ast, lark.Token):
        return set()
    elif ast.data == "var":
        return {ast}

    s = set()
    for c in ast.children:
        s.update(var_list(c))
    return s


def string_list(ast):   # This function will gather all the strings in a program
    if isinstance(ast, lark.Token):
        return set()
    elif ast.data == "string":
        return {ast}

    s = set()
    for c in ast.children:
        s.update(string_list(c))
    return s


def type_expr(expr, typelist):  # This function will check if an expression is of a given type
    if expr.data == "variable":
        e = expr.children[0].value
        if e in typelist.keys():
            return typelist[e]
        else:
            raise Exception(f"{e} not declared")
    elif expr.data == "funcall":
        e = expr.children[0].value
        if e in typelist.keys():
            return typelist[e][0]
        else:
            raise Exception(f"{e} not declared")
    elif expr.data == "len":
        return "int"
    elif expr.data == "nombre":
        return "int"
    elif expr.data == "binexpr":
        e1 = type_expr(expr.children[0], typelist)
        e2 = type_expr(expr.children[2], typelist)
        if e1 != e2:
            raise Exception("Type error")
        elif expr.children[1] in {"==", "!=", '<', '>', "<=", ">="}:
            return "int"
        else:
            return e1
    elif expr.data in {"parenexpr", "not"}:
        return type_expr(expr.children[0], typelist)
    elif expr.data == "string":
        return "string"
    elif expr.data == "len":
        return "int"
    else:
        raise Exception("Not implemented")


def compile_expr(expr, typelist):   # This function will compile an expression
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
                elif op in {'+', '-', '*', '/'}:
                    return f"{e2}\n  push rax\n{e1}\n  pop rbx\n  {intop2asm[op]} rax, rbx"
                elif op in {"==", "!=", '<', '>', "<=", ">="}:
                    return f"{e2}\n  push rax\n{e1}\n  pop rbx\n  cmp rax, rbx\n  {cmpop2asm[op]} mid{index}\n  mov rax, 0\n  jmp end{index}\nmid{index}:\n  mov rax, 1\nend{index}:"
                elif op == "&&":
                    return f"{e2}\n  push rax\n{e1}\n  pop rbx\n  imul rax, rbx"
                elif op == "||":
                    return f"{e1}\n  cmp rax, 0\n  jne mid{index}\n{e2}\n  cmp rax, 0\n  jne mid{index}\n  mov rax, 0\n  jmp end{index}\nmid{index}:\n  mov rax, 1\n  end{index}:"
                else:
                    raise Exception("Not implemented")
            elif t1 == "string":
                e1 = compile_expr(expr.children[0], typelist)
                e2 = compile_expr(expr.children[2], typelist)
                op = expr.children[1].value
                index = cpt.__next__()
                if op in {"=="}:
                    return f"{e2}\n  push rax\n{e1}\n  pop rbx\n  cmp rax, rbx\n  {cmpop2asm[op]} mid{index}\n  mov rax, 0\n  jmp end{index}\nmid{index}:\n  mov rax, 1\nend{index}:"
                elif op in {"+"}:
                    return f"{e1}\n  mov rdx, rax\n{e2}\n  mov rsi, rdx\n  mov rdi, rax\n  call strcat"
                else:
                    raise Exception("Not implemented")
            else:
                raise Exception("Not implemented")
    elif expr.data == "parenexpr":
        return compile_expr(expr.children[0], typelist)
    elif expr.data == "not":
        e = compile_expr(expr.children[0], typelist)
        index = cpt.__next__()
        return f"{e}\n  cmp rax, 0\n  je mid{index}\n  mov rax, 0\n  jmp end{index}\nmid{index}:\n  mov rax, 1\nend{index}:"
    elif expr.data == "string":
        return f"  mov rax, const_{expr.children[0][1:(len(expr.children[0])-1)]}"
    elif expr.data == "len":
        if type_expr(expr.children[0], typelist) == "string":
            if (expr.children[0].data == "variable"):
                return f"  mov rax, [{expr.children[0].children[0].value}_len]\n  sub rax,1"
            elif (expr.children[0].data == "string"):
                return f"  mov rax, const_{expr.children[0].children[0].value[1:(len(expr.children[0].children[0].value)-1)]}_len\n  sub rax,1"
            else:
                raise Exception("Not implemented")
    elif expr.data == "funcall":
        type = []
        args = expr.children[1].children
        for e in args:
            type += [type_expr(e, typelist)]
        if check_fun_type(typelist, type, expr):
            s = ""
            for i in range(len(args)):
                s += compile_expr(args[i], typelist)
                s += "\n"
                if i < 6:
                    s += f"  mov {argsreg[i]}, rax\n"
                else:
                    s += "  push rax\n"
            s += f"  call {expr.children[0]}"
            return s
    else:
        raise Exception("Not implemented")


def check_fun_type(typelist, type, func):
    e = func.children[0].value
    if e in typelist.keys():
        func_args_type = typelist[e][1]
        if len(func_args_type) < len(type):
            raise Exception(
                f"Too many arguments, expected {len(func_args_type)}, {len(type)} given")
        elif len(func_args_type) > len(type):
            raise Exception(
                f"Too few arguments, expected {len(func_args_type)}, {len(type)} given")
        else:
            for i in range(len(type)):
                if type[i] != func_args_type[i]:
                    raise Exception(
                        f"Wrong argument type, expected {func_args_type}, {type} given")
            return True
    else:
        raise Exception(f"{e} not declared")


# This function will compile a short command (assignement, declaration, ...)
def compile_short(cmd, typelist):
    if cmd.data == "assignment":
        lhs = cmd.children[0].value
        if typelist[lhs] == type_expr(cmd.children[1], typelist) and typelist[lhs] == "string":
            rhs = compile_expr(cmd.children[1], typelist)
            return f"{rhs}\n  mov [{lhs}], rax\n{rhs}_len\n  mov [{lhs}_len], rax"
        elif typelist[lhs] == type_expr(cmd.children[1], typelist) and typelist[lhs] == "int":
            rhs = compile_expr(cmd.children[1], typelist)
            return f"{rhs}\n  mov [{lhs}], rax"
        else:
            raise Exception("Type error")
    elif cmd.data == "declaration":
        lhs = cmd.children[0].children[1].value
        if typelist[lhs] == type_expr(cmd.children[1], typelist) and typelist[lhs] == "string":
            rhs = compile_expr(cmd.children[1], typelist)
            return f"{rhs}\n  mov [{lhs}], rax\n{rhs}_len\n  mov [{lhs}_len], rax"
        elif typelist[lhs] == type_expr(cmd.children[1], typelist) and typelist[lhs] == "int":
            rhs = compile_expr(cmd.children[1], typelist)
            return f"{rhs}\n  mov [{lhs}], rax"
        else:
            raise Exception("Type error")
    elif cmd.data == "shortdeclaration":
        lhs = cmd.children[0].children[1].value
        if typelist[lhs] == "int":
            return f"  mov [{lhs}], DWORD 0"
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


def compile_cmd(cmd, typelist):  # This function will compile a command (for, while, if, etc.)
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
        if type_expr(cmd.children[0], typelist) == "int":
            return f"{compile_expr(cmd.children[0], typelist)}\n  mov rdi, fmt_int\n  mov rsi, rax\n  xor rax, rax\n  call printf"
        if type_expr(cmd.children[0], typelist) == "string":
            return f"{compile_expr(cmd.children[0], typelist)}\n  mov rdi, fmt_str\n  mov rsi, rax\n  xor rax, rax\n  call printf"
    else:
        raise Exception("Not implemented")


def compile_bloc(bloc, typelist):   # This function is used to compile a bloc of commands
    b = [compile_cmd(t, typelist) for t in bloc.children]
    a = []
    for l in b:
        if len(l) > 0:
            a += [l]
    return "\n".join(a)


def compile_func(func, func_type):
    varlist = var_list(func)
    typelist = type_list(varlist)
    for f in func_type.keys():
        typelist[f] = func_type[f]
    args = func.children[2].children
    ret = func.children[0].value
    returntype = type_expr(func.children[4], typelist)
    if returntype != ret:
        raise Exception(
            f"Wrong return type, expected {func.children[0].value}, {returntype} given")
    with open("moule_func.asm") as f:
        code = f.read()
        code = code.replace("NAME", func.children[1])
        var_init = ""
        for i in range(len(args)):
            if i < 6:
                var_init += f"  mov [{args[i].children[1].value}], {argsreg[i]}\n"
            else:
                var_init += f"  pop rax\n  mov [{args[i].children[1]}],x rax\n"
        code = code.replace("VAR_INIT", var_init)
        code = code.replace("RETURN", compile_expr(func.children[4], typelist))
        code = code.replace("BODY", compile_bloc(func.children[3], typelist))
        for i in range(len(args)):
            code = code.replace(
                f"[{args[i].children[1].value}]", f"[rbp-{8*(i+1)}]")
        code += "\n"
        return code


# This function aim at converting variables into their equivalent assembly code
def compile_vars(ast):
    s = ""
    for i in range(len(ast.children)):
        s += f" mov rbx, [rbp-0x10]\n mov rdi, [rbx+{8*(i+1)}]\n call atoi\n mov [{ast.children[i].children[1].value}], rax\n"
    return s


def type_list(varlist):  # This function's goal is to create a dictionary that will contain the type of each variable, usefull when compiling expressions
    dico = {}
    for e in varlist:
        dico[e.children[1].value] = e.children[0].value
    return dico


def func_type_list(func):
    dico = {}
    for f in func:
        dico[f.children[1].value] = [f.children[0].value, [
            a.children[0].value for a in f.children[2].children]]
    return dico


#  This function is used in the compilation of the main variable at the head of an assembly file
def var_decl(varlist, stringlist):
    s = ""
    for x in varlist:
        if x.children[0] == "int":
            s += f"{x.children[1]}: dq 0\n"
        if x.children[0] == "string":
            s += f"{x.children[1]}: dq 0\n{x.children[1]}_len: dq 0\n"
    for x in stringlist:
        s += f"const_{x.children[0][1:(len(x.children[0])-1)]}: db {x.children[0]},0 \nconst_{x.children[0][1:(len(x.children[0])-1)]}_len: equ $ - const_{x.children[0][1:(len(x.children[0])-1)]} \n"
    return s


def find_main(prg):  # This function will find the function named "main" in the nanoc program
    func = []
    for t in prg.children:
        if not isinstance(t, lark.Token):
            if t.data == "func":
                name = t.children[1]
                if name == "main":
                    main = t
                else:
                    func += [t]
    return [main, func]


def compile(prg):  # This function will compile the nanoc program into an assembly file
    with open("moule.asm") as f:
        [main, func] = find_main(prg)
        code = f.read()
        varlist = var_list(main)
        stringlist = string_list(main)
        typelist = type_list(varlist)
        func_type = func_type_list(func)
        for f in func_type.keys():
            typelist[f] = func_type[f]
        compiled_func = ""
        for f in func:
            compiled_func += compile_func(f, func_type)
        code = code.replace("FUNC", compiled_func)
        code = code.replace("VAR_DECL", var_decl(varlist, stringlist))
        code = code.replace("RETURN", compile_expr(main.children[4], typelist))
        code = code.replace("BODY", compile_bloc(main.children[3], typelist))
        code = code.replace("VAR_INIT", compile_vars(main.children[2]))
        return code


if len(sys.argv) == 1:
    args = ["", "cp", "test.nanoc"]
else:
    args = sys.argv

if args[1] == "pp":
    print(pp_prog(grammaire.parse(open(args[2]).read())))
elif args[1] == "cp":
    print(compile(grammaire.parse(open(args[2]).read())))
else:
    raise Exception("Not implemented")


# How to use this script:
# python3.9 compilo.py cp test.nanoc > hum.asm
# nasm -felf64 hum.asm
# gcc -no-pie -fno-pie hum.o
