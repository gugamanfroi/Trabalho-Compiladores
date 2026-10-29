"""Testes de interface e ponta a ponta (Playwright + Chromium).

O frontend é carregado em um navegador real e conversa com o backend Flask
real através do servidor de teste (que imita o proxy do Nginx).
Executar a partir da raiz do projeto:  python -m unittest discover -s tests/e2e -v
"""
import json
import os
import re
import sys
import unittest

sys.path.insert(0, os.path.dirname(__file__))

from playwright.sync_api import sync_playwright  # noqa: E402

from servidor import Ambiente  # noqa: E402

MSG_VAZIO = "Informe um código-fonte antes de solicitar a análise."
MSG_ESPACOS = "O código informado contém apenas espaços em branco. Digite um programa para ser analisado."
MSG_COM = "Não foi possível comunicar com o servidor. Verifique a conexão e tente novamente."

# Mesmos textos de frontend/js/exemplos.js (conferidos pelo teste de carregamento)
EXEMPLOS = {
    "declaracao": "numero = 10\nprint(numero)\n",
    "aritmetica": "a = 10\nb = 5\nresultado = a + b * 2\nmedia = (a + b) / 2\nprint(resultado)\nprint(media)\n",
    "condicional": "numero = 10\nif numero > 0:\n    numero = numero + 1\nprint(numero)\n",
    "erro": "resultado = 10 +* 5\nprint(resultado)\n",
    "tokens": "# preço com desconto\npreco = 12.5\nnome = \"Ana\"\ntotal = (preco * 2) // 3 + 4 ** 2\n"
              "if total >= 10 and nome != \"Bia\":\n    total -= 1\n",
    "erros-lexicos": "valor = 10 @ 2\n12abc = 5\ntexto = \"sem fechar\ntotal = (1 + 2\n",
    "indentacao": "n = 3\nwhile n > 0:\n    if n == 2:\n        n = n - 2\n    n = n - 1\nprint(n)\n",
}
# (sucesso léxico, quantidade de erros léxicos) esperados por exemplo
RESULTADO_LEXICO = {k: (True, 0) for k in EXEMPLOS}
RESULTADO_LEXICO["erros-lexicos"] = (False, 4)
CONCLUIDO = '#resultado[data-estado="sucesso"], #resultado[data-estado="erro-lexico"]'



class UiBase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.amb = Ambiente().__enter__()
        cls.pw = sync_playwright().start()
        cls.browser = cls.pw.chromium.launch(args=["--no-sandbox"])

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.pw.stop()
        cls.amb.__exit__(None, None, None)

    def setUp(self):
        self.page = self.browser.new_page()
        self.erros_js = []
        self.page.on("pageerror", lambda e: self.erros_js.append(str(e)))
        self.page.goto(self.amb.url)

    def tearDown(self):
        self.page.close()
        self.assertEqual(self.erros_js, [], "erros JavaScript na página")

    # atalhos
    def codigo(self):
        return self.page.input_value("#codigo")

    def digitar(self, texto):
        self.page.fill("#codigo", texto)

    def analisar(self):
        self.page.click("#btn-analisar")

    def resultado(self):
        return self.page.locator("#resultado")

    def assertResultado(self, estado, trecho):
        self.assertEqual(self.resultado().get_attribute("data-estado"), estado)
        self.assertIn(trecho, self.resultado().inner_text())


class InterfaceTest(UiBase):
    def test_identificacao_do_sistema_e_linguagem(self):
        self.assertIn("Compilador Educacional", self.page.inner_text("h1"))
        self.assertIn("Python", self.page.inner_text("#linguagem"))

    def test_elementos_principais_visiveis(self):
        for sel in ["#codigo", "#btn-analisar", "#resultado", "#seletor-exemplo"]:
            self.assertTrue(self.page.locator(sel).is_visible(), sel)

    def test_campo_monoespacado_e_botao_com_texto_claro(self):
        fonte = self.page.eval_on_selector("#codigo", "e => getComputedStyle(e).fontFamily")
        self.assertRegex(fonte.lower(), r"mono|consolas|courier|cascadia|fira")
        self.assertEqual(self.page.inner_text("#btn-analisar"), "Analisar código")

    def test_estado_inicial(self):
        self.assertEqual(self.codigo(), "")
        self.assertEqual(self.resultado().get_attribute("data-estado"), "inicial")
        self.assertIn("Analisar código", self.resultado().inner_text())

    def test_seletor_tem_ao_menos_tres_exemplos(self):
        opcoes = self.page.eval_on_selector_all(
            "#seletor-exemplo option", "os => os.filter(o => o.value).map(o => o.value)"
        )
        self.assertGreaterEqual(len(opcoes), 3)
        self.assertEqual(set(opcoes), set(EXEMPLOS))


