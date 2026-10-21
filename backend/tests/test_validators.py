import unittest

from validators import (
    TAMANHO_MAXIMO_CODIGO,
    ErroValidacao,
    validar_requisicao,
)


class ValidarRequisicaoTest(unittest.TestCase):
    def assertErro(self, payload, tipo, status):
        with self.assertRaises(ErroValidacao) as ctx:
            validar_requisicao(payload)
        self.assertEqual(ctx.exception.tipo, tipo)
        self.assertEqual(ctx.exception.status, status)

    def test_codigo_valido_e_devolvido_sem_alteracao(self):
        codigo = "  x = 1\n"
        self.assertEqual(validar_requisicao({"codigo": codigo}), codigo)

    def test_caracteres_especiais_sao_aceitos(self):
        codigo = 'print("olá, mundo ✓")  # <b>&amp;</b> \t\r\n'
        self.assertEqual(validar_requisicao({"codigo": codigo}), codigo)

    def test_codigo_com_erro_sintatico_e_aceito(self):
        # O sistema não presume que o código é válido (etapas futuras o analisarão).
        self.assertEqual(validar_requisicao({"codigo": "x = 10 +* 5"}), "x = 10 +* 5")

    def test_vazio(self):
        self.assertErro({"codigo": ""}, "entrada_vazia", 422)

    def test_somente_espacos_tabs_e_quebras(self):
        for texto in ["   ", "\t", "\n\n", " \r\n\t "]:
            with self.subTest(texto=repr(texto)):
                self.assertErro({"codigo": texto}, "entrada_somente_espacos", 422)

    def test_campo_ausente(self):
        self.assertErro({}, "requisicao_invalida", 400)
        self.assertErro({"code": "x = 1"}, "requisicao_invalida", 400)

    def test_tipos_invalidos_para_codigo(self):
        for valor in [None, 10, 1.5, True, ["x = 1"], {"a": 1}]:
            with self.subTest(valor=valor):
                self.assertErro({"codigo": valor}, "requisicao_invalida", 400)

    def test_payload_que_nao_e_objeto(self):
        for payload in [None, "x = 1", 42, ["codigo"]]:
            with self.subTest(payload=payload):
                self.assertErro(payload, "requisicao_invalida", 400)

    def test_limite_de_tamanho(self):
        ok = "a" * TAMANHO_MAXIMO_CODIGO
        self.assertEqual(validar_requisicao({"codigo": ok}), ok)
        self.assertErro({"codigo": ok + "a"}, "codigo_muito_grande", 413)


if __name__ == "__main__":
    unittest.main()
