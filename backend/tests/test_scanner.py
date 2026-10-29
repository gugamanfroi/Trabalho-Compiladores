"""Testes unitários do analisador léxico (scanner)."""
import io
import json
import sys
import keyword
import tokenize
import unittest

from scanner import (
    CATEGORIAS, PALAVRAS_RESERVADAS, analisar_lexico, tokenizar,
)

ESTRUTURAIS = {"NOVA_LINHA", "INDENTACAO", "DESINDENTACAO", "FIM_ARQUIVO"}


def toks(codigo):
    """Tokens não estruturais como (tipo, lexema); falha se houver erro léxico."""
    tokens, erros = tokenizar(codigo)
    assert not erros, erros
    return [(t["tipo"], t["lexema"]) for t in tokens if t["tipo"] not in ESTRUTURAIS]


def tipos(codigo):
    tokens, _ = tokenizar(codigo)
    return [t["tipo"] for t in tokens]


class PalavrasReservadasTest(unittest.TestCase):
    def test_cada_palavra_reservada_e_reconhecida(self):
        for palavra in sorted(PALAVRAS_RESERVADAS):
            with self.subTest(palavra=palavra):
                self.assertEqual(toks(palavra), [("PALAVRA_RESERVADA", palavra)])

    def test_lista_coincide_com_a_do_python(self):
        self.assertEqual(PALAVRAS_RESERVADAS, frozenset(keyword.kwlist))

    def test_diferencia_maiusculas_de_minusculas(self):
        self.assertEqual(toks("true none If"), [("IDENTIFICADOR", "true"),
                         ("IDENTIFICADOR", "none"), ("IDENTIFICADOR", "If")])

    def test_prefixo_de_palavra_reservada_e_identificador(self):
        self.assertEqual(toks("iffy elsewhere or_x"), [("IDENTIFICADOR", "iffy"),
                         ("IDENTIFICADOR", "elsewhere"), ("IDENTIFICADOR", "or_x")])


class IdentificadoresTest(unittest.TestCase):
    def test_formacoes_validas(self):
        for nome in ["numero", "_x1", "__init__", "a", "X", "total_2", "ação", "número", "π"]:
            with self.subTest(nome=nome):
                self.assertEqual(toks(nome), [("IDENTIFICADOR", nome)])

    def test_print_e_identificador_nao_palavra_reservada(self):
        self.assertEqual(toks("print")[0][0], "IDENTIFICADOR")

    def test_nao_pode_comecar_com_digito(self):
        tokens, erros = tokenizar("1abc")
        self.assertEqual([e["subtipo"] for e in erros], ["NUMERO_MALFORMADO"])
        self.assertEqual(erros[0]["lexema"], "1abc")
        self.assertFalse([t for t in tokens if t["tipo"] == "IDENTIFICADOR"])

    def test_hifen_separa_identificadores(self):
        self.assertEqual(toks("a-b"), [("IDENTIFICADOR", "a"), ("OPERADOR", "-"), ("IDENTIFICADOR", "b")])


class LiteraisTest(unittest.TestCase):
    def test_inteiros(self):
        for n in ["0", "10", "42", "00", "1234567890"]:
            with self.subTest(n=n):
                self.assertEqual(toks(n), [("LITERAL_INTEIRO", n)])

    def test_reais(self):
        for n in ["3.14", "0.5", "10.0", "007.5"]:
            with self.subTest(n=n):
                self.assertEqual(toks(n), [("LITERAL_REAL", n)])

    def test_strings_com_aspas_simples_e_duplas(self):
        for s in ['"olá"', "'olá'", '""', "''", '"it\'s"', "'say \"hi\"'", '"# nao e comentario"']:
            with self.subTest(s=s):
                self.assertEqual(toks(s), [("LITERAL_STRING", s)])

    def test_string_com_escape_nao_fecha_cedo(self):
        s = r'"a\"b"'
        self.assertEqual(toks(s), [("LITERAL_STRING", s)])
        s2 = r'"fim\\"'
        self.assertEqual(toks(s2), [("LITERAL_STRING", s2)])

    def test_real_so_com_um_ponto(self):
        self.assertEqual(toks("1+2.5"), [("LITERAL_INTEIRO", "1"), ("OPERADOR", "+"), ("LITERAL_REAL", "2.5")])

    def test_numeros_malformados(self):
        casos = {"1.2.3": "1.2.3", "5.": "5.", "12abc": "12abc", "1e5": "1e5", "0x1F": "0x1F",
                 "3.14abc": "3.14abc", "007": "007", ".5": ".5"}
        for codigo, lexema in casos.items():
            with self.subTest(codigo=codigo):
                tokens, erros = tokenizar(codigo)
                self.assertEqual(len(erros), 1, erros)
                self.assertEqual(erros[0]["subtipo"], "NUMERO_MALFORMADO")
                self.assertEqual(erros[0]["lexema"], lexema)
                self.assertFalse([t for t in tokens if t["tipo"].startswith("LITERAL")])


