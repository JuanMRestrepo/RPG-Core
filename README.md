# 1. RPG-CORE (RPG-C)

**Lenguaje:** RPG-CORE (abreviado **RPG-C**), un lenguaje esotérico e imperativo inspirado en las mecánicas de *Resident Evil*, *Honkai: Star Rail* y *Final Fantasy VII*.

**Integrante:** Juan Manuel Echeverry Restrepo

**Curso:** Lenguajes Formales, Ingeniería de Software, Institución Universitaria EAM. Docente: David Cano Baquero.

---

# 2. Cómo ejecutar

Requiere **Python 3.10 o superior** y no usa dependencias externas.

```bash
# Ejecutar un programa
python main.py programa.rpgc

# Modo interactivo (REPL): sin argumentos
python main.py
```

Ejemplos incluidos:

```bash
python main.py ejemplos/tabla_3.rpgc           # 3 6 9 12 15
python main.py ejemplos/factorial_5.rpgc       # 120
python main.py ejemplos/promedio_notas.rpgc    # 4.0  aprueba
python main.py ejemplos/demo_rpg_completo.rpgc # alcance, lógicos, negativos, EQUIPPED, HERB_STATUS
```

Opciones de depuración (opcionales):

```bash
python main.py --tokens programa.rpgc   # muestra los tokens y termina
python main.py --arbol programa.rpgc    # muestra el AST y termina (no ejecuta)
```

**Modo interactivo.** Mantiene las variables vivas entre líneas hasta escribir `salir`. Un bloque con llaves puede escribirse en varias líneas (el prompt cambia a `... `):

```
> INVENTORY_SLOT INT a = 2;
> MOSTRAR(a * 5);
10
> SI a > 1 ENTONCES {
...     MOSTRAR("mayor");
... }
mayor
> salir
```

**Errores.** Cualquier error (léxico, sintáctico o semántico) muestra el mensaje, la línea del código y un `^` bajo la columna exacta:

```
Error semántico en línea 2, columna 9: la variable 'edad' no ha sido declarada
    MOSTRAR(edad);
            ^
```

**Estructura del proyecto**

```
README.md
tokens.py      Token y jerarquía de errores (ErrorDeLenguaje, ErrorLexico, ErrorSintactico, ErrorSemantico)
lexer.py       Escáner carácter por carácter (sin regex)
arbol.py       Nodos del AST y mostrar_arbol
parser.py      Parser por descenso recursivo
interprete.py  Entorno (alcance anidado) e Interprete
main.py        Archivo, errores con ^ y modo interactivo
ejemplos/      tabla_3, factorial_5, promedio_notas y demo_rpg_completo (.rpgc)
```

---

# 3. Ficha del lenguaje

## Nombre y por qué se llama así

**RPG-CORE**: *RPG* porque el programa se modela como un ciclo de juego de rol y supervivencia (variables como ranuras de inventario, salud como estado de hierbas, ciclos como turnos de combate); *CORE* porque es el núcleo mínimo y estricto de un lenguaje: tipos, variables, decisiones y repetición. Las palabras reservadas vienen de tres juegos: `INVENTORY_SLOT`, `HERB_STATUS` y `DISCARD` (Resident Evil), `CYCLE_TURN` (Honkai: Star Rail) y `EQUIPPED` (Final Fantasy VII).

## Tabla de traducción desde Java

| Concepto | Java | RPG-CORE |
|---|---|---|
| Tipo entero | `int` | `INT` |
| Tipo decimal | `double` | `FLOAT` |
| Tipo texto | `String` | `STRING` |
| Tipo lógico | `boolean` | `BOOL` (`true` / `false`) |
| Tipo estado | *(no existe)* | `HERB_STATUS` (`FINE`, `POISON`, `DEAD`) |
| Declaración | `int hp = 100;` | `INVENTORY_SLOT INT hp = 100;` |
| Constante | `final int hp = 100;` | `EQUIPPED INVENTORY_SLOT INT hp = 100;` |
| Asignación | `hp = hp - 10;` | `hp = hp - 10;` |
| Fin de instrucción | `;` | `;` |
| Salida | `System.out.println(hp);` | `MOSTRAR(hp);` |
| Condicional | `if (c) { ... } else { ... }` | `SI c ENTONCES { ... } SINO { ... }` |
| Condicional encadenado | `else if (c2) { ... }` | `SINO SI c2 ENTONCES { ... }` |
| Ciclo | `while (c) { ... }` | `CYCLE_TURN (c) { ... }` |
| Operadores lógicos | `&&`, `\|\|`, `!` | `&&`, `\|\|`, `NO` |
| Liberar variable | *(lo hace el recolector de basura)* | `DISCARD(hp);` |
| Comentario | `// línea` y `/* bloque */` | `// línea` y `/* bloque */` |

## Decisión de diseño

