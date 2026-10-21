"""Ponto de entrada do processamento do código-fonte.

Na etapa 2 o código apenas é recebido e contabilizado. Nas próximas etapas
as análises léxica, sintática e semântica serão encadeadas aqui, sem
alterar as rotas HTTP.
"""


def processar_codigo(codigo):
    """Recebe um código já validado e devolve o resultado do processamento."""
    return {
        "recebido": True,
        "mensagem": "Código recebido com sucesso.",
        "estatisticas": {
            "linhas": len(codigo.splitlines()),
            "caracteres": len(codigo),
        },
    }