class OperadoresEDelimitadoresTest(unittest.TestCase):
    def test_cada_operador(self):
        for op in ["+", "-", "*", "/", "//", "%", "**", "=", "+=", "-=", "*=", "/=", "//=", "%=", "**=",
                   "==", "!=", "<", ">", "<=", ">="]:
            with self.subTest(op=op):
                self.assertEqual(toks("a %s b" % op),
                                 [("IDENTIFICADOR", "a"), ("OPERADOR", op), ("IDENTIFICADOR", "b")])

    def test_maior_casamento_possivel(self):
        self.assertEqual([l for _, l in toks("a**=b//=c==d")], ["a", "**=", "b", "//=", "c", "==", "d"])
        self.assertEqual([l for _, l in toks("a<=b>=c!=d")], ["a", "<=", "b", ">=", "c", "!=", "d"])

    def test_operadores_colados(self):
        self.assertEqual([l for _, l in toks("x=-1")], ["x", "=", "-", "1"])
        self.assertEqual([l for _, l in toks("10 +* 5")], ["10", "+", "*", "5"])  # erro sintático, não léxico

    def test_operadores_logicos_sao_palavras_reservadas(self):
        for p in ["and", "or", "not"]:
            self.assertEqual(toks("a %s b" % p)[1], ("PALAVRA_RESERVADA", p))

    def test_cada_delimitador(self):
        casos = {"(": ("(1)", 0), ")": ("(1)", 2), ",": ("1,2", 1), ":": ("a:", 1)}
        for d, (codigo, i) in casos.items():
            with self.subTest(delimitador=d):
                self.assertEqual(toks(codigo)[i], ("DELIMITADOR", d))

    def test_expressao_com_parenteses(self):
        self.assertEqual([l for _, l in toks("(a + b) * 2")], ["(", "a", "+", "b", ")", "*", "2"])


class ComentariosEEspacosTest(unittest.TestCase):
    def test_comentario_de_linha_e_ignorado(self):
        self.assertEqual(toks("x = 1  # isto é um comentário com @ $ ?"),
                         [("IDENTIFICADOR", "x"), ("OPERADOR", "="), ("LITERAL_INTEIRO", "1")])

    def test_apenas_comentarios(self):
        for codigo in ["# so comentario", "# a\n# b\n", "   # indentado\n"]:
            with self.subTest(codigo=codigo):
                tokens, erros = tokenizar(codigo)
                self.assertEqual(erros, [])
                self.assertEqual([t["tipo"] for t in tokens], ["FIM_ARQUIVO"])

    def test_espacos_tabs_e_formfeed_nao_geram_tokens(self):
        self.assertEqual(toks("a\t=\x0c1"), [("IDENTIFICADOR", "a"), ("OPERADOR", "="), ("LITERAL_INTEIRO", "1")])

    def test_cerquilha_dentro_de_string_nao_e_comentario(self):
        self.assertEqual(toks('x = "a # b"')[2], ("LITERAL_STRING", '"a # b"'))

    def test_quebras_crlf_e_cr_equivalem_a_lf(self):
        base = [(t["tipo"], t["lexema"] if t["tipo"] != "NOVA_LINHA" else "", t["linha"], t["coluna"])
                for t in tokenizar("a = 1\nb = 2\n")[0]]
        for sep in ["\r\n", "\r"]:
            with self.subTest(sep=repr(sep)):
                got = [(t["tipo"], t["lexema"] if t["tipo"] != "NOVA_LINHA" else "", t["linha"], t["coluna"])
                       for t in tokenizar("a = 1%sb = 2%s" % (sep, sep))[0]]
                self.assertEqual(got, base)


