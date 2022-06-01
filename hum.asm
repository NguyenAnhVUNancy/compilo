extern printf, atoi
global main
section .data
fmt_int: db "%d", 10, 0
fmt_str: db "%s", 10, 0
X: dq 0
A: dq 0
A_len: dq 0
const_a: db "a",0 
const_bc: db "bc",0 


section .text
main:
  push rbp
  mov rbp, rsp
  push rdi
  push rsi

  mov rbx, [rbp-0x10]
  lea rdi, [rbx+8]
  call atoi
  mov [X], rax

  mov rax, const_a
  mov [A], rax
  mov rax, const_bc
  push rax
  mov rax, const_a
  pop rbx
  add rax, rbx
  mov rdi, fmt_str
  mov rsi, rax
  xor rax, rax
  call printf
  mov rax, 0

  mov rdi, fmt_int
  mov rsi, rax
  xor rax, rax
  call printf
  add rsp, 16
  pop rbp
  ret

