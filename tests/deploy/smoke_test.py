"""Teste de implantação: verifica uma instância já em execução.

Uso:  python tests/deploy/smoke_test.py [URL_BASE]     (padrão: http://localhost:8080)
Confirma que o frontend responde, que o proxy chega ao backend e que o
contrato de /api/analisar está sendo cumprido na stack em execução.
"""
import json
import sys
import urllib.error
import urllib.request

BASE = (sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8080").rstrip("/")
falhas = []


def req(caminho, corpo=None):
    dados = json.dumps(corpo).encode() if corpo is not None else None
    r = urllib.request.Request(BASE + caminho, data=dados,
                               headers={"Content-Type": "application/json"} if dados else {})
    try:
        with urllib.request.urlopen(r, timeout=10) as resp:
            return resp.status, resp.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()


def checar(nome, condicao):
    print(("OK    " if condicao else "FALHA ") + nome)
    if not condicao:
        falhas.append(nome)


s, corpo = req("/")
checar("frontend: GET / -> 200 com o título do sistema", s == 200 and "Compilador Educacional" in corpo)
for arq in ["style.css", "js/validacao.js", "js/exemplos.js", "js/api.js", "js/tokens.js", "js/resultado.js", "js/app.js"]:
    checar("frontend: arquivo estático %s -> 200" % arq, req("/" + arq)[0] == 200)
s, corpo = req("/health")
checar("proxy: GET /health chega ao backend", s == 200 and json.loads(corpo) == {"status": "ok"})
s, corpo = req("/api/analisar", {"codigo": "numero = 10\nprint(numero)\n"})
d = json.loads(corpo)
checar("API: código válido -> 200, recebido, sucesso léxico e estatísticas",
       s == 200 and d["recebido"] is True and d["sucesso"] is True and d["erros"] == []
       and d["estatisticas"] == {"linhas": 2, "caracteres": 26})
checar("API: tokens com tipo, lexema, linha e coluna",
       {"tipo": "IDENTIFICADOR", "lexema": "numero", "linha": 1, "coluna": 1} in d["tokens"]
       and {"tipo": "LITERAL_INTEIRO", "lexema": "10", "linha": 1, "coluna": 10} in d["tokens"]
       and d["tokens"][-1]["tipo"] == "FIM_ARQUIVO")
s, corpo = req("/api/analisar", {"codigo": "a = 1 @ 2\n"})
d = json.loads(corpo)
checar("API: erro léxico -> 200, sucesso=false, erro localizado",
       s == 200 and d["sucesso"] is False and len(d["erros"]) == 1
       and (d["erros"][0]["lexema"], d["erros"][0]["linha"], d["erros"][0]["coluna"]) == ("@", 1, 7))
s, corpo = req("/api/analisar", {"codigo": "   "})
checar("API: somente espaços -> 422", s == 422 and json.loads(corpo)["erro"]["tipo"] == "entrada_somente_espacos")
s, corpo = req("/api/analisar", {})
checar("API: campo ausente -> 400", s == 400 and json.loads(corpo)["erro"]["tipo"] == "requisicao_invalida")

print("\n%s" % ("Todas as verificações passaram." if not falhas else "%d verificação(ões) falharam." % len(falhas)))
sys.exit(1 if falhas else 0)
