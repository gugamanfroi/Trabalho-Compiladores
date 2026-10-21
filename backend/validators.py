"""Validação da entrada recebida pelo backend.

O backend não confia nas verificações feitas pelo frontend: todo payload é
validado aqui antes de ser entregue ao analisador.
"""

TAMANHO_MAXIMO_CODIGO = 100_000  # caracteres

MSG_ENTRADA_VAZIA = "Informe um código-fonte antes de solicitar a análise."
MSG_SOMENTE_ESPACOS = (
    "O código informado contém apenas espaços em branco. "
    "Digite um programa para ser analisado."
)


class ErroValidacao(Exception):
    """Erro de entrada com tipo estável (para o frontend) e status HTTP."""

    def __init__(self, tipo, mensagem, status):
        super().__init__(mensagem)
        self.tipo = tipo
        self.mensagem = mensagem
        self.status = status


def validar_requisicao(payload):
    """Valida o corpo JSON e devolve o código-fonte (str).

    Levanta ErroValidacao quando a entrada não pode ser processada:
      400 requisicao_invalida        -> corpo ausente/mal formado, campo ausente ou de tipo errado
      422 entrada_vazia              -> código vazio
      422 entrada_somente_espacos    -> código só com espaços/quebras de linha
      413 codigo_muito_grande        -> código acima do limite
    """
    if not isinstance(payload, dict):
        raise ErroValidacao(
            "requisicao_invalida",
            "O corpo da requisição deve ser um objeto JSON com o campo 'codigo'.",
            400,
        )
    if "codigo" not in payload:
        raise ErroValidacao(
            "requisicao_invalida", "O campo 'codigo' é obrigatório.", 400
        )

    codigo = payload["codigo"]
    if not isinstance(codigo, str):
        raise ErroValidacao(
            "requisicao_invalida", "O campo 'codigo' deve ser um texto.", 400
        )
    if codigo == "":
        raise ErroValidacao("entrada_vazia", MSG_ENTRADA_VAZIA, 422)
    if codigo.strip() == "":
        raise ErroValidacao("entrada_somente_espacos", MSG_SOMENTE_ESPACOS, 422)
    if len(codigo) > TAMANHO_MAXIMO_CODIGO:
        raise ErroValidacao(
            "codigo_muito_grande",
            "O código excede o limite de %d caracteres." % TAMANHO_MAXIMO_CODIGO,
            413,
        )
    return codigo