class PosicaoTest(unittest.TestCase):
    def pos(self, codigo):
        tokens, _ = tokenizar(codigo)
        return [(t["lexema"], t["linha"], t["coluna"]) for t in tokens if t["tipo"] not in ESTRUTURAIS]

    def test_exemplo_do_enunciado(self):
        self.assertEqual(self.pos("numero = 10"), [("numero", 1, 1), ("=", 1, 8), ("10", 1, 10)])

    def test_varias_linhas(self):
        self.assertEqual(self.pos("a = 1\n\n  # c\nbb = 22\n"),
                         [("a", 1, 1), ("=", 1, 3), ("1", 1, 5), ("bb", 4, 1), ("=", 4, 4), ("22", 4, 6)])

    def test_colunas_contam_caracteres_e_nao_bytes(self):
        self.assertEqual(self.pos('"ção" + x'), [('"ção"', 1, 1), ("+", 1, 7), ("x", 1, 9)])

    def test_tab_conta_como_uma_coluna(self):
        self.assertEqual(self.pos("a\t=\t1"), [("a", 1, 1), ("=", 1, 3), ("1", 1, 5)])

    def test_token_no_fim_do_arquivo_sem_quebra_de_linha(self):
        tokens, erros = tokenizar("x = 10")
        self.assertEqual(erros, [])
        self.assertEqual([(t["tipo"], t["linha"], t["coluna"]) for t in tokens[-3:]],
                         [("LITERAL_INTEIRO", 1, 5), ("NOVA_LINHA", 1, 7), ("FIM_ARQUIVO", 2, 1)])

    def test_posicao_apos_continuacao_de_linha(self):
        self.assertEqual(self.pos("x = 1 + \\\n    2"), [("x", 1, 1), ("=", 1, 3), ("1", 1, 5), ("+", 1, 7), ("2", 2, 5)])


class EstruturaDePythonTest(unittest.TestCase):
    def test_indent_e_dedent_do_exemplo_condicional(self):
        codigo = "if numero > 0:\n    numero = numero + 1\nprint(numero)\n"
        t = tipos(codigo)
        self.assertEqual(t.count("INDENTACAO"), 1)
        self.assertEqual(t.count("DESINDENTACAO"), 1)
        self.assertLess(t.index("INDENTACAO"), t.index("DESINDENTACAO"))

    def test_blocos_aninhados_fecham_no_fim_do_arquivo(self):
        t = tipos("if a:\n    if b:\n        c = 1\n")
        self.assertEqual(t.count("INDENTACAO"), 2)
        self.assertEqual(t.count("DESINDENTACAO"), 2)
        self.assertEqual(t[-3:], ["DESINDENTACAO", "DESINDENTACAO", "FIM_ARQUIVO"])

    def test_dedent_multiplo_de_uma_vez(self):
        t = tipos("if a:\n    if b:\n        c = 1\nd = 2\n")
        i = t.index("DESINDENTACAO")
        self.assertEqual(t[i:i + 2], ["DESINDENTACAO", "DESINDENTACAO"])

    def test_linhas_em_branco_e_comentarios_nao_alteram_indentacao(self):
        com = tipos("if a:\n    x = 1\n\n# fora\n   # torto\n    y = 2\n")
        sem = tipos("if a:\n    x = 1\n    y = 2\n")
        self.assertEqual(com, sem)

    def test_quebra_dentro_de_parenteses_e_ignorada(self):
        t = tipos("f(1,\n  2,\n       3)\n")
        self.assertEqual(t.count("NOVA_LINHA"), 1)
        self.assertNotIn("INDENTACAO", t)

    def test_continuacao_com_barra_invertida(self):
        t = tipos("x = 1 + \\\n    2\n")
        self.assertEqual(t.count("NOVA_LINHA"), 1)
        self.assertNotIn("INDENTACAO", t)

    def test_tab_equivale_a_oito_espacos(self):
        self.assertEqual(tipos("if a:\n\tx = 1\n"), tipos("if a:\n        x = 1\n"))

    def test_tab_e_oito_espacos_pertencem_ao_mesmo_nivel(self):
        # 8 espaços e depois um tab: mesmo nível, portanto sem erro e sem INDENT/DEDENT extras
        tokens, erros = tokenizar("if a:\n        x\n\ty\n")
        self.assertEqual(erros, [])
        self.assertEqual([t["tipo"] for t in tokens].count("INDENTACAO"), 1)

    def test_nova_linha_sintetizada_no_fim_sem_quebra(self):
        tokens, _ = tokenizar("x = 1")
        self.assertEqual(tokens[-2]["tipo"], "NOVA_LINHA")
        self.assertEqual(tokens[-2]["lexema"], "")

    def test_codigo_sempre_termina_com_fim_de_arquivo(self):
        for codigo in ["", " ", "\n", "x", "if a:\n    b\n", "@", '"'] :
            with self.subTest(codigo=repr(codigo)):
                self.assertEqual(tokenizar(codigo)[0][-1]["tipo"], "FIM_ARQUIVO")