La decisión central es hacer que **el lenguaje sea estricto con los tipos y que el estado de salud sea un tipo propio**:

1. **`HERB_STATUS` como tipo de primera clase.** En Java un estado como "sano / envenenado / muerto" se simularía con un `enum` o con `String`. En RPG-C es un tipo con exactamente tres valores válidos; guardar `"hola"` en una variable `HERB_STATUS` es un error semántico.
2. **Concatenación estricta.** Java permite `"Turno " + 3` (convierte el número a texto en silencio). En RPG-C `+` solo une `STRING` con `STRING`; mezclar texto con otro tipo es un error. Se evitan conversiones ocultas y los errores aparecen donde ocurren.
3. **Palabras en lugar de símbolos donde ayudan a leer:** `NO` en lugar de `!` (que además queda como carácter inválido si va solo), y `SI ... ENTONCES` / `SINO` en español.
4. **Liberación explícita con `DISCARD`**, que modela el "baúl de objetos" del survival horror: la variable se elimina del entorno y deja de existir.

---

# 4. Gramática final (EBNF)

Notación: `::=` "está formado por", `|` "o", `*` cero o más veces, `?` cero o una vez. Lo que va entre comillas es un token exacto; lo que va en MAYÚSCULAS es un tipo de token.

```ebnf
programa          ::= instruccion* EOF

instruccion       ::= declaracion | asignacion | salida | descarte
                    | condicional | ciclo

declaracion       ::= 'EQUIPPED'? 'INVENTORY_SLOT' TIPO IDENTIFICADOR '='
                      expresion_logica ';'
asignacion        ::= IDENTIFICADOR '=' expresion_logica ';'
salida            ::= 'MOSTRAR' '(' expresion_logica ')' ';'
descarte          ::= 'DISCARD' '(' IDENTIFICADOR ')' ';'
condicional       ::= 'SI' expresion_logica 'ENTONCES' bloque
                      ( 'SINO' ( bloque | condicional ) )?
ciclo             ::= 'CYCLE_TURN' '(' expresion_logica ')' bloque
bloque            ::= '{' instruccion* '}'

expresion_logica  ::= termino_logico ( '||' termino_logico )*
termino_logico    ::= factor_logico ( '&&' factor_logico )*
factor_logico     ::= 'NO' factor_logico | comparacion
comparacion       ::= expresion ( COMPARADOR expresion )*
expresion         ::= termino ( ( '+' | '-' ) termino )*
termino           ::= factor ( ( '*' | '/' ) factor )*
factor            ::= '-' factor | NUMERO | CADENA | BOOLEANO | VALOR_ESTADO
                    | IDENTIFICADOR | '(' expresion_logica ')'
```

**Tokens (categorías del lexer)**

```ebnf
TIPO            ::= 'INT' | 'FLOAT' | 'STRING' | 'BOOL' | 'HERB_STATUS'
PALABRA_CLAVE   ::= 'INVENTORY_SLOT' | 'EQUIPPED' | 'SI' | 'ENTONCES' | 'SINO'
                  | 'CYCLE_TURN' | 'MOSTRAR' | 'DISCARD' | 'NO'
BOOLEANO        ::= 'true' | 'false'
VALOR_ESTADO    ::= 'FINE' | 'POISON' | 'DEAD'
COMPARADOR      ::= '==' | '!=' | '>=' | '<=' | '>' | '<'
OPERADOR_LOGICO ::= '&&' | '||'
OPERADOR        ::= '+' | '-' | '*' | '/'
SIMBOLO         ::= '=' | ';' | '(' | ')' | '{' | '}' | ','
NUMERO          ::= DIGITO+ ( '.' DIGITO+ )?
CADENA          ::= '"' (cualquier carácter salvo '"' y salto de línea)* '"'
IDENTIFICADOR   ::= LETRA ( LETRA | DIGITO | '_' )*
```

**Precedencia** (de menor a mayor): `||` < `&&` < `NO` < comparadores < `+ -` < `* /` < menos unario. Por la regla `factor_logico`, `NO a == b` se lee como `NO (a == b)`. Los comparadores se asocian a la izquierda.

---

# 5. Reglas de operaciones entre tipos

La validación usa `type(valor)` de Python, por lo que un `BOOL` **nunca** se acepta como `INT`. Cualquier combinación que no esté en las tablas lanza un `ErrorSemantico` con la línea y la columna del operador.

## Aritméticas

| Operador | INT con INT | Con al menos un FLOAT | STRING con STRING | STRING con otro tipo | BOOL / HERB_STATUS |
|---|---|---|---|---|---|
| `+` | `INT` | `FLOAT` | Une los textos | Error | Error |
| `-` `*` | `INT` | `FLOAT` | Error | Error | Error |
| `/` | División entera (`//`) | `FLOAT` | Error | Error | Error |

