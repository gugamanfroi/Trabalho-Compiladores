import json
import unittest
from unittest import mock

from app import create_app
from validators import TAMANHO_MAXIMO_CODIGO


class ApiBase(unittest.TestCase):
    def setUp(self):
        self.client = create_app().test_client()

    def post_json(self, corpo):
        return self.client.post("/api/analisar", json=corpo)


class RegressaoEtapa1Test(ApiBase):
    def test_rota_raiz_continua_funcionando(self):
        r = self.client.get("/")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.get_json(), {"message": "Hello, World!"})

    def test_health(self):
        r = self.client.get("/health")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.get_json(), {"status": "ok"})


class AnalisarRequisicaoValidaTest(ApiBase):
    def test_codigo_valido(self):
        r = self.post_json({"codigo": "numero = 10\nprint(numero)"})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.content_type, "application/json")
        dados = r.get_json()
        self.assertTrue(dados["recebido"])
        # Etapa 3: a mensagem passou a descrever a análise léxica (mudança intencional).
        self.assertEqual(dados["mensagem"], "Análise léxica concluída sem erros: 10 tokens reconhecidos.")
        self.assertTrue(dados["sucesso"])
        self.assertEqual(dados["estatisticas"], {"linhas": 2, "caracteres": 25})

    def test_caracteres_especiais(self):
        codigo = 'print("ação ✓ <script>alert(1)</script>")\t# "aspas" \'simples\' \\'
        r = self.post_json({"codigo": codigo})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.get_json()["estatisticas"]["caracteres"], len(codigo))

    def test_codigo_sintaticamente_invalido_e_recebido(self):
        r = self.post_json({"codigo": "resultado = 10 +* 5"})
        self.assertEqual(r.status_code, 200)
        dados = r.get_json()
        self.assertTrue(dados["recebido"])
        self.assertTrue(dados["sucesso"])  # erro sintático não é erro léxico (parser: Etapa 4)

    def test_campo_extra_e_ignorado(self):
        r = self.post_json({"codigo": "x = 1", "extra": 123})
        self.assertEqual(r.status_code, 200)

    def test_json_enviado_como_texto_com_content_type_json(self):
        r = self.client.post(
            "/api/analisar",
            data=json.dumps({"codigo": "x = 1"}),
            content_type="application/json",
        )
        self.assertEqual(r.status_code, 200)

    def test_codigo_no_limite(self):
        r = self.post_json({"codigo": "a" * TAMANHO_MAXIMO_CODIGO})
        self.assertEqual(r.status_code, 200)


class AnalisarLexicoTest(ApiBase):
    """Contrato da Etapa 3: a resposta carrega tokens, erros e resumo."""

    def test_exemplo_do_enunciado_retorna_tokens_com_posicao(self):
        d = self.post_json({"codigo": "numero = 10\n"}).get_json()
        self.assertTrue(d["sucesso"])
        self.assertEqual(d["erros"], [])
        nao_estruturais = [t for t in d["tokens"] if t["tipo"] in
                           ("IDENTIFICADOR", "OPERADOR", "LITERAL_INTEIRO")]
        self.assertEqual(nao_estruturais, [
            {"tipo": "IDENTIFICADOR", "lexema": "numero", "linha": 1, "coluna": 1},
            {"tipo": "OPERADOR", "lexema": "=", "linha": 1, "coluna": 8},
            {"tipo": "LITERAL_INTEIRO", "lexema": "10", "linha": 1, "coluna": 10},
        ])

    def test_formato_de_cada_token(self):
        d = self.post_json({"codigo": "if a > 1:\n    b = \"x\"\n"}).get_json()
        for t in d["tokens"]:
            self.assertEqual(set(t), {"tipo", "lexema", "linha", "coluna"})
            self.assertIsInstance(t["lexema"], str)
            self.assertIsInstance(t["linha"], int)
            self.assertIsInstance(t["coluna"], int)
        self.assertEqual(d["tokens"][-1]["tipo"], "FIM_ARQUIVO")

    def test_erro_lexico_retorna_200_sucesso_false_e_lista_de_erros(self):
        r = self.post_json({"codigo": "a = 1\nb = 2 @ 3\n"})
        self.assertEqual(r.status_code, 200)  # a requisição foi processada; o erro está no código analisado
        d = r.get_json()
        self.assertTrue(d["recebido"])
        self.assertFalse(d["sucesso"])
        self.assertEqual(len(d["erros"]), 1)
        e = d["erros"][0]
        self.assertEqual(set(e), {"tipo", "subtipo", "lexema", "linha", "coluna", "mensagem"})
        self.assertEqual((e["tipo"], e["lexema"], e["linha"], e["coluna"]), ("ERRO_LEXICO", "@", 2, 7))
        self.assertIn("linha 2, coluna 7", e["mensagem"])
        self.assertIn("1 erro léxico", d["mensagem"])
        # tokens válidos continuam sendo devolvidos
        self.assertIn("b", [t["lexema"] for t in d["tokens"]])

    def test_varios_erros_sao_devolvidos_de_uma_vez(self):
        d = self.post_json({"codigo": 'x = $\ny = "aberta\nz = 12ab\n'}).get_json()
        self.assertFalse(d["sucesso"])
        self.assertEqual([e["linha"] for e in d["erros"]], [1, 2, 3])
        self.assertIn("3 erros léxicos", d["mensagem"])

    def test_resumo_consistente_com_as_listas(self):
        d = self.post_json({"codigo": "x = 1 + 2 @\n"}).get_json()
        r = d["resumo"]
        self.assertEqual(r["total_tokens"], len(d["tokens"]))
        self.assertEqual(r["total_erros"], len(d["erros"]))
        self.assertEqual(sum(r["por_categoria"].values()), len(d["tokens"]))
        self.assertEqual(r["por_categoria"]["OPERADOR"], 2)

    def test_contrato_da_etapa_2_foi_preservado(self):
        d = self.post_json({"codigo": "x = 1\ny = 2\n"}).get_json()
        self.assertTrue(d["recebido"])
        self.assertEqual(d["estatisticas"], {"linhas": 2, "caracteres": 12})

    def test_erro_sintatico_nao_e_erro_lexico(self):
        d = self.post_json({"codigo": "resultado = 10 +* 5\nif :\n"}).get_json()
        self.assertTrue(d["sucesso"])
        self.assertEqual(d["erros"], [])

    def test_caracteres_especiais_e_controle_geram_json_valido(self):
        for codigo in ["x = \u0000", "x = \ud800", "😀", "a\r\nb\rc", "x\x0b= 1"]:
            with self.subTest(codigo=repr(codigo)):
                r = self.post_json({"codigo": codigo})
                self.assertEqual(r.status_code, 200)
                self.assertIn("tokens", r.get_json())

    def test_codigo_no_limite_de_tamanho_e_tokenizado(self):
        r = self.post_json({"codigo": "x = 1\n" * 16000})  # ~96 mil caracteres
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.get_json()["sucesso"])

    def test_entrada_vazia_continua_tratada_como_na_etapa_2(self):
        for codigo, tipo in [("", "entrada_vazia"), ("  \n\t", "entrada_somente_espacos")]:
            r = self.post_json({"codigo": codigo})
            self.assertEqual(r.status_code, 422)
            self.assertEqual(r.get_json()["erro"]["tipo"], tipo)
            self.assertNotIn("tokens", r.get_json())


