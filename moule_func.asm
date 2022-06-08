NAME:
  push rbp
  mov rbp, rsp
  push rdi
  push rsi

VAR_INIT
BODY
RETURN

  add rsp, 16
  pop rbp
  ret