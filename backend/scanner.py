"""Analisador léxico (scanner) para um subconjunto de Python.

Implementação manual, caractere a caractere (sem expressões regulares e sem
bibliotecas externas), para que cada decisão do scanner seja legível e possa
ser explicada ao estudante. Tarefas desta fase:

  * agrupar caracteres em lexemas e classificá-los em tokens;
  * ignorar espaços em branco e comentários (``# ...``);
  * produzir os tokens estruturais de Python (NOVA_LINHA, INDENTACAO,
    DESINDENTACAO e FIM_ARQUIVO), necessários porque a indentação faz parte
    da gramática da linguagem;
  * registrar linha/coluna (base 1, contadas em caracteres) de cada token;
  * acumular erros léxicos e continuar a leitura, para mostrar todos os
    problemas de uma vez.

O scanner NÃO verifica a estrutura do programa (tarefa do parser, Etapa 4):
``x = 10 +* 5`` é tokenizado normalmente.
"""

# --- Categorias de token ----------------------------------------------------
PALAVRA_RESERVADA = "PALAVRA_RESERVADA"
IDENTIFICADOR = "IDENTIFICADOR"
LITERAL_INTEIRO = "LITERAL_INTEIRO"
LITERAL_REAL = "LITERAL_REAL"
LITERAL_STRING = "LITERAL_STRING"
OPERADOR = "OPERADOR"
DELIMITADOR = "DELIMITADOR"
NOVA_LINHA = "NOVA_LINHA"
INDENTACAO = "INDENTACAO"
DESINDENTACAO = "DESINDENTACAO"
FIM_ARQUIVO = "FIM_ARQUIVO"

CATEGORIAS = (
    PALAVRA_RESERVADA, IDENTIFICADOR, LITERAL_INTEIRO, LITERAL_REAL,
    LITERAL_STRING, OPERADOR, DELIMITADOR, NOVA_LINHA, INDENTACAO,
    DESINDENTACAO, FIM_ARQUIVO,
)

# --- Subtipos de erro léxico ------------------------------------------------
ERRO_CARACTERE = "CARACTERE_NAO_RECONHECIDO"
ERRO_FORA_SUBCONJUNTO = "FORA_DO_SUBCONJUNTO"
ERRO_STRING_ABERTA = "STRING_NAO_FECHADA"
ERRO_STRING_TRIPLA = "STRING_TRIPLA"
ERRO_NUMERO = "NUMERO_MALFORMADO"
ERRO_INDENTACAO = "INDENTACAO_INCONSISTENTE"
ERRO_PAREN_ABERTO = "PARENTESE_NAO_FECHADO"
ERRO_PAREN_SOBRA = "PARENTESE_SEM_ABERTURA"
ERRO_BARRA = "BARRA_INVERTIDA_INVALIDA"

# --- Alfabeto do subconjunto ------------------------------------------------
# As 35 palavras reservadas de Python 3.8+ (módulo ``keyword``). Todas são
# reconhecidas como PALAVRA_RESERVADA porque nunca podem ser identificadores;
# o subconjunto *sintático* (Etapa 4) usará apenas parte delas.
PALAVRAS_RESERVADAS = frozenset((
    "False", "None", "True", "and", "as", "assert", "async", "await",
    "break", "class", "continue", "def", "del", "elif", "else", "except",
    "finally", "for", "from", "global", "if", "import", "in", "is",
    "lambda", "nonlocal", "not", "or", "pass", "raise", "return", "try",
    "while", "with", "yield",
))

OPERADORES_3 = ("**=", "//=")
OPERADORES_2 = ("**", "//", "+=", "-=", "*=", "/=", "%=", "==", "!=", "<=", ">=")
OPERADORES_1 = "+-*/%=<>"
DELIMITADORES = "(),:"

# Operadores válidos em Python, mas fora do subconjunto: um único erro por lexema.
OPERADORES_FORA_3 = ("<<=", ">>=")
OPERADORES_FORA_2 = ("<<", ">>", "->", ":=")
# Símbolos válidos em Python, mas fora do subconjunto.
SIMBOLOS_FORA = "[]{};.@|&^~"

TAMANHO_TAB = 8  # como o CPython: a tabulação avança até o próximo múltiplo de 8


def _mostrar(texto):
    """Versão segura para mensagens: escapa caracteres de controle/invisíveis."""
    if texto.isprintable():
        return texto
    return texto.encode("unicode_escape").decode("ascii")


def _digito(c):
    return "0" <= c <= "9"


def _inicio_ident(c):
    return c.isidentifier()  # letra (inclusive acentuada) ou "_"


def _continua_ident(c):
    return ("a" + c).isidentifier()  # letra, dígito ou "_"