class EntradaEExemplosTest(UiBase):
    def test_cada_exemplo_carrega_o_codigo_correto(self):
        for id_, esperado in EXEMPLOS.items():
            with self.subTest(exemplo=id_):
                self.page.select_option("#seletor-exemplo", id_)
                self.assertEqual(self.codigo(), esperado)
                self.assertNotEqual(self.page.inner_text("#descricao-exemplo"), "")

    def test_novo_exemplo_substitui_o_conteudo_anterior(self):
        self.page.select_option("#seletor-exemplo", "declaracao")
        self.page.select_option("#seletor-exemplo", "condicional")
        self.assertEqual(self.codigo(), EXEMPLOS["condicional"])

    def test_exemplo_substitui_texto_digitado(self):
        self.digitar("qualquer coisa")
        self.page.select_option("#seletor-exemplo", "aritmetica")
        self.assertEqual(self.codigo(), EXEMPLOS["aritmetica"])

    def test_exemplo_pode_ser_editado(self):
        self.page.select_option("#seletor-exemplo", "declaracao")
        self.page.click("#codigo")
        self.page.keyboard.press("Control+End")
        self.page.keyboard.type("x = 99")
        self.assertEqual(self.codigo(), EXEMPLOS["declaracao"] + "x = 99")

    def test_exemplo_limpa_resultado_anterior(self):
        self.digitar("x = 1")
        self.analisar()
        self.page.wait_for_selector('#resultado[data-estado="sucesso"]')
        self.page.select_option("#seletor-exemplo", "declaracao")
        self.assertEqual(self.resultado().get_attribute("data-estado"), "inicial")

    def test_contador_acompanha_a_edicao(self):
        self.digitar("a = 1\nb = 2")
        self.assertIn("2 linhas", self.page.inner_text("#contador"))
        self.assertIn("11 caracteres", self.page.inner_text("#contador"))

    def test_contador_de_linhas_coincide_com_o_do_servidor(self):
        for id_ in EXEMPLOS:  # os exemplos terminam com quebra de linha
            with self.subTest(exemplo=id_):
                self.page.select_option("#seletor-exemplo", id_)
                linhas_ui = int(re.match(r"(\d+) linha", self.page.inner_text("#contador")).group(1))
                self.analisar()
                self.page.wait_for_selector(CONCLUIDO)
                m = re.search(r"Linhas recebidas\s+(\d+)", self.resultado().inner_text())
                self.assertEqual(linhas_ui, int(m.group(1)))

    def test_limpar(self):
        self.page.select_option("#seletor-exemplo", "declaracao")
        self.page.click("#btn-limpar")
        self.assertEqual(self.codigo(), "")
        self.assertEqual(self.page.input_value("#seletor-exemplo"), "")
        self.assertEqual(self.resultado().get_attribute("data-estado"), "inicial")

    def test_colar_e_substituir_conteudo(self):
        self.digitar("primeiro = 1")
        self.digitar("segundo = 2")
        self.assertEqual(self.codigo(), "segundo = 2")

    def test_conteudo_preservado_apos_analise_com_sucesso_e_com_erro(self):
        self.digitar("x = 1\ny = 2")
        self.analisar()
        self.page.wait_for_selector('#resultado[data-estado="sucesso"]')
        self.assertEqual(self.codigo(), "x = 1\ny = 2")
        self.digitar("   ")
        self.analisar()
        self.assertEqual(self.codigo(), "   ")


