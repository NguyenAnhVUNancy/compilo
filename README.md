#   .sc (Simili C) compiler

##  Authors
- Hugo LAFLEUR
- Maximilien SONNIC
- Nguyen Anh VU

##  Implemented functionalities
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