class ErrosLexicosTest(unittest.TestCase):
    def erros(self, codigo):
        return tokenizar(codigo)[1]

    def test_caractere_nao_reconhecido(self):
        [e] = self.erros("x = 1 $ 2")
        self.assertEqual((e["tipo"], e["subtipo"], e["lexema"], e["linha"], e["coluna"]),
                         ("ERRO_LEXICO", "CARACTERE_NAO_RECONHECIDO", "$", 1, 7))
        self.assertIn("linha 1, coluna 7", e["mensagem"])
        self.assertIn("'$'", e["mensagem"])

    def test_mensagem_no_formato_do_enunciado(self):
        [e] = self.erros("a = 1\nb = 2 ? 3")
        self.assertEqual(e["mensagem"], "Erro léxico na linha 2, coluna 7: caractere não reconhecido '?'. "
                                        "Verifique se ele faz parte do subconjunto suportado.")

    def test_simbolos_validos_em_python_mas_fora_do_subconjunto(self):
        for c in "[]{};.@|&^~":
            with self.subTest(c=c):
                [e] = self.erros("a %s b" % c)
                self.assertEqual(e["subtipo"], "FORA_DO_SUBCONJUNTO")
                self.assertEqual(e["lexema"], c)

    def test_operadores_compostos_fora_do_subconjunto_geram_um_unico_erro(self):
        for op in ["<<", ">>", "->", ":=", "<<=", ">>="]:
            with self.subTest(op=op):
                [e] = self.erros("a %s b" % op)
                self.assertEqual((e["subtipo"], e["lexema"]), ("FORA_DO_SUBCONJUNTO", op))

    def test_exclamacao_sozinha_sugere_diferente(self):
        [e] = self.erros("a ! b")
        self.assertIn("!=", e["mensagem"])

    def test_string_nao_fechada(self):
        tokens, erros = tokenizar('x = "abc\ny = 1\n')
        self.assertEqual([(e["subtipo"], e["lexema"], e["linha"], e["coluna"]) for e in erros],
                         [("STRING_NAO_FECHADA", '"abc', 1, 5)])
        self.assertNotIn("LITERAL_STRING", [t["tipo"] for t in tokens])  # string aberta não vira token
        # o scanner continua: a linha 2 é tokenizada normalmente
        self.assertIn(("y", 2, 1), [(t["lexema"], t["linha"], t["coluna"]) for t in tokens])

    def test_string_terminada_em_barra_e_fim_de_arquivo(self):
        for codigo in ['"abc', "'abc", '"abc\\', '"']:
            with self.subTest(codigo=codigo):
                self.assertEqual([e["subtipo"] for e in self.erros(codigo)], ["STRING_NAO_FECHADA"])

    def test_string_tripla_nao_suportada_ignora_o_trecho(self):
        tokens, erros = tokenizar('x = """a\nb @ c"""\ny = 2\n')
        self.assertEqual([e["subtipo"] for e in erros], ["STRING_TRIPLA"])  # '@' dentro do trecho não gera erro
        self.assertIn(("y", 3, 1), [(t["lexema"], t["linha"], t["coluna"]) for t in tokens])

    def test_string_tripla_nunca_fechada_vai_ate_o_fim(self):
        self.assertEqual([e["subtipo"] for e in self.erros("x = '''abc\n def")], ["STRING_TRIPLA"])

    def test_parentese_nao_fechado_aponta_para_a_abertura(self):
        [e] = self.erros("a = 1\nb = (2 +\n  3\n")
        self.assertEqual((e["subtipo"], e["linha"], e["coluna"]), ("PARENTESE_NAO_FECHADO", 2, 5))

    def test_erro_de_parentese_aberto_e_ordenado_junto_dos_demais(self):
        # o erro do '(' só é detectado no fim da leitura, mas deve aparecer antes do '@' da linha 2
        erros = self.erros("a = (1\nb = @\n")
        self.assertEqual([(e["subtipo"], e["linha"]) for e in erros],
                         [("PARENTESE_NAO_FECHADO", 1), ("FORA_DO_SUBCONJUNTO", 2)])

    def test_parentese_sem_abertura(self):
        tokens, erros = tokenizar("a = 1)")
        self.assertEqual([(e["subtipo"], e["coluna"]) for e in erros], [("PARENTESE_SEM_ABERTURA", 6)])
        self.assertNotIn(")", [t["lexema"] for t in tokens])

    def test_indentacao_inconsistente(self):
        [e] = self.erros("if a:\n        x\n    y\n")
        self.assertEqual((e["subtipo"], e["linha"], e["coluna"]), ("INDENTACAO_INCONSISTENTE", 3, 1))

    def test_barra_invertida_fora_de_lugar(self):
        for codigo in ["a \\ b", "a \\"]:
            with self.subTest(codigo=codigo):
                self.assertEqual([e["subtipo"] for e in self.erros(codigo)], ["BARRA_INVERTIDA_INVALIDA"])

    def test_varios_erros_sao_acumulados_em_ordem_de_posicao(self):
        erros = self.erros('a = @\nb = 12x $\nc = "aberta\n')
        self.assertEqual([(e["linha"], e["coluna"], e["lexema"]) for e in erros],
                         [(1, 5, "@"), (2, 5, "12x"), (2, 9, "$"), (3, 5, '"aberta')])

    def test_apos_um_erro_o_restante_continua_sendo_tokenizado(self):
        tokens, erros = tokenizar("a = 1 @ 2 + 3")
        self.assertEqual(len(erros), 1)
        self.assertEqual([t["lexema"] for t in tokens if t["tipo"] not in ESTRUTURAIS],
                         ["a", "=", "1", "2", "+", "3"])

    def test_caracteres_de_controle_sao_escapados_na_mensagem(self):
        [e] = self.erros("a = \x00")
        self.assertIn("\\x00", e["mensagem"])
        self.assertNotIn("\x00", e["mensagem"])
        json.dumps(e)  # serializável

    def test_emoji_e_caracteres_unicode_invalidos(self):
        [e] = self.erros("x = 😀 + 1")
        self.assertEqual((e["lexema"], e["coluna"]), ("😀", 5))

    def test_caractere_substituto_isolado_nao_quebra(self):
        [e] = self.erros("x = \ud800")
        self.assertEqual(e["subtipo"], "CARACTERE_NAO_RECONHECIDO")
        json.dumps(analisar_lexico("x = \ud800"))

    def test_erro_nunca_expoe_detalhes_internos(self):
        entradas = ["@", '"', "(", "1.2.3", "\\", "if a:\n        x\n    y", '"""', "\x00\x01"]
        for e in sum((self.erros(c) for c in entradas), []):
            self.assertNotRegex(e["mensagem"], r"Traceback|\.py|Exception|line \d+, in")