class FluxoComBackendRealTest(UiBase):
    def test_exemplo_completo_do_inicio_ao_fim(self):
        self.page.select_option("#seletor-exemplo", "condicional")
        with self.page.expect_request("**/api/analisar") as info:
            self.analisar()
        req = info.value
        self.assertEqual(req.method, "POST")
        self.assertEqual(json.loads(req.post_data), {"codigo": EXEMPLOS["condicional"]})
        self.page.wait_for_selector('#resultado[data-estado="sucesso"]')
        texto = self.resultado().inner_text()
        # Etapa 3: a mensagem agora descreve a análise léxica (mudança intencional de requisito)
        self.assertIn("Análise léxica concluída sem erros", texto)
        self.assertRegex(texto, r"Linhas recebidas\s+4")
        self.assertRegex(texto, r"Caracteres recebidos\s+%d" % len(EXEMPLOS["condicional"]))
        self.assertIn("Etapa 4", texto)

    def test_todos_os_exemplos_sao_aceitos_pelo_backend(self):
        for id_ in EXEMPLOS:  # inclui o exemplo com erros léxicos (a requisição continua sendo aceita)
            with self.subTest(exemplo=id_):
                self.page.select_option("#seletor-exemplo", id_)
                self.analisar()
                self.page.wait_for_selector(CONCLUIDO)

    def test_codigo_digitado_manualmente(self):
        self.digitar("resultado = 10 + 5")
        self.analisar()
        self.page.wait_for_selector('#resultado[data-estado="sucesso"]')
        self.assertRegex(self.resultado().inner_text(), r"Caracteres recebidos\s+18")

    def test_caracteres_especiais_sao_enviados_intactos_e_nao_executados(self):
        especial = 'print("ação ✓")  # <script>window.__xss=1</script> <img src=x onerror="window.__xss=1"> "\'\\\t'
        self.digitar(especial)
        with self.page.expect_request("**/api/analisar") as info:
            self.analisar()
        self.assertEqual(json.loads(info.value.post_data)["codigo"], especial)
        self.page.wait_for_selector('#resultado[data-estado="sucesso"]')
        self.assertIsNone(self.page.evaluate("window.__xss"))

    def test_botao_fica_desabilitado_durante_o_envio(self):
        self.digitar("x = 1")
        desabilitado = self.page.evaluate(
            "() => { const b = document.getElementById('btn-analisar'); b.click(); return b.disabled; }"
        )
        self.assertTrue(desabilitado)
        self.page.wait_for_selector('#resultado[data-estado="sucesso"]')
        self.assertFalse(self.page.is_disabled("#btn-analisar"))
        self.assertEqual(self.page.inner_text("#btn-analisar"), "Analisar código")

    def test_backend_valida_mesmo_sem_frontend(self):
        casos = [
            ({"codigo": ""}, 422, "entrada_vazia"),
            ({"codigo": "  "}, 422, "entrada_somente_espacos"),
            ({}, 400, "requisicao_invalida"),
        ]
        for corpo, status, tipo in casos:
            with self.subTest(corpo=corpo):
                r = self.page.evaluate(
                    """async (c) => { const r = await fetch('/api/analisar', {method:'POST',
                         headers:{'Content-Type':'application/json'}, body: JSON.stringify(c)});
                         return {status: r.status, corpo: await r.json()}; }""", corpo)
                self.assertEqual(r["status"], status)
                self.assertEqual(r["corpo"]["erro"]["tipo"], tipo)

    def test_health_via_proxy(self):
        r = self.page.evaluate("fetch('/health').then(async r => ({s: r.status, b: await r.json()}))")
        self.assertEqual(r, {"s": 200, "b": {"status": "ok"}})


