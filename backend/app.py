from flask import Flask, jsonify, request
from werkzeug.exceptions import HTTPException

from analisador import processar_codigo
from validators import ErroValidacao, validar_requisicao

LIMITE_CORPO_BYTES = 1024 * 1024  # 1 MiB; evita corpos absurdamente grandes

MSG_ERRO_INTERNO = (
    "Ocorreu um erro inesperado ao processar a requisição. "
    "Tente novamente em instantes."
)

_TIPOS_HTTP = {
    404: ("recurso_nao_encontrado", "Recurso não encontrado."),
    405: ("metodo_nao_permitido", "Método não permitido para este recurso."),
    413: ("codigo_muito_grande", "O código enviado é grande demais para ser processado."),
}


def _erro(tipo, mensagem, status):
    corpo = {"recebido": False, "erro": {"tipo": tipo, "mensagem": mensagem}}
    return jsonify(corpo), status


def create_app():
    app = Flask(__name__)
    app.config["MAX_CONTENT_LENGTH"] = LIMITE_CORPO_BYTES

    try:  # CORS só é necessário se o frontend for servido por outra origem
        from flask_cors import CORS

        CORS(app)
    except ImportError:  # pragma: no cover
        pass

    @app.route("/")
    def hello():  # mantido da etapa 1 (teste de regressão)
        return jsonify({"message": "Hello, World!"})

    @app.route("/health")
    def health():
        return jsonify({"status": "ok"})

    @app.route("/api/analisar", methods=["POST"])
    def analisar():
        payload = request.get_json(silent=True)
        codigo = validar_requisicao(payload)  # levanta ErroValidacao
        return jsonify(processar_codigo(codigo)), 200

    @app.errorhandler(ErroValidacao)
    def tratar_validacao(e):
        return _erro(e.tipo, e.mensagem, e.status)

    @app.errorhandler(HTTPException)
    def tratar_http(e):
        tipo, msg = _TIPOS_HTTP.get(
            e.code, ("requisicao_invalida", "A requisição não pôde ser processada.")
        )
        return _erro(tipo, msg, e.code)

    @app.errorhandler(Exception)
    def tratar_inesperado(e):
        # Detalhes ficam só no log do servidor; o usuário recebe mensagem genérica.
        app.logger.exception("Erro inesperado")
        return _erro("erro_interno", MSG_ERRO_INTERNO, 500)

    return app


app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