- `7 / 2` da `3`, `7 / 2.0` da `3.5`. La división entera sigue la regla de Python (`//`, redondea hacia abajo).
- Dividir por cero (`INT` o `FLOAT`) lanza `ErrorSemantico: división por cero`.
- `HERB_STATUS` es un texto restringido a `FINE`, `POISON` o `DEAD`, pero no participa en la aritmética de enteros.

## Comparación

| Operador | Números (INT / FLOAT) | STRING con STRING | BOOL con BOOL | Cualquier otra mezcla |
|---|---|---|---|---|
| `==` `!=` | Sí (`1 == 1.0` es `true`) | Sí | Sí | Error |
| `<` `>` `<=` `>=` | Sí | Error | Error | Error |

Un `HERB_STATUS` se compara con `==` / `!=` contra otro estado (`salud == DEAD`).

## Lógicos y unarios

| Operador | Operandos permitidos | Resultado | Notas |
|---|---|---|---|
| `&&` | `BOOL`, `BOOL` | `BOOL` | Cortocircuito: si el izquierdo es `false`, el derecho no se evalúa |
| `\|\|` | `BOOL`, `BOOL` | `BOOL` | Cortocircuito: si el izquierdo es `true`, el derecho no se evalúa |
| `NO` | `BOOL` | `BOOL` | Negación |
| `-` (unario) | `INT` o `FLOAT` | Mismo tipo | `-(x + 2)`, `- -5` |

La condición de `SI` y de `CYCLE_TURN` debe dar `BOOL`; si no, hay `ErrorSemantico` en la posición de la palabra clave.

## Asignación y declaración

| Tipo de la variable | Acepta | Detalle |
|---|---|---|
| `INT` | `INT` | No acepta `FLOAT` ni `BOOL` |
| `FLOAT` | `INT`, `FLOAT` | Un `INT` se convierte a `FLOAT` (`FLOAT f = 3;` guarda `3.0`) |
| `STRING` | `STRING` | |
| `BOOL` | `BOOL` | No acepta `0` ni `1` |
| `HERB_STATUS` | `FINE`, `POISON`, `DEAD` | Cualquier otro texto es error |

## Reglas semánticas adicionales

| Situación | Resultado |
|---|---|
| Usar o asignar una variable no declarada | `ErrorSemantico` |
| Declarar dos veces el mismo nombre **en el mismo bloque** | `ErrorSemantico` (en un bloque interno se permite "sombrear" un nombre externo) |
| Reasignar una variable `EQUIPPED` | `ErrorSemantico` |
| Usar una variable fuera del bloque donde se declaró | `ErrorSemantico` (alcance léxico anidado) |
| `DISCARD` de una variable inexistente | `ErrorSemantico` |
| `CYCLE_TURN` con más de 100 000 vueltas | `ErrorSemantico` en la posición de `CYCLE_TURN` |

**Salida con `MOSTRAR`:** los `BOOL` se imprimen como `true` / `false`; los `FLOAT` con su parte decimal (`9000.0`).

---

# 6. Requerimientos electivos implementados

## Electivo 1: Tipo booleano

`BOOL` es un tipo real del lenguaje, con los literales `true` y `false`, que puede guardarse en variables y usarse en condiciones:

```
INVENTORY_SLOT INT n = 7;
INVENTORY_SLOT BOOL en_rango = n >= 1 && n <= 10;
SI en_rango ENTONCES {
    MOSTRAR("en rango");
}
MOSTRAR(en_rango);     // true
```

- Se distingue estrictamente de `INT` (usa `type(valor)`, no `isinstance`): `INVENTORY_SLOT INT x = true;` y `INVENTORY_SLOT BOOL b = 1;` son errores semánticos.
- Los comparadores producen `BOOL`; `&&`, `||` y `NO` solo aceptan `BOOL`.
- Una condición que no sea `BOOL` (por ejemplo `SI 5 ENTONCES`) lanza `ErrorSemantico`.
- Casos de error: `MOSTRAR(NO 5);`, `SI 1 && 2 ENTONCES { ... }`.

## Electivo 2: Modo interactivo

`python main.py` sin argumentos abre un REPL (`> `) que ejecuta línea por línea **recordando las variables** gracias a un `Entorno` único que vive durante toda la sesión:

```
> INVENTORY_SLOT INT a = 2;
> MOSTRAR(a);
2
> MOSTRAR(b);
Error semántico en línea 1, columna 9: la variable 'b' no ha sido declarada
    MOSTRAR(b);
            ^
> a = a + 1;
> MOSTRAR(a);
3
> salir
```

- Un error no cierra la sesión: se muestra con su `^` y el entorno sigue intacto.
- Los bloques con llaves pueden escribirse en varias líneas (prompt `... ` mientras falte cerrar una `{`).
- `Ctrl+C` cancela lo que se estaba escribiendo; `salir` o `Ctrl+D` terminan la sesión.