class CasosDeBordaTest(unittest.TestCase):
    def test_codigo_vazio_ou_so_espacos(self):
        for codigo in ["", " ", "   \n  \n\t\n"]:
            with self.subTest(codigo=repr(codigo)):
                r = analisar_lexico(codigo)
                self.assertTrue(r["sucesso"])
                self.assertEqual([t["tipo"] for t in r["tokens"]], ["FIM_ARQUIVO"])

    def test_comentario_no_fim_sem_quebra_de_linha(self):
        tokens, erros = tokenizar("x = 1 # fim")
        self.assertEqual(erros, [])
        self.assertEqual(tokens[-2]["coluna"], 12)

    def test_espacos_no_fim_da_linha_com_dedent(self):
        self.assertEqual(tipos("if a:\n    b   \n"), tipos("if a:\n    b\n"))

    def test_entrada_grande_roda_rapido(self):
        import time
        codigo = "x = (1 + 2) * 3.5  # c\n" * 4000  # ~ 90 mil caracteres
        t0 = time.time()
        r = analisar_lexico(codigo)
        self.assertTrue(r["sucesso"])
        self.assertLess(time.time() - t0, 3.0)

    def test_exemplos_do_enunciado(self):
        r = analisar_lexico("numero = 10\nprint(numero)\n")
        self.assertEqual([t["lexema"] for t in r["tokens"] if t["tipo"] not in ESTRUTURAIS],
                         ["numero", "=", "10", "print", "(", "numero", ")"])


