"""Ponto de entrada do processamento do código-fonte.

Etapa 3: executa o analisador léxico (scanner). As próximas etapas encadearão
aqui o parser (Etapa 4) e a análise semântica (Etapa 5), sem alterar as rotas.
"""
from scanner import analisar_lexico


def _plural(n, singular, plural):
    return "%d %s" % (n, singular if n == 1 else plural)


def processar_codigo(codigo):
    """Recebe um código já validado e devolve o resultado do processamento."""
    lexico = analisar_lexico(codigo)
    resumo = lexico["resumo"]
    tokens = _plural(resumo["total_tokens"], "token reconhecido", "tokens reconhecidos")

    if lexico["sucesso"]:
        mensagem = "Análise léxica concluída sem erros: %s." % tokens
    else:
        mensagem = "Análise léxica concluída com %s. %s." % (
            _plural(resumo["total_erros"], "erro léxico", "erros léxicos"), tokens)

    return {
        "recebido": True,
        "sucesso": lexico["sucesso"],
        "mensagem": mensagem,
        "estatisticas": {
            "linhas": len(codigo.splitlines()),
            "caracteres": len(codigo),
        },
        "tokens": lexico["tokens"],
        "erros": lexico["erros"],
        "resumo": resumo,
    }
