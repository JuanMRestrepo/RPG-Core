"""
parser.py - Analizador sintáctico de RPG-CORE (RPG-C) por descenso recursivo.

Gramática completa (EBNF)
-------------------------
Convenciones: '::=' "está formado por", '|' "o", '*' "cero o más veces",
'?' "cero o una vez". Lo que va entre comillas es un token exacto; lo que va en
MAYÚSCULAS es un tipo de token.

  programa         ::= instruccion* EOF
  instruccion      ::= declaracion | asignacion | salida | descarte
                     | condicional | ciclo

  declaracion      ::= 'EQUIPPED'? 'INVENTORY_SLOT' TIPO IDENTIFICADOR '='
                       expresion_logica ';'
  asignacion       ::= IDENTIFICADOR '=' expresion_logica ';'
  salida           ::= 'MOSTRAR' '(' expresion_logica ')' ';'
  descarte         ::= 'DISCARD' '(' IDENTIFICADOR ')' ';'
  condicional      ::= 'SI' expresion_logica 'ENTONCES' bloque
                       ( 'SINO' ( bloque | condicional ) )?
  ciclo            ::= 'CYCLE_TURN' '(' expresion_logica ')' bloque
  bloque           ::= '{' instruccion* '}'

  expresion_logica ::= termino_logico ( '||' termino_logico )*
  termino_logico   ::= factor_logico ( '&&' factor_logico )*
  factor_logico    ::= 'NO' factor_logico | comparacion
  comparacion      ::= expresion ( COMPARADOR expresion )*
  expresion        ::= termino ( ( '+' | '-' ) termino )*
  termino          ::= factor ( ( '*' | '/' ) factor )*
  factor           ::= '-' factor | NUMERO | CADENA | BOOLEANO | VALOR_ESTADO
                     | IDENTIFICADOR | '(' expresion_logica ')'

  TIPO        ::= 'INT' | 'FLOAT' | 'STRING' | 'BOOL' | 'HERB_STATUS'
  COMPARADOR  ::= '==' | '!=' | '>=' | '<=' | '>' | '<'
  BOOLEANO    ::= 'true' | 'false'
  VALOR_ESTADO::= 'FINE' | 'POISON' | 'DEAD'

Precedencia (de menor a mayor): ||  <  &&  <  NO  <  comparadores  <  + -  <  * /
<  menos unario. Cada nivel es un método que llama al nivel inmediatamente
inferior, así el árbol queda con lo de mayor precedencia más abajo.

Nota sobre la recursión por la izquierda: las reglas con repetición se escriben
como `termino (op termino)*` y se implementan con un `while`, porque una regla
como `expresion ::= expresion '+' termino` se llamaría a sí misma sin consumir
ningún token y nunca terminaría.
"""

from tokens import ErrorSintactico
from arbol import (
    Programa, Declaracion, Asignacion, Mostrar, Discard, Si, Mientras,
    OperacionBinaria, OperacionUnaria, Numero, Cadena, Booleano, EstadoHerb,
    Variable,
)


