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
}


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
                self.page.wait_for_selector('#resultado[data-estado="sucesso"]')
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
        self.assertIn("Código recebido com sucesso.", texto)
        self.assertRegex(texto, r"Linhas recebidas\s+4")
        self.assertRegex(texto, r"Caracteres recebidos\s+%d" % len(EXEMPLOS["condicional"]))
        self.assertIn("próximas etapas", texto)

    def test_todos_os_exemplos_sao_aceitos_pelo_backend(self):
        for id_ in EXEMPLOS:  # inclui o exemplo com erro intencional
            with self.subTest(exemplo=id_):
                self.page.select_option("#seletor-exemplo", id_)
                self.analisar()
                self.page.wait_for_selector('#resultado[data-estado="sucesso"]')

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
