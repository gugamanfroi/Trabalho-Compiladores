/* Cliente do backend: envia o código e normaliza qualquer resposta/falha. */
(function (root, factory) {
  if (typeof module === "object" && module.exports) module.exports = factory(require("./validacao.js"));
  else root.Api = factory(root.Validacao);
})(typeof self !== "undefined" ? self : this, function (Validacao) {
  var M = Validacao.MENSAGENS;

  /**
   * Resultado normalizado:
   *   { ok: true,  mensagem, dados }
   *   { ok: false, tipo, mensagem }   tipo: tipo do backend | falha_comunicacao | erro_inesperado
   */
  async function enviarCodigo(codigo, opcoes) {
    opcoes = opcoes || {};
    var fetchFn = opcoes.fetch || (typeof fetch !== "undefined" ? fetch.bind(globalThis) : null);
    var url = opcoes.url || "/api/analisar";
    var timeoutMs = opcoes.timeoutMs || 10000;

    var controller = typeof AbortController !== "undefined" ? new AbortController() : null;
    var timer = controller ? setTimeout(function () { controller.abort(); }, timeoutMs) : null;

    var resposta;
    try {
      resposta = await fetchFn(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ codigo: codigo }),
        signal: controller ? controller.signal : undefined,
      });
    } catch (e) {
      return { ok: false, tipo: "falha_comunicacao", mensagem: M.falha_comunicacao };
    } finally {
      if (timer) clearTimeout(timer);
    }

    var dados = null;
    try { dados = await resposta.json(); } catch (e) { dados = null; }

    if (resposta.ok && dados && dados.recebido === true) {
      return { ok: true, mensagem: dados.mensagem, dados: dados };
    }
    if (dados && dados.erro && typeof dados.erro.mensagem === "string") {
      return { ok: false, tipo: dados.erro.tipo || "erro_inesperado", mensagem: dados.erro.mensagem };
    }
    // Sem JSON utilizável: proxy/servidor fora do ar (502/503/504) ou resposta estranha.
    if ([502, 503, 504].indexOf(resposta.status) !== -1 || dados === null) {
      return { ok: false, tipo: "falha_comunicacao", mensagem: M.falha_comunicacao };
    }
    return { ok: false, tipo: "erro_inesperado", mensagem: M.erro_inesperado };
  }

  return { enviarCodigo: enviarCodigo };
});