class ValidacaoEErrosNaInterfaceTest(UiBase):
    def assertSemRequisicao(self):
        enviadas = []
        self.page.on("request", lambda r: enviadas.append(r.url) if "/api/" in r.url else None)
        self.analisar()
        self.page.wait_for_selector('#resultado[data-estado="erro-entrada"]')
        self.assertEqual(enviadas, [], "não deveria enviar requisição")

    def test_entrada_vazia(self):
        self.assertSemRequisicao()
        self.assertIn(MSG_VAZIO, self.resultado().inner_text())

    def test_entrada_somente_espacos(self):
        self.digitar("   \n\t  ")
        self.assertSemRequisicao()
        self.assertIn(MSG_ESPACOS, self.resultado().inner_text())

    def test_falha_de_rede(self):
        self.page.route("**/api/analisar", lambda route: route.abort())
        self.digitar("x = 1")
        self.analisar()
        self.page.wait_for_selector('#resultado[data-estado="erro-comunicacao"]')
        self.assertIn(MSG_COM, self.resultado().inner_text())

    def test_interface_consistente_apos_falha_e_nova_tentativa_funciona(self):
        self.page.route("**/api/analisar", lambda route: route.abort())
        self.digitar("x = 1")
        self.analisar()
        self.page.wait_for_selector('#resultado[data-estado="erro-comunicacao"]')
        self.assertFalse(self.page.is_disabled("#btn-analisar"))
        self.assertEqual(self.page.inner_text("#btn-analisar"), "Analisar código")
        self.assertEqual(self.codigo(), "x = 1")
        self.page.unroute("**/api/analisar")
        self.analisar()
        self.page.wait_for_selector('#resultado[data-estado="sucesso"]')

    def test_proxy_devolve_502_html(self):
        self.page.route("**/api/analisar", lambda r: r.fulfill(
            status=502, content_type="text/html", body="<html><h1>502 Bad Gateway</h1>nginx/1.27</html>"))
        self.digitar("x = 1")
        self.analisar()
        self.page.wait_for_selector('#resultado[data-estado="erro-comunicacao"]')
        texto = self.resultado().inner_text()
        self.assertIn(MSG_COM, texto)
        self.assertNotIn("nginx", texto)

    def test_erro_interno_mostra_mensagem_generica(self):
        self.page.route("**/api/analisar", lambda r: r.fulfill(
            status=500, content_type="application/json",
            body=json.dumps({"recebido": False, "erro": {
                "tipo": "erro_interno",
                "mensagem": "Ocorreu um erro inesperado ao processar a requisição. Tente novamente em instantes."}})))
        self.digitar("x = 1")
        self.analisar()
        self.page.wait_for_selector('#resultado[data-estado="erro-inesperado"]')
        texto = self.resultado().inner_text()
        self.assertIn("erro inesperado", texto)
        self.assertNotRegex(texto, r"Traceback|\.py|/app/")

    def test_erro_do_backend_e_exibido_quando_frontend_deixa_passar(self):
        # Simula um frontend que não validou: o backend responde 422 e a UI mostra a mensagem.
        self.page.route("**/api/analisar", lambda r: r.fulfill(
            status=422, content_type="application/json",
            body=json.dumps({"recebido": False, "erro": {"tipo": "entrada_vazia", "mensagem": MSG_VAZIO}})))
        self.digitar("x = 1")
        self.analisar()
        self.page.wait_for_selector('#resultado[data-estado="erro-entrada"]')
        self.assertIn(MSG_VAZIO, self.resultado().inner_text())

    def test_texto_vindo_do_servidor_e_exibido_como_texto_nao_como_html(self):
        malicioso = '<img src=x onerror="window.__xss=1"><b>negrito</b>'
        self.page.route("**/api/analisar", lambda r: r.fulfill(
            status=422, content_type="application/json",
            body=json.dumps({"recebido": False, "erro": {"tipo": "entrada_vazia", "mensagem": malicioso}})))
        self.digitar("x = 1")
        self.analisar()
        self.page.wait_for_selector('#resultado[data-estado="erro-entrada"]')
        self.assertIn(malicioso, self.resultado().inner_text())
        self.assertEqual(self.page.locator("#resultado img, #resultado b").count(), 0)
        self.assertIsNone(self.page.evaluate("window.__xss"))

    def test_mensagem_de_erro_some_ao_analisar_com_sucesso(self):
        self.analisar()
        self.page.wait_for_selector('#resultado[data-estado="erro-entrada"]')
        self.digitar("x = 1")
        self.analisar()
        self.page.wait_for_selector('#resultado[data-estado="sucesso"]')
        self.assertNotIn(MSG_VAZIO, self.resultado().inner_text())


