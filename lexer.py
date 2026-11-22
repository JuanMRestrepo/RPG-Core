"""
lexer.py - Analizador léxico de RPG-CORE (RPG-C).

Decisiones de diseño (heredadas del primer lexer del proyecto)
---------------------------------------------------------------
* Un solo recorrido con puntero `i`, sin expresiones regulares: así el orden de
  las comprobaciones es visible y se puede justificar carácter por carácter.
* `linea` y `col` (base 1) se llevan aparte y no se derivan de `i`.
* Las palabras se leen COMPLETAS y solo después se clasifican; comparar prefijos
  partiría `INTEGER` en `INT` + `EGER`.
* Los errores se lanzan como excepción (`ErrorLexico`): un lexer que sigue después
  de un error produce tokens basura que luego confunden al parser.
* El lexer distingue mayúsculas y minúsculas: `true`/`false` son minúsculas y
  `NO` (negación) es la palabra clave, mientras que `no` sería un identificador.
"""

from tokens import Token, ErrorLexico

# ---------------------------------------------------------------------------
# Categorías de tokens
# ---------------------------------------------------------------------------
TIPOS = {"INT", "FLOAT", "STRING", "BOOL", "HERB_STATUS"}

PALABRAS_CLAVE = {
    "INVENTORY_SLOT", "EQUIPPED", "SI", "ENTONCES", "SINO",
    "CYCLE_TURN", "MOSTRAR", "DISCARD", "NO",
}

BOOLEANOS = {"true", "false"}

# Estados válidos para una variable HERB_STATUS (salud al estilo Resident Evil).
VALORES_ESTADO = {"FINE", "POISON", "DEAD"}

# Tuplas (no conjuntos) porque el orden importa: los de dos caracteres van
# primero, o `>=` se leería como `>` seguido de `=`.
COMPARADORES = ("==", "!=", ">=", "<=", ">", "<")
OPERADORES_LOGICOS = ("&&", "||")

OPERADORES = {"+", "-", "*", "/"}
SIMBOLOS = {"=", ";", "(", ")", "{", "}", ","}

# Se enumeran a mano porque str.isdigit() acepta dígitos Unicode como '²'.
DIGITOS = "0123456789"


