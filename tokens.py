"""
tokens.py - Piezas básicas compartidas por todas las fases de RPG-CORE (RPG-C).

Contiene:
  * La clase de datos `Token`, que reemplaza a las tuplas (tipo, texto, linea,
    columna) del primer lexer: ahora cada dato tiene nombre (t.tipo, t.linea...).
  * La jerarquía de errores del lenguaje. Las tres fases (léxica, sintáctica y
    semántica) guardan lo mismo (mensaje, línea y columna), así que comparten una
    clase base y `main.py` puede atrapar cualquiera con un solo `except`.
"""

from dataclasses import dataclass


@dataclass
class Token:
    """Una pieza reconocida por el lexer, con su posición en el código fuente.

    Atributos:
        tipo:    categoría del token (TIPO, PALABRA_CLAVE, NUMERO, EOF...).
        texto:   texto exacto leído del código (las cadenas conservan sus comillas).
        linea:   línea donde empieza (base 1).
        columna: columna donde empieza (base 1).
    """
    tipo: str
    texto: str
    linea: int
    columna: int

    def __str__(self):
        return f"{self.tipo}('{self.texto}') en {self.linea}:{self.columna}"


class ErrorDeLenguaje(Exception):
    """Clase base de todos los errores de RPG-C.

    Cada subclase solo cambia el atributo `fase`, que aparece al inicio del
    mensaje. `linea` y `columna` quedan como atributos para que `main.py` pueda
    señalar el punto exacto del error en el código fuente.
    """
    fase = "Error"

    def __init__(self, mensaje, linea, columna):
        self.mensaje = mensaje
        self.linea = linea
        self.columna = columna
        super().__init__(f"{self.fase} en línea {linea}, columna {columna}: {mensaje}")


class ErrorLexico(ErrorDeLenguaje):
    """Carácter no reconocido, número o cadena mal formados, comentario sin cerrar."""
    fase = "Error léxico"


class ErrorSintactico(ErrorDeLenguaje):
    """Los tokens son válidos, pero no siguen el orden que pide la gramática."""
    fase = "Error sintáctico"


class ErrorSemantico(ErrorDeLenguaje):
    """El programa está bien escrito, pero no tiene sentido al ejecutarlo
    (variable inexistente, tipos incompatibles, división por cero...)."""
    fase = "Error semántico"
