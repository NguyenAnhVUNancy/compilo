extern printf, atoi, strcat
global main
section .data
fmt_int: db "%d", 10, 0
fmt_str: db "%s", 10, 0
VAR_DECL

section .text
FUNC

main:
  push rbp
  mov rbp, rsp
  push rdi
  push rsi

VAR_INIT
BODY
RETURN

  mov rdi, fmt_int
  mov rsi, rax
  xor rax, rax
  call printf
  add rsp, 16
  pop rbp
  ret