def tokenizar(codigo):
    """Convierte el texto fuente en una lista de `Token` terminada en EOF.

    Lanza `ErrorLexico` ante el primer problema encontrado.
    """
    tokens = []
    i = 0
    n = len(codigo)
    linea = 1
    col = 1

    # El orden de las comprobaciones no es arbitrario: cada una asume que las
    # anteriores ya descartaron sus casos. Espacios y comentarios van primero
    # para que nunca se interpreten como parte de otro token.
    while i < n:
        c = codigo[i]

        # --- Saltos de línea y espacios ------------------------------------
        if c == "\n":
            i += 1
            linea += 1
            col = 1
            continue

        # \r (archivos de Windows) no cuenta como columna.
        if c == "\r":
            i += 1
            continue

        if c == " " or c == "\t":
            i += 1
            col += 1
            continue

        # --- Comentario de línea: // ... hasta el final de la línea ---------
        # Se para ANTES del '\n' para que el bloque de arriba sea el único
        # lugar que incrementa `linea`.
        if codigo.startswith("//", i):
            while i < n and codigo[i] != "\n":
                if codigo[i] != "\r":
                    col += 1
                i += 1
            continue

        # --- Comentario de bloque: /* ... */ (puede abarcar varias líneas) --
        if codigo.startswith("/*", i):
            linea_ini, col_ini = linea, col
            i += 2
            col += 2
            while i < n and not codigo.startswith("*/", i):
                if codigo[i] == "\n":
                    linea += 1
                    col = 1
                elif codigo[i] != "\r":
                    col += 1
                i += 1
            if i >= n:
                # El error se reporta donde EMPEZÓ el comentario.
                raise ErrorLexico("comentario sin cerrar", linea_ini, col_ini)
            i += 2
            col += 2
            continue

        # --- Palabras: tipos, palabras clave, booleanos, estados, nombres ---
        # Empieza con letra (isalpha también acepta la Ñ), por eso `_x` no es
        # un identificador y cae al error final.
        if c.isalpha():
            inicio = i
            while i < n and (codigo[i].isalnum() or codigo[i] == "_"):
                i += 1
            palabra = codigo[inicio:i]
            if palabra in TIPOS:
                tipo = "TIPO"
            elif palabra in PALABRAS_CLAVE:
                tipo = "PALABRA_CLAVE"
            elif palabra in BOOLEANOS:
                tipo = "BOOLEANO"
            elif palabra in VALORES_ESTADO:
                tipo = "VALOR_ESTADO"
            else:
                tipo = "IDENTIFICADOR"
            tokens.append(Token(tipo, palabra, linea, col))
            col += i - inicio
            continue

        # --- Números: enteros y flotantes -----------------------------------
        # Se consumen dígitos Y puntos juntos para tomar `3.4.5` como una sola
        # pieza mala; el error se ubica al inicio del literal.
        if c in DIGITOS:
            inicio = i
            while i < n and (codigo[i] in DIGITOS or codigo[i] == "."):
                i += 1
            texto = codigo[inicio:i]
            if texto.count(".") > 1:
                raise ErrorLexico(
                    f"número mal formado '{texto}' (más de un punto decimal)", linea, col)
            if texto.endswith("."):
                raise ErrorLexico(
                    f"número mal formado '{texto}' (falta la parte decimal)", linea, col)
            tokens.append(Token("NUMERO", texto, linea, col))
            col += i - inicio
            continue

        # --- Cadenas: "..." sin cruzar líneas --------------------------------
        # Se reporta la posición de la comilla de APERTURA: una cadena que cruza
        # líneas casi siempre es una comilla olvidada.
        if c == '"':
            j = i + 1
            while j < n and codigo[j] != '"' and codigo[j] != "\n" and codigo[j] != "\r":
                j += 1
            if j >= n or codigo[j] != '"':
                raise ErrorLexico("cadena sin cerrar", linea, col)
            texto = codigo[i:j + 1]          # incluye las comillas
            tokens.append(Token("CADENA", texto, linea, col))
            i = j + 1
            col += len(texto)
            continue

        # --- Comparadores (los de dos caracteres primero) --------------------
        # Van antes que el símbolo '=' para que `==` no salga como dos '='.
        encontrado = None
        for simbolo in COMPARADORES:
            if codigo.startswith(simbolo, i):
                encontrado = simbolo
                break
        if encontrado:
            tokens.append(Token("COMPARADOR", encontrado, linea, col))
            i += len(encontrado)
            col += len(encontrado)
            continue

        # --- Operadores lógicos && y || ---------------------------------------
        encontrado = None
        for simbolo in OPERADORES_LOGICOS:
            if codigo.startswith(simbolo, i):
                encontrado = simbolo
                break
        if encontrado:
            tokens.append(Token("OPERADOR_LOGICO", encontrado, linea, col))
            i += 2
            col += 2
            continue

        # `&` y `|` solos no existen: el mensaje útil es "te faltó el segundo".
        if c == "&" or c == "|":
            raise ErrorLexico(f"operador incompleto, se esperaba '{c}{c}'", linea, col)

        # --- Operadores aritméticos y símbolos de un carácter -----------------
        if c in OPERADORES:
            tokens.append(Token("OPERADOR", c, linea, col))
            i += 1
            col += 1
            continue

        if c in SIMBOLOS:
            tokens.append(Token("SIMBOLO", c, linea, col))
            i += 1
            col += 1
            continue

        # --- Nada coincidió: carácter desconocido (incluye '!' suelto) --------
        raise ErrorLexico(f"carácter '{c}' no reconocido", linea, col)

    # Token final: el parser lo necesita para saber cuándo parar.
    tokens.append(Token("EOF", "", linea, col))
    return tokens