class ResumoTest(unittest.TestCase):
    def test_contagem_por_categoria_inclui_todas_as_categorias(self):
        r = analisar_lexico("if a > 1:\n    b = 2.5\n")
        pc = r["resumo"]["por_categoria"]
        self.assertEqual(list(pc), list(CATEGORIAS))
        self.assertEqual(pc["PALAVRA_RESERVADA"], 1)
        self.assertEqual(pc["IDENTIFICADOR"], 2)
        self.assertEqual(pc["OPERADOR"], 2)
        self.assertEqual(pc["LITERAL_REAL"], 1)
        self.assertEqual(pc["LITERAL_STRING"], 0)
        self.assertEqual(sum(pc.values()), r["resumo"]["total_tokens"])
        self.assertEqual(r["resumo"]["total_erros"], 0)

    def test_sucesso_reflete_a_existencia_de_erros(self):
        self.assertTrue(analisar_lexico("a = 1")["sucesso"])
        r = analisar_lexico("a = @")
        self.assertFalse(r["sucesso"])
        self.assertEqual(r["resumo"]["total_erros"], 1)


# --- Teste diferencial contra o tokenize do próprio CPython ------------------
_MAPA = {
    "PALAVRA_RESERVADA": "NAME", "IDENTIFICADOR": "NAME", "LITERAL_INTEIRO": "NUMBER",
    "LITERAL_REAL": "NUMBER", "LITERAL_STRING": "STRING", "OPERADOR": "OP", "DELIMITADOR": "OP",
    "NOVA_LINHA": "NEWLINE", "INDENTACAO": "INDENT", "DESINDENTACAO": "DEDENT",
}

PROGRAMAS_VALIDOS = [
    "numero = 10\nprint(numero)\n",
    "a = 10\nb = 5\nresultado = a + b * 2\nmedia = (a + b) / 2\nprint(resultado)\nprint(media)\n",
    "numero = 10\nif numero > 0:\n    numero = numero + 1\nprint(numero)\n",
    "resultado = 10 +* 5\n",  # erro sintático, mas tokens válidos
    "x = 3.14  # comentário\ns = 'olá' + \"mundo\"\nok = True and not False or None\n",
    "if a:\n    if b:\n        c = 1\n\n    # comentário\n    d = 2\ne = 3\n",
    "total = (1 +\n         2 +\n   3)\nx = 1 + \\\n    2\n",
    "x **= 2\ny //= 3\nz %= 4\nw = a != b\nv = a <= b >= c == d\n",
    "while n > 0:\n\tn -= 1\n\tif n == 3:\n\t\tbreak\n",
    "ação = 1\nnúmero_2 = ação + 1\n",
    "x = 1",
    "x = 1  # sem quebra no fim",
    "def f(a, b):\n    return a + b\n",
    "",
    "\n\n   \n# so comentarios\n",
]


class ComparacaoComTokenizeDoCPythonTest(unittest.TestCase):
    """Para programas sem erro léxico, o scanner deve concordar com o CPython."""

    @staticmethod
    def esperado(codigo):
        saida = []
        for t in tokenize.generate_tokens(io.StringIO(codigo).readline):
            nome = tokenize.tok_name[t.type]
            if nome in ("COMMENT", "NL", "ENDMARKER"):
                continue
            saida.append((nome, t.string, t.start[0], t.start[1] + 1))
        return saida

    @staticmethod
    def obtido(codigo):
        tokens, erros = tokenizar(codigo)
        assert not erros, erros
        return [(_MAPA[t["tipo"]], t["lexema"], t["linha"], t["coluna"])
                for t in tokens if t["tipo"] != "FIM_ARQUIVO"]

    def test_tipos_lexemas_e_posicoes_coincidem(self):
        for codigo in PROGRAMAS_VALIDOS:
            with self.subTest(codigo=codigo[:40]):
                esp, obt = self.esperado(codigo), self.obtido(codigo)
                # Em versões do Python que posicionam NEWLINE/DEDENT sintéticos de outro jeito,
                # ao menos tipos e lexemas dos demais tokens devem coincidir.
                estrut = {"NEWLINE", "INDENT", "DEDENT"}
                self.assertEqual([x for x in obt if x[0] not in estrut], [x for x in esp if x[0] not in estrut])
                self.assertEqual([x[0] for x in obt], [x[0] for x in esp])

    @unittest.skipIf(sys.version_info < (3, 12), "tokenize puro-Python de versões antigas posiciona tokens sintéticos de forma diferente")
    def test_posicoes_dos_tokens_estruturais_coincidem_no_python_3_12(self):
        for codigo in PROGRAMAS_VALIDOS:
            with self.subTest(codigo=codigo[:40]):
                esp = [x for x in self.esperado(codigo) if not (x[0] in ("NEWLINE", "DEDENT") and x[1] == "")]
                obt = [x for x in self.obtido(codigo) if not (x[0] in ("NEWLINE", "DEDENT") and x[1] == "")]
                self.assertEqual(obt, esp)


if __name__ == "__main__":
    unittest.main()
