"""
main.py - Punto de entrada de RPG-CORE (RPG-C).

Uso:
    python main.py programa.rpgc            ejecuta el archivo (lexer -> parser -> intérprete)
    python main.py                          abre el modo interactivo (REPL)
    python main.py --tokens programa.rpgc   solo muestra los tokens
    python main.py --arbol programa.rpgc    solo muestra el AST (sin ejecutar)

Ante cualquier ErrorDeLenguaje (léxico, sintáctico o semántico) se imprime el
mensaje, la línea del código donde ocurrió y un '^' alineado bajo la columna.
"""

import sys

from tokens import ErrorDeLenguaje
from lexer import tokenizar
from parser import Parser
from arbol import mostrar_arbol
from interprete import Interprete


def imprimir_error(error, lineas):
    """Muestra el mensaje, la línea del código fuente y un ^ bajo la columna.

    `lineas` es el código partido en líneas. Si el error cae después de la última
    línea (por ejemplo, un EOF tras un salto de línea final) se imprime vacía.
    """
    print(error)
    texto = lineas[error.linea - 1] if 1 <= error.linea <= len(lineas) else ""
    # Los tabuladores se conservan en el prefijo para que el ^ quede alineado.
    prefijo = "".join("\t" if ch == "\t" else " " for ch in texto[:error.columna - 1])
    faltan = (error.columna - 1) - len(prefijo)       # error más allá del final de la línea
    print("    " + texto)
    print("    " + prefijo + " " * max(0, faltan) + "^")


def ejecutar_archivo(ruta, solo_tokens=False, solo_arbol=False):
    """Lee, analiza y ejecuta un archivo .rpgc. Devuelve el código de salida."""
    try:
        with open(ruta, encoding="utf-8-sig") as archivo:
            codigo = archivo.read()
    except (OSError, UnicodeDecodeError) as e:
        print(f"No se pudo leer el archivo '{ruta}': {e}")
        return 1

    lineas = codigo.splitlines()
    try:
        tokens = tokenizar(codigo)
        if solo_tokens:
            for token in tokens:
                print(token)
            return 0
        programa = Parser(tokens).programa()
        if solo_arbol:
            mostrar_arbol(programa)
            return 0
        Interprete().ejecutar_programa(programa)
    except ErrorDeLenguaje as e:
        imprimir_error(e, lineas)
        return 1
    return 0


def llaves_abiertas(tokens):
    """¿Hay más '{' que '}'? Sirve para pedir más líneas en el REPL."""
    abiertas = sum(1 for t in tokens if t.tipo == "SIMBOLO" and t.texto == "{")
    cerradas = sum(1 for t in tokens if t.tipo == "SIMBOLO" and t.texto == "}")
    return abiertas > cerradas


def modo_interactivo():
    """REPL: ejecuta línea tras línea manteniendo vivo el Entorno hasta 'salir'.

    Un bloque con llaves puede escribirse en varias líneas: mientras falte cerrar
    una '{' el prompt cambia a '... ' y se sigue acumulando el texto.
    """
    print("RPG-CORE (RPG-C) - Modo interactivo. Escribe 'salir' para terminar.")
    interprete = Interprete()          # un solo intérprete: el entorno persiste
    buffer = []

    while True:
        try:
            entrada = input("... " if buffer else "> ")
        except EOFError:               # Ctrl+D / Ctrl+Z
            print()
            break
        except KeyboardInterrupt:      # Ctrl+C cancela lo que se estaba escribiendo
            print()
            buffer = []
            continue

        if not buffer:
            if entrada.strip() == "salir":
                break
            if entrada.strip() == "":
                continue

        buffer.append(entrada)
        codigo = "\n".join(buffer)
        try:
            tokens = tokenizar(codigo)
            if llaves_abiertas(tokens):
                continue               # el bloque sigue abierto: pedir otra línea
            programa = Parser(tokens).programa()
            interprete.ejecutar_programa(programa)
        except ErrorDeLenguaje as e:
            imprimir_error(e, codigo.splitlines())
        buffer = []


def main():
    solo_tokens = solo_arbol = False
    rutas = []
    for argumento in sys.argv[1:]:
        if argumento == "--tokens":
            solo_tokens = True
        elif argumento == "--arbol":
            solo_arbol = True
        else:
            rutas.append(argumento)

    if not rutas:
        modo_interactivo()
        return 0
    return ejecutar_archivo(rutas[0], solo_tokens, solo_arbol)


if __name__ == "__main__":
    try:                                # que ñ y tildes salgan bien en cualquier consola
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, OSError):
        pass
    sys.exit(main())