class Parser:
    """Convierte la lista de tokens del lexer en un AST.

    `self.tokens` y `self.pos` son compartidos por todos los métodos: la posición
    vive en el objeto (el "dedo" que sigue la lista), no se pasa de una función a otra.
    """

    def __init__(self, tokens):
        self.tokens = tokens
        self.pos = 0

    # ------------------------------------------------------------------
    # Utilidades
    # ------------------------------------------------------------------
    def actual(self):
        """Token en el que va el parser, sin moverse."""
        return self.tokens[self.pos]

    def avanzar(self):
        """Mueve el parser un token y devuelve el token que deja atrás."""
        token = self.tokens[self.pos]
        if token.tipo != "EOF":          # nunca se pasa del EOF final
            self.pos += 1
        return token

    def esperar(self, tipo, texto=None):
        """Consume el token actual si es el que pide la regla; si no, lanza
        ErrorSintactico con la posición del token que SÍ llegó."""
        t = self.actual()
        if t.tipo != tipo or (texto is not None and t.texto != texto):
            quiero = f"'{texto}'" if texto else f"un {tipo}"
            raise ErrorSintactico(
                f"se esperaba {quiero} y llegó {self._describir(t)}", t.linea, t.columna)
        return self.avanzar()

    @staticmethod
    def _describir(token):
        return "el fin del archivo" if token.tipo == "EOF" else f"'{token.texto}'"

    def _es(self, tipo, texto=None):
        """¿El token actual es de este tipo (y texto, si se indica)? No consume."""
        t = self.actual()
        return t.tipo == tipo and (texto is None or t.texto == texto)

    # ------------------------------------------------------------------
    # Instrucciones
    # ------------------------------------------------------------------
    # programa ::= instruccion* EOF
    def programa(self):
        instrucciones = []
        while self.actual().tipo != "EOF":
            instrucciones.append(self.instruccion())
        return Programa(instrucciones)

    # instruccion ::= declaracion | asignacion | salida | descarte | condicional | ciclo
    def instruccion(self):
        t = self.actual()
        if t.tipo == "PALABRA_CLAVE":
            if t.texto in ("INVENTORY_SLOT", "EQUIPPED"):
                return self.declaracion()
            if t.texto == "MOSTRAR":
                return self.salida()
            if t.texto == "DISCARD":
                return self.descarte()
            if t.texto == "SI":
                return self.condicional()
            if t.texto == "CYCLE_TURN":
                return self.ciclo()
        if t.tipo == "IDENTIFICADOR":
            return self.asignacion()
        raise ErrorSintactico(
            f"se esperaba el inicio de una instrucción y llegó {self._describir(t)}",
            t.linea, t.columna)

    # declaracion ::= 'EQUIPPED'? 'INVENTORY_SLOT' TIPO IDENTIFICADOR '=' expresion_logica ';'
    def declaracion(self):
        es_constante = False
        if self._es("PALABRA_CLAVE", "EQUIPPED"):
            self.avanzar()
            es_constante = True
        self.esperar("PALABRA_CLAVE", "INVENTORY_SLOT")
        tipo = self.esperar("TIPO")
        nombre = self.esperar("IDENTIFICADOR")
        self.esperar("SIMBOLO", "=")
        valor = self.expresion_logica()
        self.esperar("SIMBOLO", ";")
        return Declaracion(tipo, nombre, valor, es_constante)

    # asignacion ::= IDENTIFICADOR '=' expresion_logica ';'
    def asignacion(self):
        nombre = self.esperar("IDENTIFICADOR")
        self.esperar("SIMBOLO", "=")
        valor = self.expresion_logica()
        self.esperar("SIMBOLO", ";")
        return Asignacion(nombre, valor)

    # salida ::= 'MOSTRAR' '(' expresion_logica ')' ';'
    def salida(self):
        palabra = self.esperar("PALABRA_CLAVE", "MOSTRAR")
        self.esperar("SIMBOLO", "(")
        valor = self.expresion_logica()
        self.esperar("SIMBOLO", ")")
        self.esperar("SIMBOLO", ";")
        return Mostrar(palabra, valor)

    # descarte ::= 'DISCARD' '(' IDENTIFICADOR ')' ';'
    def descarte(self):
        palabra = self.esperar("PALABRA_CLAVE", "DISCARD")
        self.esperar("SIMBOLO", "(")
        nombre = self.esperar("IDENTIFICADOR")
        self.esperar("SIMBOLO", ")")
        self.esperar("SIMBOLO", ";")
        return Discard(palabra, nombre)

    # condicional ::= 'SI' expresion_logica 'ENTONCES' bloque ( 'SINO' ( bloque | condicional ) )?
    def condicional(self):
        palabra = self.esperar("PALABRA_CLAVE", "SI")
        condicion = self.expresion_logica()
        self.esperar("PALABRA_CLAVE", "ENTONCES")
        entonces = self.bloque()
        sino = None
        # El SINO se pregunta con _es() y no con esperar(), porque puede no estar.
        if self._es("PALABRA_CLAVE", "SINO"):
            self.avanzar()
            if self._es("PALABRA_CLAVE", "SI"):
                sino = [self.condicional()]      # SINO SI ... (cadena de condiciones)
            else:
                sino = self.bloque()
        return Si(palabra, condicion, entonces, sino)

    # ciclo ::= 'CYCLE_TURN' '(' expresion_logica ')' bloque
    def ciclo(self):
        palabra = self.esperar("PALABRA_CLAVE", "CYCLE_TURN")
        self.esperar("SIMBOLO", "(")
        condicion = self.expresion_logica()
        self.esperar("SIMBOLO", ")")
        cuerpo = self.bloque()
        return Mientras(palabra, condicion, cuerpo)

    # bloque ::= '{' instruccion* '}'
    def bloque(self):
        llave = self.esperar("SIMBOLO", "{")      # se guarda para decir dónde se abrió
        instrucciones = []
        while not self._es("SIMBOLO", "}"):
            if self.actual().tipo == "EOF":
                t = self.actual()
                raise ErrorSintactico(
                    f"falta '}}' para cerrar el bloque abierto en la línea {llave.linea}",
                    t.linea, t.columna)
            instrucciones.append(self.instruccion())
        self.avanzar()                            # '}'
        return instrucciones

    # ------------------------------------------------------------------
    # Expresiones (de menor a mayor precedencia)
    # ------------------------------------------------------------------
    # expresion_logica ::= termino_logico ( '||' termino_logico )*
    def expresion_logica(self):
        izq = self.termino_logico()
        while self._es("OPERADOR_LOGICO", "||"):
            operador = self.avanzar()
            der = self.termino_logico()
            izq = OperacionBinaria(izq, operador, der)
        return izq

    # termino_logico ::= factor_logico ( '&&' factor_logico )*
    def termino_logico(self):
        izq = self.factor_logico()
        while self._es("OPERADOR_LOGICO", "&&"):
            operador = self.avanzar()
            der = self.factor_logico()
            izq = OperacionBinaria(izq, operador, der)
        return izq

    # factor_logico ::= 'NO' factor_logico | comparacion
    def factor_logico(self):
        if self._es("PALABRA_CLAVE", "NO"):
            operador = self.avanzar()
            return OperacionUnaria(operador, self.factor_logico())
        return self.comparacion()

    # comparacion ::= expresion ( COMPARADOR expresion )*
    def comparacion(self):
        izq = self.expresion()
        while self.actual().tipo == "COMPARADOR":
            operador = self.avanzar()
            der = self.expresion()
            izq = OperacionBinaria(izq, operador, der)
        return izq

    # expresion ::= termino ( ( '+' | '-' ) termino )*
    def expresion(self):
        izq = self.termino()
        while self.actual().tipo == "OPERADOR" and self.actual().texto in ("+", "-"):
            operador = self.avanzar()
            der = self.termino()
            izq = OperacionBinaria(izq, operador, der)
        return izq

    # termino ::= factor ( ( '*' | '/' ) factor )*
    def termino(self):
        izq = self.factor()
        while self.actual().tipo == "OPERADOR" and self.actual().texto in ("*", "/"):
            operador = self.avanzar()
            der = self.factor()
            izq = OperacionBinaria(izq, operador, der)
        return izq

    # factor ::= '-' factor | NUMERO | CADENA | BOOLEANO | VALOR_ESTADO
    #          | IDENTIFICADOR | '(' expresion_logica ')'
    def factor(self):
        t = self.actual()
        if t.tipo == "OPERADOR" and t.texto == "-":
            operador = self.avanzar()
            return OperacionUnaria(operador, self.factor())
        if t.tipo == "NUMERO":
            return Numero(self.avanzar())
        if t.tipo == "CADENA":
            return Cadena(self.avanzar())
        if t.tipo == "BOOLEANO":
            return Booleano(self.avanzar())
        if t.tipo == "VALOR_ESTADO":
            return EstadoHerb(self.avanzar())
        if t.tipo == "IDENTIFICADOR":
            return Variable(self.avanzar())
        if t.tipo == "SIMBOLO" and t.texto == "(":
            self.avanzar()                        # '('
            dentro = self.expresion_logica()
            self.esperar("SIMBOLO", ")")
            return dentro                         # los paréntesis no generan nodo
        raise ErrorSintactico(
            f"se esperaba un número, una variable o '(' y llegó {self._describir(t)}",
            t.linea, t.columna)
