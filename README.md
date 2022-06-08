#   .nanoc (Nano C) compiler

##  Authors
- Hugo LAFLEUR
- Maximilien SONNIC
- Nguyen Anh VU

##  Main Implemented functionalities 
- function
  - there can be multiple functions in a program
- string
  - string can be defined 
  - string can be compared
  - sting can be printed out using printf
  - string lenght can be computed usung len()
- typage
  - types are static for any element
  - two types for variables : string and int
  - an additional type for function : void

## Implemented functionalities
- data structures:
  - integers
- expressions:
  - variables
  - numbers
  - binary expressions
    - \+ , \-, \*, \/, **
    - \<,  \>, \<=, \>=
    - ==, !=
    - &&, ||
  - expression with parentheses
  - no: !expression
- commands:
  - assignments
    - simple assignment: =
    - +=, -=, ++, --
  - loops:
    - while(...){...}
    - if(...){...}
    - if(...){...}else{...}
    - for(...;...;...){...}
  - printf
- comments:
  - single line: //...
  - multiple lines: /\*...\*/
- pretty printer

##  How to test features ?
- there is a test file that test all the features : test.nanoc
- to pretty print a nanoc file : python3 compilo.py pp test.nanoc
- to compile a nanoc file : python3 compilo.py cp test.nanoc > hum.asm
- nasm -felf64 hum.asm
- gcc -no-pie -fno-pie hum.o
- ./a.out
- additionnal test files:
  - teststring.nanoc allow to test the string features
  - testtype.nanoc allow to test the type features (it should return an error)


