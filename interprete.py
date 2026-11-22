"""
interprete.py - Intérprete (evaluador del AST) de RPG-CORE (RPG-C).

Dos clases:
  * `Entorno`: tabla de variables de UN bloque, con referencia a su `padre`.
    Encadenados forman el alcance léxico: al abrir un bloque `{ }` se crea un
    entorno nuevo cuyo padre es el actual, y al cerrarlo se vuelve al padre.
  * `Interprete`: recorre el árbol con dos métodos:
        ejecutar(nodo)  -> instrucciones (declarar, asignar, mostrar...). No devuelve nada.
        evaluar(nodo)   -> expresiones. Devuelve un valor de Python.

Representación de valores:  INT -> int, FLOAT -> float, STRING -> str,
BOOL -> bool, HERB_STATUS -> str ("FINE" | "POISON" | "DEAD").

La validación de tipos usa `type(valor)` y NO `isinstance`, porque en Python
`True` cuenta como entero (`isinstance(True, int)` es True) y un BOOL se
colaría en una variable INT.
"""

from tokens import ErrorSemantico
from arbol import (
    Programa, Declaracion, Asignacion, Mostrar, Discard, Si, Mientras,
    OperacionBinaria, OperacionUnaria, Numero, Cadena, Booleano, EstadoHerb,
    Variable,
)

# Qué tipos de Python acepta cada tipo de RPG-C.
ACEPTA = {
    "INT": (int,),
    "FLOAT": (int, float),        # un int se convierte a float al guardarse
    "STRING": (str,),
    "BOOL": (bool,),
    "HERB_STATUS": (str,),        # además debe ser FINE, POISON o DEAD
}
ESTADOS_VALIDOS = ("FINE", "POISON", "DEAD")

# Nombre en RPG-C de cada tipo de Python (para los mensajes de error).
NOMBRE_TIPO = {int: "INT", float: "FLOAT", str: "STRING", bool: "BOOL"}

LIMITE_VUELTAS = 100_000          # protección contra CYCLE_TURN infinitos


def nombre_tipo(valor):
    """Nombre RPG-C del tipo de un valor de Python."""
    return NOMBRE_TIPO.get(type(valor), type(valor).__name__)


def es_numero(valor):
    """True solo para INT y FLOAT (excluye bool, aunque en Python sea int)."""
    return type(valor) in (int, float)


def formatear(valor):
    """Cómo se imprime un valor con MOSTRAR: los booleanos en minúscula."""
    if type(valor) is bool:
        return "true" if valor else "false"
    return str(valor)


# ---------------------------------------------------------------------------
# Entorno (alcance léxico anidado)
# ---------------------------------------------------------------------------
class Entorno:
    """Variables de un bloque. Cada entrada guarda tipo, valor, línea y si es constante."""

    def __init__(self, padre=None):
        self.variables = {}
        self.padre = padre

    def definir(self, nombre, tipo, valor, linea, constante=False):
        """Crea la variable en ESTE entorno."""
        self.variables[nombre] = {
            "tipo": tipo, "valor": valor, "linea": linea, "constante": constante,
        }

    def existe_local(self, nombre):
        """¿Está declarada en este mismo entorno (sin mirar a los padres)?"""
        return nombre in self.variables

    def propietario(self, nombre):
        """Entorno (este o un ancestro) que contiene la variable, o None."""
        entorno = self
        while entorno is not None:
            if nombre in entorno.variables:
                return entorno
            entorno = entorno.padre
        return None

    def buscar(self, nombre):
        """Entrada de la variable buscando hacia arriba, o None si no existe."""
        dueño = self.propietario(nombre)
        return dueño.variables[nombre] if dueño else None

    def eliminar(self, nombre):
        """Quita la variable del entorno donde fue declarada (DISCARD)."""
        dueño = self.propietario(nombre)
        if dueño is not None:
            del dueño.variables[nombre]