class _Scanner:
    def __init__(self, codigo):
        # \r\n e \r viram \n: as colunas não são afetadas (o contador zera a cada quebra)
        self.src = codigo.replace("\r\n", "\n").replace("\r", "\n")
        self.n = len(self.src)
        self.pos = 0
        self.linha = 1
        self.inicio_linha = 0  # índice do primeiro caractere da linha física atual
        self.tokens = []
        self.erros = []
        self.indentacoes = [0]  # pilha de níveis de indentação
        self.parenteses = []  # pilha de ("(", linha, coluna) ainda abertos
        self.inicio_de_instrucao = True  # próximo caractere começa uma linha lógica?

    # ------------------------------------------------------------ utilitários
    def _coluna(self, pos=None):
        return (self.pos if pos is None else pos) - self.inicio_linha + 1

    def _token(self, tipo, lexema, linha, coluna):
        self.tokens.append(
            {"tipo": tipo, "lexema": lexema, "linha": linha, "coluna": coluna}
        )

    def _erro(self, subtipo, lexema, linha, coluna, detalhe):
        self.erros.append({
            "tipo": "ERRO_LEXICO",
            "subtipo": subtipo,
            "lexema": lexema,
            "linha": linha,
            "coluna": coluna,
            "mensagem": "Erro léxico na linha %d, coluna %d: %s" % (linha, coluna, detalhe),
        })

    def _quebra_de_linha_fisica(self):
        """Chamado logo após consumir um '\\n' (pos já aponta para a linha seguinte)."""
        self.linha += 1
        self.inicio_linha = self.pos

    def _avancar_ate(self, destino):
        """Avança pos até ``destino`` mantendo linha/coluna corretas."""
        ultima = self.src.rfind("\n", self.pos, destino)
        if ultima != -1:
            self.linha += self.src.count("\n", self.pos, destino)
            self.inicio_linha = ultima + 1
        self.pos = destino

    # --------------------------------------------------------------- principal
    def executar(self):
        while self.pos < self.n:
            if self.inicio_de_instrucao and not self.parenteses:
                self._indentacao()
            else:
                self._proximo()
        self._finalizar()
        self.erros.sort(key=lambda e: (e["linha"], e["coluna"]))
        return self.tokens, self.erros

    def _indentacao(self):
        """Mede a indentação no início de uma linha lógica e gera INDENT/DEDENT."""
        i, largura = self.pos, 0
        while i < self.n and self.src[i] in " \t\f":
            c = self.src[i]
            if c == " ":
                largura += 1
            elif c == "\t":
                largura = (largura // TAMANHO_TAB + 1) * TAMANHO_TAB
            else:  # \f reinicia a contagem
                largura = 0
            i += 1

        if i >= self.n:  # só espaços até o fim do código
            self.pos = i
            return
        c = self.src[i]
        if c == "\n":  # linha em branco: não altera a indentação
            self.pos = i + 1
            self._quebra_de_linha_fisica()
            return
        if c == "#":  # linha só com comentário: idem
            fim = self.src.find("\n", i)
            if fim == -1:
                self.pos = self.n
            else:
                self.pos = fim + 1
                self._quebra_de_linha_fisica()
            return

        espacos = self.src[self.pos:i]
        coluna = i - self.inicio_linha + 1
        if largura > self.indentacoes[-1]:
            self.indentacoes.append(largura)
            self._token(INDENTACAO, espacos, self.linha, 1)
        elif largura < self.indentacoes[-1]:
            while largura < self.indentacoes[-1]:
                self.indentacoes.pop()
                self._token(DESINDENTACAO, "", self.linha, coluna)
            if largura != self.indentacoes[-1]:
                self._erro(
                    ERRO_INDENTACAO, espacos, self.linha, 1,
                    "indentação inconsistente. Esta linha volta para um nível de "
                    "recuo que não corresponde a nenhum bloco aberto. "
                    "Use sempre a mesma quantidade de espaços em cada bloco.",
                )
                self.indentacoes.append(largura)  # evita erros em cascata
        self.pos = i
        self.inicio_de_instrucao = False

    def _proximo(self):
        src, c = self.src, self.src[self.pos]

        if c in " \t\f":
            self.pos += 1
        elif c == "\n":
            if self.parenteses:  # dentro de ( ) a quebra é ignorada
                self.pos += 1
                self._quebra_de_linha_fisica()
            else:
                self._token(NOVA_LINHA, "\n", self.linha, self._coluna())
                self.pos += 1
                self._quebra_de_linha_fisica()
                self.inicio_de_instrucao = True
        elif c == "#":
            fim = src.find("\n", self.pos)
            self.pos = self.n if fim == -1 else fim
        elif c == "\\":
            self._barra_invertida()
        elif _inicio_ident(c):
            self._identificador()
        elif _digito(c):
            self._numero()
        elif c in "\"'":
            self._string()
        elif c == "." and self.pos + 1 < self.n and _digito(src[self.pos + 1]):
            fim = self.pos + 1
            while fim < self.n and _digito(src[fim]):
                fim += 1
            lex = src[self.pos:fim]
            self._erro(
                ERRO_NUMERO, lex, self.linha, self._coluna(),
                "literal real '%s' sem parte inteira não é suportado. Escreva 0%s." % (lex, lex),
            )
            self.pos = fim
        else:
            self._simbolo(c)

    # --------------------------------------------------------------- lexemas
    def _barra_invertida(self):
        l, c = self.linha, self._coluna()
        if self.pos + 1 < self.n and self.src[self.pos + 1] == "\n":
            self.pos += 2  # continuação de linha: a instrução segue na linha seguinte
            self._quebra_de_linha_fisica()
            return
        if self.pos + 1 >= self.n:
            detalhe = "a barra invertida '\\' no fim do código não continua nenhuma linha."
        else:
            detalhe = ("barra invertida '\\' inesperada. Ela só pode aparecer dentro de "
                       "strings ou no fim de uma linha, para continuar a instrução.")
        self._erro(ERRO_BARRA, "\\", l, c, detalhe)
        self.pos += 1

    def _identificador(self):
        fim = self.pos + 1
        while fim < self.n and _continua_ident(self.src[fim]):
            fim += 1
        lex = self.src[self.pos:fim]
        tipo = PALAVRA_RESERVADA if lex in PALAVRAS_RESERVADAS else IDENTIFICADOR
        self._token(tipo, lex, self.linha, self._coluna())
        self.pos = fim

    def _consumir_resto_numerico(self, fim):
        """Estende ``fim`` sobre letras/dígitos/_ (e pontos seguidos de ident) colados ao número."""
        s = self.src
        while fim < self.n:
            if _continua_ident(s[fim]) or (
                s[fim] == "." and fim + 1 < self.n and _continua_ident(s[fim + 1])
            ):
                fim += 1
            else:
                break
        return fim

    def _numero_malformado(self, fim, detalhe):
        lex = self.src[self.pos:fim]
        self._erro(ERRO_NUMERO, lex, self.linha, self._coluna(),
                   "literal numérico malformado '%s': %s" % (_mostrar(lex), detalhe))
        self.pos = fim

    def _numero(self):
        s, i = self.src, self.pos
        while i < self.n and _digito(s[i]):
            i += 1

        if i < self.n and s[i] == ".":
            if i + 1 < self.n and _digito(s[i + 1]):
                j = i + 1
                while j < self.n and _digito(s[j]):
                    j += 1
                if j < self.n and (_continua_ident(s[j]) or (
                        s[j] == "." and j + 1 < self.n and _digito(s[j + 1]))):
                    fim = self._consumir_resto_numerico(j)
                    lex = s[self.pos:fim]
                    if lex.count(".") > 1:
                        det = "um número real só pode ter um ponto decimal."
                    else:
                        det = ("um número não pode ter letras coladas. Notação científica e "
                               "sufixos não fazem parte do subconjunto.")
                    self._numero_malformado(fim, det)
                else:
                    self._token(LITERAL_REAL, s[self.pos:j], self.linha, self._coluna())
                    self.pos = j
            else:  # "5." sem dígitos depois do ponto
                self._numero_malformado(
                    i + 1, "faltam dígitos depois do ponto. Escreva, por exemplo, %s.0." % s[self.pos:i])
        elif i < self.n and _continua_ident(s[i]):
            fim = self._consumir_resto_numerico(i)
            self._numero_malformado(
                fim, "identificadores não podem começar com dígito, e sufixos, "
                     "hexadecimal e notação científica não fazem parte do subconjunto.")
        else:
            lex = s[self.pos:i]
            if len(lex) > 1 and lex[0] == "0" and lex.strip("0"):
                self._erro(ERRO_NUMERO, lex, self.linha, self._coluna(),
                           "o inteiro '%s' tem zeros à esquerda, o que não é permitido em "
                           "Python 3. Escreva %s." % (lex, lex.lstrip("0")))
            else:
                self._token(LITERAL_INTEIRO, lex, self.linha, self._coluna())
            self.pos = i

    def _string(self):
        s, aspas = self.src, self.src[self.pos]
        l, c = self.linha, self._coluna()

        if s.startswith(aspas * 3, self.pos):
            fim = s.find(aspas * 3, self.pos + 3)
            self._erro(
                ERRO_STRING_TRIPLA, aspas * 3, l, c,
                "strings de aspas triplas (%s) não fazem parte do subconjunto. "
                "O trecho até o fechamento foi ignorado." % (aspas * 3))
            self._avancar_ate(self.n if fim == -1 else fim + 3)
            return

        i = self.pos + 1
        while i < self.n:
            ch = s[i]
            if ch == aspas:
                self._token(LITERAL_STRING, s[self.pos:i + 1], l, c)
                self.pos = i + 1
                return
            if ch == "\n":
                break
            if ch == "\\" and i + 1 < self.n and s[i + 1] != "\n":
                i += 2  # sequência de escape: o caractere seguinte não fecha a string
                continue
            i += 1

        fim = s.find("\n", self.pos)
        fim = self.n if fim == -1 else fim
        lex = s[self.pos:fim]
        self._erro(
            ERRO_STRING_ABERTA, lex, l, c,
            "string não fechada. Faltou a aspa de fechamento (%s) antes do fim da linha." % aspas)
        self.pos = fim

    def _simbolo(self, c):
        s, p = self.src, self.pos
        l, col = self.linha, self._coluna()
        tres, dois = s[p:p + 3], s[p:p + 2]

        if tres in OPERADORES_FORA_3 or dois in OPERADORES_FORA_2:
            lex = tres if tres in OPERADORES_FORA_3 else dois
            self._erro(ERRO_FORA_SUBCONJUNTO, lex, l, col,
                       "o operador '%s' é válido em Python, mas não faz parte do "
                       "subconjunto suportado." % lex)
            self.pos += len(lex)
        elif tres in OPERADORES_3:
            self._token(OPERADOR, tres, l, col)
            self.pos += 3
        elif dois in OPERADORES_2:
            self._token(OPERADOR, dois, l, col)
            self.pos += 2
        elif c in OPERADORES_1:
            self._token(OPERADOR, c, l, col)
            self.pos += 1
        elif c == "(":
            self.parenteses.append((c, l, col))
            self._token(DELIMITADOR, c, l, col)
            self.pos += 1
        elif c == ")":
            if self.parenteses:
                self.parenteses.pop()
                self._token(DELIMITADOR, c, l, col)
            else:
                self._erro(ERRO_PAREN_SOBRA, c, l, col,
                           "parêntese ')' sem o '(' correspondente.")
            self.pos += 1
        elif c in DELIMITADORES:  # "," e ":"
            self._token(DELIMITADOR, c, l, col)
            self.pos += 1
        elif c == "!":
            self._erro(ERRO_CARACTERE, c, l, col,
                       "'!' sozinho não é um operador. Você quis escrever '!=' (diferente)?")
            self.pos += 1
        elif c in SIMBOLOS_FORA:
            self._erro(ERRO_FORA_SUBCONJUNTO, c, l, col,
                       "o símbolo '%s' é válido em Python, mas não faz parte do "
                       "subconjunto suportado." % c)
            self.pos += 1
        else:
            self._erro(ERRO_CARACTERE, c, l, col,
                       "caractere não reconhecido '%s'. Verifique se ele faz parte do "
                       "subconjunto suportado." % _mostrar(c))
            self.pos += 1

    # -------------------------------------------------------------- término
    def _finalizar(self):
        for _, l, c in self.parenteses:
            self._erro(ERRO_PAREN_ABERTO, "(", l, c,
                       "parêntese '(' aberto aqui e nunca fechado.")
        # Se a última instrução não terminou com \n, o scanner fecha a linha lógica.
        if not self.inicio_de_instrucao and self.tokens:
            self._token(NOVA_LINHA, "", self.linha, self._coluna(self.n))
            self.linha += 1
            self.inicio_linha = self.n
        for _ in range(len(self.indentacoes) - 1):
            self._token(DESINDENTACAO, "", self.linha, 1)
        self._token(FIM_ARQUIVO, "", self.linha, 1)


def tokenizar(codigo):
    """Devolve ``(tokens, erros)`` para o código-fonte informado."""
    return _Scanner(codigo).executar()


def analisar_lexico(codigo):
    """Executa o scanner e monta o resultado no formato usado pela API."""
    tokens, erros = tokenizar(codigo)
    por_categoria = dict.fromkeys(CATEGORIAS, 0)
    for t in tokens:
        por_categoria[t["tipo"]] += 1
    return {
        "sucesso": not erros,
        "tokens": tokens,
        "erros": erros,
        "resumo": {
            "total_tokens": len(tokens),
            "total_erros": len(erros),
            "por_categoria": por_categoria,
        },
    }