class AnalisarRequisicaoInvalidaTest(ApiBase):
    def assertErro(self, resposta, status, tipo):
        self.assertEqual(resposta.status_code, status)
        self.assertEqual(resposta.content_type, "application/json")
        dados = resposta.get_json()
        self.assertFalse(dados["recebido"])
        self.assertEqual(dados["erro"]["tipo"], tipo)
        self.assertTrue(dados["erro"]["mensagem"])

    def test_vazio(self):
        r = self.post_json({"codigo": ""})
        self.assertErro(r, 422, "entrada_vazia")
        self.assertEqual(
            r.get_json()["erro"]["mensagem"],
            "Informe um código-fonte antes de solicitar a análise.",
        )

    def test_somente_espacos(self):
        self.assertErro(self.post_json({"codigo": "  \n\t "}), 422, "entrada_somente_espacos")

    def test_campo_ausente(self):
        self.assertErro(self.post_json({}), 400, "requisicao_invalida")

    def test_campo_com_tipo_errado(self):
        for valor in [None, 42, ["x"], {"a": 1}]:
            with self.subTest(valor=valor):
                self.assertErro(self.post_json({"codigo": valor}), 400, "requisicao_invalida")

    def test_corpo_json_nao_e_objeto(self):
        self.assertErro(self.post_json(["x = 1"]), 400, "requisicao_invalida")

    def test_json_malformado(self):
        r = self.client.post(
            "/api/analisar", data="{codigo: ", content_type="application/json"
        )
        self.assertErro(r, 400, "requisicao_invalida")

    def test_corpo_vazio(self):
        r = self.client.post("/api/analisar", content_type="application/json")
        self.assertErro(r, 400, "requisicao_invalida")

    def test_content_type_que_nao_e_json(self):
        r = self.client.post("/api/analisar", data="codigo=x", content_type="text/plain")
        self.assertErro(r, 400, "requisicao_invalida")

    def test_codigo_acima_do_limite(self):
        r = self.post_json({"codigo": "a" * (TAMANHO_MAXIMO_CODIGO + 1)})
        self.assertErro(r, 413, "codigo_muito_grande")

    def test_corpo_gigante_e_rejeitado_pelo_servidor(self):
        r = self.post_json({"codigo": "a" * (2 * 1024 * 1024)})
        self.assertErro(r, 413, "codigo_muito_grande")

    def test_metodo_nao_permitido(self):
        self.assertErro(self.client.get("/api/analisar"), 405, "metodo_nao_permitido")

    def test_rota_inexistente(self):
        self.assertErro(self.client.get("/api/nao-existe"), 404, "recurso_nao_encontrado")


class ErroInesperadoTest(unittest.TestCase):
    def test_erro_interno_nao_expoe_detalhes(self):
        app = create_app()
        client = app.test_client()
        segredo = "/srv/interno/segredo.py SENHA=abc123"
        with mock.patch("app.processar_codigo", side_effect=RuntimeError(segredo)):
            with self.assertLogs(app.logger, level="ERROR"):
                r = client.post("/api/analisar", json={"codigo": "x = 1"})
        self.assertEqual(r.status_code, 500)
        dados = r.get_json()
        self.assertFalse(dados["recebido"])
        self.assertEqual(dados["erro"]["tipo"], "erro_interno")
        texto = r.get_data(as_text=True)
        self.assertNotIn("segredo", texto)
        self.assertNotIn("abc123", texto)
        self.assertNotIn("Traceback", texto)


if __name__ == "__main__":
    unittest.main()