# ---------------------------------------------------------------------------
# Intérprete
# ---------------------------------------------------------------------------
class Interprete:
    """Ejecuta un AST. Si se le pasa un `Entorno`, lo reutiliza (modo interactivo)."""

    def __init__(self, entorno=None):
        self.global_ = entorno if entorno is not None else Entorno()
        self.entorno = self.global_

    # -- Instrucciones -------------------------------------------------------
    def ejecutar_programa(self, programa):
        self.entorno = self.global_
        for instruccion in programa.instrucciones:
            self.ejecutar(instruccion)

    def ejecutar_bloque(self, instrucciones):
        """Ejecuta una lista de instrucciones en un entorno hijo del actual."""
        anterior = self.entorno
        self.entorno = Entorno(anterior)
        try:
            for instruccion in instrucciones:
                self.ejecutar(instruccion)
        finally:
            self.entorno = anterior          # también si hubo un error

    def ejecutar(self, nodo):
        if isinstance(nodo, Declaracion):
            self._declarar(nodo)

        elif isinstance(nodo, Asignacion):
            self._asignar(nodo)

        elif isinstance(nodo, Mostrar):
            print(formatear(self.evaluar(nodo.valor)))

        elif isinstance(nodo, Discard):
            nombre = nodo.nombre
            if self.entorno.buscar(nombre.texto) is None:
                raise ErrorSemantico(
                    f"la variable '{nombre.texto}' no ha sido declarada",
                    nombre.linea, nombre.columna)
            self.entorno.eliminar(nombre.texto)

        elif isinstance(nodo, Si):
            if self._condicion(nodo.condicion, nodo.palabra):
                self.ejecutar_bloque(nodo.entonces)
            elif nodo.sino is not None:
                self.ejecutar_bloque(nodo.sino)

        elif isinstance(nodo, Mientras):
            vueltas = 0
            while self._condicion(nodo.condicion, nodo.palabra):
                vueltas += 1
                if vueltas > LIMITE_VUELTAS:
                    raise ErrorSemantico(
                        f"el ciclo superó {LIMITE_VUELTAS} vueltas; "
                        "¿falta actualizar la variable de la condición?",
                        nodo.palabra.linea, nodo.palabra.columna)
                self.ejecutar_bloque(nodo.cuerpo)

        else:
            raise ErrorSemantico(f"instrucción desconocida: {nodo!r}", 0, 0)

    def _declarar(self, nodo):
        nombre = nodo.nombre
        # Solo se revisa el entorno ACTUAL: un bloque puede "sombrear" un nombre de afuera.
        if self.entorno.existe_local(nombre.texto):
            previa = self.entorno.variables[nombre.texto]["linea"]
            raise ErrorSemantico(
                f"la variable '{nombre.texto}' ya fue declarada en la línea {previa}",
                nombre.linea, nombre.columna)
        valor = self._validar_tipo(nodo.tipo.texto, self.evaluar(nodo.valor), nombre)
        self.entorno.definir(nombre.texto, nodo.tipo.texto, valor,
                             nombre.linea, nodo.es_constante)

    def _asignar(self, nodo):
        nombre = nodo.nombre
        entrada = self.entorno.buscar(nombre.texto)
        if entrada is None:
            raise ErrorSemantico(
                f"la variable '{nombre.texto}' no ha sido declarada",
                nombre.linea, nombre.columna)
        if entrada["constante"]:
            raise ErrorSemantico(
                f"no se puede reasignar '{nombre.texto}': fue declarada con EQUIPPED (constante)",
                nombre.linea, nombre.columna)
        entrada["valor"] = self._validar_tipo(
            entrada["tipo"], self.evaluar(nodo.valor), nombre)

    def _validar_tipo(self, tipo, valor, token):
        """Comprueba que `valor` cabe en una variable de `tipo` y lo devuelve
        (convirtiendo int a float si la variable es FLOAT)."""
        if type(valor) not in ACEPTA[tipo]:
            raise ErrorSemantico(
                f"no se puede guardar un {nombre_tipo(valor)} en la variable "
                f"'{token.texto}' de tipo {tipo}", token.linea, token.columna)
        if tipo == "HERB_STATUS" and valor not in ESTADOS_VALIDOS:
            raise ErrorSemantico(
                f"'{valor}' no es un estado válido para la variable '{token.texto}' "
                f"de tipo HERB_STATUS (use FINE, POISON o DEAD)", token.linea, token.columna)
        if tipo == "FLOAT" and type(valor) is int:
            return float(valor)
        return valor

    def _condicion(self, nodo, palabra):
        """Evalúa una condición de SI / CYCLE_TURN, que debe dar BOOL."""
        valor = self.evaluar(nodo)
        if type(valor) is not bool:
            raise ErrorSemantico(
                f"la condición debe ser BOOL y se obtuvo {nombre_tipo(valor)}",
                palabra.linea, palabra.columna)
        return valor

    # -- Expresiones -----------------------------------------------------------
    def evaluar(self, nodo):
        if isinstance(nodo, Numero):
            texto = nodo.token.texto
            return float(texto) if "." in texto else int(texto)

        if isinstance(nodo, Cadena):
            return nodo.token.texto[1:-1]            # quita las comillas

        if isinstance(nodo, Booleano):
            return nodo.token.texto == "true"

        if isinstance(nodo, EstadoHerb):
            return nodo.token.texto

        if isinstance(nodo, Variable):
            entrada = self.entorno.buscar(nodo.token.texto)
            if entrada is None:
                raise ErrorSemantico(
                    f"la variable '{nodo.token.texto}' no ha sido declarada",
                    nodo.token.linea, nodo.token.columna)
            return entrada["valor"]

        if isinstance(nodo, OperacionUnaria):
            return self._unaria(nodo)

        if isinstance(nodo, OperacionBinaria):
            op = nodo.operador
            if op.tipo == "OPERADOR_LOGICO":
                return self._logica(nodo)
            izq = self.evaluar(nodo.izq)
            der = self.evaluar(nodo.der)
            if op.tipo == "COMPARADOR":
                return self.comparar(izq, op, der)
            return self.operar(izq, op, der)

        raise ErrorSemantico(f"expresión desconocida: {nodo!r}", 0, 0)

    def _unaria(self, nodo):
        op = nodo.operador
        valor = self.evaluar(nodo.operando)
        if op.texto == "-":
            if not es_numero(valor):
                raise ErrorSemantico(
                    f"el operador '-' solo opera con números, no con {nombre_tipo(valor)}",
                    op.linea, op.columna)
            return -valor
        # 'NO'
        if type(valor) is not bool:
            raise ErrorSemantico(
                f"el operador 'NO' solo opera con BOOL, no con {nombre_tipo(valor)}",
                op.linea, op.columna)
        return not valor

    def _logica(self, nodo):
        """&& y || con evaluación en cortocircuito; ambos lados deben ser BOOL."""
        op = nodo.operador
        izq = self.evaluar(nodo.izq)
        self._exigir_bool(izq, op)
        if op.texto == "&&" and not izq:
            return False                              # el lado derecho no se evalúa
        if op.texto == "||" and izq:
            return True
        der = self.evaluar(nodo.der)
        self._exigir_bool(der, op)
        return der

    @staticmethod
    def _exigir_bool(valor, op):
        if type(valor) is not bool:
            raise ErrorSemantico(
                f"el operador '{op.texto}' solo opera con BOOL, no con {nombre_tipo(valor)}",
                op.linea, op.columna)

    def comparar(self, izq, operador, der):
        """==, != entre tipos compatibles; <, >, <=, >= solo entre números."""
        op = operador.texto
        ambos_num = es_numero(izq) and es_numero(der)
        mismo_tipo = type(izq) is type(der) and type(izq) in (str, bool)

        if op in ("==", "!="):
            if not (ambos_num or mismo_tipo):
                raise ErrorSemantico(
                    f"no se puede comparar {nombre_tipo(izq)} con {nombre_tipo(der)} usando '{op}'",
                    operador.linea, operador.columna)
            return izq == der if op == "==" else izq != der

        if not ambos_num:
            raise ErrorSemantico(
                f"el operador '{op}' solo compara números, no {nombre_tipo(izq)} con {nombre_tipo(der)}",
                operador.linea, operador.columna)
        if op == "<":
            return izq < der
        if op == ">":
            return izq > der
        if op == "<=":
            return izq <= der
        return izq >= der                              # '>='

    def operar(self, izq, operador, der):
        """Operaciones aritméticas: + - * /  (ver tabla de reglas en el README)."""
        op = operador.texto
        linea, columna = operador.linea, operador.columna

        # '+' también une dos STRING.
        if op == "+" and type(izq) is str and type(der) is str:
            return izq + der

        if type(izq) is str or type(der) is str:
            if op == "+":
                raise ErrorSemantico(
                    f"no se puede sumar {nombre_tipo(izq)} con {nombre_tipo(der)}: "
                    "solo se pueden unir dos STRING", linea, columna)
            raise ErrorSemantico(f"no se puede usar '{op}' con textos", linea, columna)

        if not (es_numero(izq) and es_numero(der)):
            raise ErrorSemantico(
                f"el operador '{op}' solo opera con números, no con "
                f"{nombre_tipo(izq)} y {nombre_tipo(der)}", linea, columna)

        if op == "+":
            return izq + der                           # int+int=int; si hay float, float
        if op == "-":
            return izq - der
        if op == "*":
            return izq * der
        # '/'
        if der == 0:
            raise ErrorSemantico("división por cero", linea, columna)
        if type(izq) is int and type(der) is int:
            return izq // der                          # división entera
        return izq / der                               # división flotante