class AnaliseLexicaUiTest(UiBase):
    """Etapa 3: tokens, erros léxicos, destaque e passo a passo exibidos na interface."""

    def analisar_texto(self, texto):
        self.digitar(texto)
        self.analisar()
        self.page.wait_for_selector(CONCLUIDO)

    def abrir_aba(self, id_):
        self.page.click("#aba-" + id_)
        self.page.wait_for_selector("#painel-%s:not([hidden])" % id_)

    def linhas_da_tabela(self):
        return self.page.eval_on_selector_all(
            "#tabela-tokens tbody tr", "rs => rs.map(r => Array.from(r.cells).map(c => c.innerText))")

    # --- tabela
    def test_tokens_aparecem_na_tabela_com_tipo_lexema_linha_e_coluna(self):
        self.analisar_texto("numero = 10\n")
        self.abrir_aba("tabela")
        self.assertEqual(
            [l[1:] for l in self.linhas_da_tabela()],
            [["IDENTIFICADOR", "numero", "1", "1"], ["OPERADOR", "=", "1", "8"],
             ["LITERAL_INTEIRO", "10", "1", "10"], ["NOVA_LINHA", "↵", "1", "12"],
             ["FIM_ARQUIVO", "∎", "2", "1"]])
        cabecalhos = self.page.eval_on_selector_all("#tabela-tokens th", "hs => hs.map(h => h.innerText)")
        self.assertEqual(cabecalhos, ["#", "Tipo", "Lexema", "Linha", "Coluna"])

    def test_alternar_tokens_de_estrutura(self):
        self.analisar_texto("numero = 10\n")
        self.abrir_aba("tabela")
        self.page.uncheck("#chk-estruturais")
        self.assertEqual([l[2] for l in self.linhas_da_tabela()], ["numero", "=", "10"])
        self.assertEqual(self.page.locator(".legenda-item[data-tipo=NOVA_LINHA]").count(), 0)
        self.page.check("#chk-estruturais")
        self.assertEqual(len(self.linhas_da_tabela()), 5)

    def test_cada_exemplo_gera_o_resultado_lexico_esperado(self):
        for id_ in EXEMPLOS:
            with self.subTest(exemplo=id_):
                self.page.select_option("#seletor-exemplo", id_)
                self.analisar()
                self.page.wait_for_selector(CONCLUIDO)
                sucesso, n_erros = RESULTADO_LEXICO[id_]
                estado = self.resultado().get_attribute("data-estado")
                self.assertEqual(estado, "sucesso" if sucesso else "erro-lexico")
                self.assertEqual(self.page.locator(".erros-lista li").count(), n_erros)
                total = int(re.search(r"Tokens\s+(\d+)", self.resultado().inner_text()).group(1))
                self.abrir_aba("tabela")
                self.assertEqual(len(self.linhas_da_tabela()), total)

    def test_erro_de_sintaxe_nao_e_apontado_pelo_scanner(self):
        self.page.select_option("#seletor-exemplo", "erro")
        self.analisar()
        self.page.wait_for_selector('#resultado[data-estado="sucesso"]')
        self.assertEqual(self.page.locator(".erros-lista").count(), 0)

    # --- erros
    def test_erros_lexicos_exibidos_com_mensagem_e_localizacao(self):
        self.page.select_option("#seletor-exemplo", "erros-lexicos")
        self.analisar()
        self.page.wait_for_selector('#resultado[data-estado="erro-lexico"]')
        itens = self.page.eval_on_selector_all(".erros-lista li", "ls => ls.map(l => l.innerText)")
        self.assertEqual(len(itens), 4)
        self.assertIn("linha 1, coluna 12", itens[0])
        self.assertIn("'@'", itens[0])
        self.assertIn("linha 2, coluna 1", itens[1])
        self.assertIn("12abc", itens[1])
        self.assertIn("string não fechada", itens[2])
        self.assertIn("linha 4, coluna 9", itens[3])
        self.assertIn("4 erros léxicos", self.resultado().inner_text())
        self.assertNotRegex(self.resultado().inner_text(), r"Traceback|\.py\b")

    def test_erros_sao_marcados_no_codigo_e_a_analise_continua_apos_eles(self):
        self.page.select_option("#seletor-exemplo", "erros-lexicos")
        self.analisar()
        self.page.wait_for_selector('#resultado[data-estado="erro-lexico"]')
        marcados = self.page.eval_on_selector_all("#painel-codigo .seg[data-erro]", "es => es.map(e => e.textContent)")
        self.assertEqual(marcados, ["@", "12abc", '"sem fechar', "("])
        self.abrir_aba("tabela")
        lexemas = [l[2] for l in self.linhas_da_tabela()]
        self.assertIn("valor", lexemas)
        self.assertIn("total", lexemas)  # linha 4 foi tokenizada mesmo após os erros anteriores

    # --- destaque
    def test_destaque_colorido_por_categoria_e_legenda(self):
        self.page.select_option("#seletor-exemplo", "tokens")
        self.analisar()
        self.page.wait_for_selector('#resultado[data-estado="sucesso"]')
        def lex(tipo):
            return self.page.eval_on_selector_all(
                '#painel-codigo .codigo-view .seg[data-tipo="%s"]' % tipo, "es => es.map(e => e.textContent)")
        self.assertEqual(lex("PALAVRA_RESERVADA"), ["if", "and"])
        self.assertEqual(lex("LITERAL_REAL"), ["12.5"])
        self.assertEqual(lex("LITERAL_STRING"), ['"Ana"', '"Bia"'])
        self.assertIn("//", lex("OPERADOR"))
        self.assertIn("**", lex("OPERADOR"))
        self.assertEqual(self.page.eval_on_selector_all("#painel-codigo .seg.comentario", "es => es.map(e => e.textContent)"),
                         ["# preço com desconto"])
        self.assertEqual(self.page.inner_text(".legenda-item[data-tipo=PALAVRA_RESERVADA] b"), "2")
        def cor(tipo):
            return self.page.eval_on_selector(
                '#painel-codigo .codigo-view .seg[data-tipo="%s"]' % tipo, "e => getComputedStyle(e).color")
        cores = {t: cor(t) for t in ("PALAVRA_RESERVADA", "LITERAL_STRING", "LITERAL_INTEIRO", "OPERADOR", "IDENTIFICADOR")}
        self.assertEqual(len(set(cores.values())), len(cores), cores)  # cada categoria tem sua cor

    def test_codigo_exibido_e_identico_ao_enviado(self):
        for id_ in ("tokens", "erros-lexicos", "indentacao"):
            with self.subTest(exemplo=id_):
                self.page.select_option("#seletor-exemplo", id_)
                self.analisar()
                self.page.wait_for_selector(CONCLUIDO)
                linhas = self.page.eval_on_selector_all(
                    "#painel-codigo .codigo-view .linha", "ls => ls.map(l => Array.from(l.querySelectorAll('.seg:not(.marcador)')).map(s => s.textContent).join(''))")
                self.assertEqual(linhas, EXEMPLOS[id_].rstrip("\n").split("\n"))

    def test_sequencia_de_tokens_exibida(self):
        self.analisar_texto("a = 1\n")
        chips = self.page.eval_on_selector_all("#painel-codigo .sequencia .chip", "cs => cs.map(c => c.textContent)")
        self.assertEqual(chips, ["a", "=", "1", "↵", "∎"])

    # --- passo a passo
    def test_passo_a_passo_navega_pelos_tokens(self):
        self.analisar_texto("numero = 10\n")
        self.abrir_aba("passos")
        self.assertIn("Passo 0 de 5", self.page.inner_text(".progresso"))
        self.assertTrue(self.page.is_disabled("#btn-anterior"))
        self.page.click("#btn-proximo")
        self.assertIn("Passo 1 de 5", self.page.inner_text(".progresso"))
        self.assertEqual(self.page.inner_text("#painel-passos .seg.atual"), "numero")
        self.assertIn("IDENTIFICADOR", self.page.inner_text(".cartao-passo"))
        self.assertIn("linha 1, coluna 1", self.page.inner_text(".cartao-passo"))
        self.page.click("#btn-proximo")
        self.assertEqual(self.page.inner_text("#painel-passos .seg.atual"), "=")
        self.assertEqual(self.page.locator("#painel-passos .seg.lido").count(), 1)
        self.assertIn("OPERADOR", self.page.inner_text(".cartao-passo"))
        self.page.click("#btn-anterior")
        self.assertEqual(self.page.inner_text("#painel-passos .seg.atual"), "numero")
        self.page.click("#btn-fim")
        self.assertIn("Passo 5 de 5", self.page.inner_text(".progresso"))
        self.assertTrue(self.page.is_disabled("#btn-proximo"))
        self.assertIn("FIM_ARQUIVO", self.page.inner_text(".cartao-passo"))
        self.page.click("#btn-inicio")
        self.assertIn("Passo 0 de 5", self.page.inner_text(".progresso"))
        self.assertEqual(self.page.locator("#painel-passos .seg.atual").count(), 0)

    def test_passo_a_passo_explica_erro_lexico(self):
        self.analisar_texto("a = @\n")
        self.abrir_aba("passos")
        for _ in range(3):  # a, =, erro léxico (@)
            self.page.click("#btn-proximo")
        card = self.page.locator(".cartao-passo")
        self.assertEqual(card.get_attribute("data-erro"), "1")
        self.assertIn("'@'", card.inner_text())
        self.assertEqual(self.page.inner_text("#painel-passos .seg.atual"), "@")

    def test_execucao_automatica_percorre_e_para_no_fim(self):
        self.analisar_texto("a = 1\n")
        self.abrir_aba("passos")
        self.page.select_option("#sel-velocidade", "rapida")
        self.page.click("#btn-executar")
        self.assertEqual(self.page.inner_text("#btn-executar"), "⏸ Pausar")
        self.page.wait_for_function("document.querySelector('.progresso').textContent.includes('Passo 5 de 5')", timeout=5000)
        self.assertEqual(self.page.inner_text("#btn-executar"), "▶ Executar")

    def test_pausar_interrompe_a_execucao(self):
        self.analisar_texto("a = 1\nb = 2\nc = 3\n")
        self.abrir_aba("passos")
        self.page.select_option("#sel-velocidade", "lenta")
        self.page.click("#btn-executar")
        self.page.click("#btn-executar")  # pausa
        self.assertEqual(self.page.inner_text("#btn-executar"), "▶ Executar")
        antes = self.page.inner_text(".progresso")
        self.page.wait_for_timeout(1500)
        self.assertEqual(self.page.inner_text(".progresso"), antes)

    def test_clicar_numa_linha_da_tabela_abre_o_passo_correspondente(self):
        self.analisar_texto("a = 10\n")
        self.abrir_aba("tabela")
        self.page.click("#tabela-tokens tbody tr:nth-child(3)")  # token "10"
        self.page.wait_for_selector("#painel-passos:not([hidden])")
        self.assertEqual(self.page.inner_text("#painel-passos .seg.atual"), "10")
        self.assertIn("Passo 3 de", self.page.inner_text(".progresso"))

    def test_nova_analise_substitui_o_resultado_e_encerra_a_execucao_automatica(self):
        self.analisar_texto("a = 1\n")
        self.abrir_aba("passos")
        self.page.select_option("#sel-velocidade", "rapida")
        self.page.click("#btn-executar")
        self.analisar_texto("zzz = 2\n")
        self.page.wait_for_timeout(600)  # um timer antigo, se vivo, geraria erro JS (verificado no tearDown)
        self.abrir_aba("tabela")
        self.assertIn("zzz", [l[2] for l in self.linhas_da_tabela()])
        self.assertEqual(self.page.locator("#resultado .abas").count(), 1)

    # --- robustez
    def test_interface_nao_quebra_com_entradas_hostis(self):
        entradas = [
            "@@@ $$$ ??? ``", '"', "'", "((((((((", "))))", "\\", "\\\n\\", "x = " + "1" * 5000,
            "😀😀😀", "a = \x00\x01\x02", "<script>window.__xss=1</script>", '<img src=x onerror="window.__xss=1">',
            "\t\tx", "if x:\n        a\n    b\n", '"""abc', "# só comentário", "a" * 20000, "é" * 500, "1.2.3 0x1F 1e5 007 .5 5.",
            "x = 1" + "\n" * 300,
        ]
        for texto in entradas:
            with self.subTest(entrada=texto[:30]):
                self.analisar_texto(texto)
                self.assertTrue(self.page.locator("#resultado .abas").count() == 1)
                self.assertFalse(self.page.is_disabled("#btn-analisar"))
                self.assertNotRegex(self.resultado().inner_text(), r"Traceback|NaN|undefined|\[object")
        self.assertIsNone(self.page.evaluate("window.__xss"))

    def test_html_no_codigo_do_usuario_e_exibido_como_texto(self):
        self.analisar_texto('<img src=x onerror="window.__xss=1"> <b>negrito</b>')
        self.assertEqual(self.page.locator("#resultado img, #resultado script, #resultado .codigo-view b").count(), 0)
        self.assertIsNone(self.page.evaluate("window.__xss"))

    def test_programa_grande_ativa_modo_limitado(self):
        self.analisar_texto("x = 1\n" * 1500)
        self.assertEqual(self.page.locator("#aba-codigo").count(), 0)
        self.assertEqual(self.page.locator("#aba-passos").count(), 0)
        self.assertLessEqual(len(self.linhas_da_tabela()), 5000)
        self.assertIn("Programa grande", self.page.inner_text("#painel-tabela"))

    def test_codigo_vazio_continua_validado_antes_do_scanner(self):
        self.analisar()
        self.page.wait_for_selector('#resultado[data-estado="erro-entrada"]')
        self.assertEqual(self.page.locator("#resultado .abas").count(), 0)

    def test_abas_acessiveis_por_teclado_e_papel_aria(self):
        self.analisar_texto("a = 1\n")
        self.assertEqual(self.page.get_attribute("#aba-codigo", "aria-selected"), "true")
        self.assertEqual(self.page.get_attribute("#aba-tabela", "aria-selected"), "false")
        self.page.focus("#aba-tabela")
        self.page.keyboard.press("Enter")
        self.assertEqual(self.page.get_attribute("#aba-tabela", "aria-selected"), "true")
        self.assertTrue(self.page.locator("#painel-codigo").is_hidden())

    def test_ajuda_explica_token_e_lexema(self):
        self.assertFalse(self.page.locator("#ajuda-token").get_attribute("open") is not None)
        self.page.click("#ajuda-token summary")
        texto = self.page.inner_text("#ajuda-token")
        self.assertIn("Lexema", texto)
        self.assertIn("Token", texto)

    def test_layout_mobile_sem_rolagem_horizontal_da_pagina(self):
        self.page.set_viewport_size({"width": 390, "height": 800})
        self.page.select_option("#seletor-exemplo", "tokens")
        self.analisar()
        self.page.wait_for_selector(CONCLUIDO)
        for aba in ("codigo", "tabela", "passos"):
            self.abrir_aba(aba)
            largura = self.page.evaluate("[document.documentElement.scrollWidth, window.innerWidth]")
            self.assertLessEqual(largura[0], largura[1] + 1, "rolagem horizontal na aba " + aba)


class BackendForaDoArTest(unittest.TestCase):
    def test_mensagem_quando_o_backend_esta_fora_do_ar(self):
        with Ambiente(backend_no_ar=False) as amb, sync_playwright() as pw:
            browser = pw.chromium.launch(args=["--no-sandbox"])
            page = browser.new_page()
            page.goto(amb.url)
            page.fill("#codigo", "x = 1")
            page.click("#btn-analisar")
            page.wait_for_selector('#resultado[data-estado="erro-comunicacao"]')
            self.assertIn(MSG_COM, page.inner_text("#resultado"))
            self.assertFalse(page.is_disabled("#btn-analisar"))
            browser.close()


if __name__ == "__main__":
    unittest.main()
