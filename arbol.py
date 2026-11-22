"""
arbol.py - Nodos del Árbol de Sintaxis Abstracta (AST) de RPG-CORE (RPG-C).

Cada tipo de nodo es una clase de datos. Los nodos guardan TOKENS y no solo
textos, para poder dar línea y columna si algo falla durante la ejecución.

  * Hojas (guardan un solo token): Numero, Cadena, Booleano, EstadoHerb, Variable.
  * Nodos con hijos: OperacionBinaria, OperacionUnaria, Declaracion, Asignacion,
    Mostrar, Discard, Si, Mientras.
  * Raíz: Programa.
"""

from dataclasses import dataclass
from tokens import Token


# ---------------------------------------------------------------------------
# Expresiones
# ---------------------------------------------------------------------------
@dataclass
class Numero:                 # 42, 3.14
    token: Token


@dataclass
class Cadena:                 # "Leon" (el token conserva las comillas)
    token: Token


@dataclass
class Booleano:               # true, false
    token: Token


@dataclass
class EstadoHerb:             # FINE, POISON, DEAD
    token: Token


@dataclass
class Variable:               # un nombre usado en una expresión: hp
    token: Token


@dataclass
class OperacionBinaria:       # a + b, a >= b, a && b
    izq: object
    operador: Token
    der: object


@dataclass
class OperacionUnaria:        # -x, NO activo
    operador: Token
    operando: object


# ---------------------------------------------------------------------------
# Instrucciones
# ---------------------------------------------------------------------------
@dataclass
class Declaracion:            # INVENTORY_SLOT INT hp = 100;   |   EQUIPPED ...
    tipo: Token
    nombre: Token
    valor: object
    es_constante: bool = False


@dataclass
class Asignacion:             # hp = hp - 10;
    nombre: Token
    valor: object


@dataclass
class Mostrar:                # MOSTRAR(hp);
    palabra: Token
    valor: object


@dataclass
class Discard:                # DISCARD(hp);
    palabra: Token
    nombre: Token


@dataclass
class Si:                     # SI cond ENTONCES { ... } SINO { ... }
    palabra: Token
    condicion: object
    entonces: list
    sino: list | None = None  # None si no hay SINO


@dataclass
class Mientras:               # CYCLE_TURN (cond) { ... }
    palabra: Token
    condicion: object
    cuerpo: list


@dataclass
class Programa:               # todas las instrucciones del archivo
    instrucciones: list


# ---------------------------------------------------------------------------
# Impresión visual del árbol
# ---------------------------------------------------------------------------
def mostrar_arbol(nodo, nivel=0):
    """Imprime el AST indentado (2 espacios por nivel)."""
    sangria = "  " * nivel

    def rotulo(texto, hijos):
        """Imprime una etiqueta ('Condicion', 'Entonces'...) y sus hijos."""
        print(f"{sangria}  {texto}")
        for hijo in hijos:
            mostrar_arbol(hijo, nivel + 2)

    if isinstance(nodo, Programa):
        print(f"{sangria}Programa")
        for instruccion in nodo.instrucciones:
            mostrar_arbol(instruccion, nivel + 1)

    elif isinstance(nodo, Declaracion):
        marca = " (EQUIPPED)" if nodo.es_constante else ""
        print(f"{sangria}Declaracion {nodo.tipo.texto} {nodo.nombre.texto}{marca}")
        mostrar_arbol(nodo.valor, nivel + 1)

    elif isinstance(nodo, Asignacion):
        print(f"{sangria}Asignacion {nodo.nombre.texto}")
        mostrar_arbol(nodo.valor, nivel + 1)

    elif isinstance(nodo, Mostrar):
        print(f"{sangria}Mostrar")
        mostrar_arbol(nodo.valor, nivel + 1)

    elif isinstance(nodo, Discard):
        print(f"{sangria}Discard {nodo.nombre.texto}")

    elif isinstance(nodo, Si):
        print(f"{sangria}Si")
        rotulo("Condicion", [nodo.condicion])
        rotulo("Entonces", nodo.entonces)
        if nodo.sino is not None:
            rotulo("Sino", nodo.sino)

    elif isinstance(nodo, Mientras):
        print(f"{sangria}Mientras")
        rotulo("Condicion", [nodo.condicion])
        rotulo("Cuerpo", nodo.cuerpo)

    elif isinstance(nodo, OperacionBinaria):
        print(f"{sangria}OperacionBinaria {nodo.operador.texto}")
        mostrar_arbol(nodo.izq, nivel + 1)
        mostrar_arbol(nodo.der, nivel + 1)

    elif isinstance(nodo, OperacionUnaria):
        print(f"{sangria}OperacionUnaria {nodo.operador.texto}")
        mostrar_arbol(nodo.operando, nivel + 1)

    elif isinstance(nodo, Numero):
        print(f"{sangria}Numero {nodo.token.texto}")
    elif isinstance(nodo, Cadena):
        print(f"{sangria}Cadena {nodo.token.texto}")
    elif isinstance(nodo, Booleano):
        print(f"{sangria}Booleano {nodo.token.texto}")
    elif isinstance(nodo, EstadoHerb):
        print(f"{sangria}EstadoHerb {nodo.token.texto}")
    elif isinstance(nodo, Variable):
        print(f"{sangria}Variable {nodo.token.texto}")

    else:
        print(f"{sangria}{nodo!r}")
