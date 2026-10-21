const test = require("node:test");
const assert = require("node:assert/strict");
const { enviarCodigo } = require("../js/api.js");
const { MENSAGENS } = require("../js/validacao.js");

const resp = (status, corpo, { json = true } = {}) => ({
  ok: status >= 200 && status < 300,
  status,
  json: async () => {
    if (!json) throw new SyntaxError("Unexpected token <");
    return corpo;
  },
});

test("envia POST JSON com o campo 'codigo' para /api/analisar", async () => {
  let chamada;
  const fakeFetch = async (url, init) => {
    chamada = { url, init };
    return resp(200, { recebido: true, mensagem: "Código recebido com sucesso.", estatisticas: { linhas: 1, caracteres: 6 } });
  };
  const r = await enviarCodigo("x = 1\n", { fetch: fakeFetch });
  assert.equal(chamada.url, "/api/analisar");
  assert.equal(chamada.init.method, "POST");
  assert.equal(chamada.init.headers["Content-Type"], "application/json");
  assert.deepEqual(JSON.parse(chamada.init.body), { codigo: "x = 1\n" });
  assert.equal(r.ok, true);
  assert.equal(r.mensagem, "Código recebido com sucesso.");
  assert.equal(r.dados.estatisticas.linhas, 1);
});

test("preserva caracteres especiais no corpo enviado", async () => {
  const codigo = 'print("ação ✓ <b>")\t\\ \r\n';
  let corpo;
  await enviarCodigo(codigo, { fetch: async (_u, i) => { corpo = i.body; return resp(200, { recebido: true, mensagem: "ok" }); } });
  assert.equal(JSON.parse(corpo).codigo, codigo);
});

test("erro de validação do backend (422) mantém tipo e mensagem", async () => {
  const f = async () => resp(422, { recebido: false, erro: { tipo: "entrada_vazia", mensagem: "Informe um código-fonte antes de solicitar a análise." } });
  const r = await enviarCodigo("x", { fetch: f });
  assert.deepEqual(r, { ok: false, tipo: "entrada_vazia", mensagem: "Informe um código-fonte antes de solicitar a análise." });
});

test("requisição inválida (400) é tratada como erro de entrada", async () => {
  const f = async () => resp(400, { recebido: false, erro: { tipo: "requisicao_invalida", mensagem: "O campo 'codigo' é obrigatório." } });
  const r = await enviarCodigo("x", { fetch: f });
  assert.equal(r.ok, false);
  assert.equal(r.tipo, "requisicao_invalida");
});

test("rede indisponível (fetch rejeita) vira falha de comunicação", async () => {
  const f = async () => { throw new TypeError("Failed to fetch"); };
  const r = await enviarCodigo("x", { fetch: f });
  assert.deepEqual(r, { ok: false, tipo: "falha_comunicacao", mensagem: MENSAGENS.falha_comunicacao });
});

test("timeout (AbortError) vira falha de comunicação", async () => {
  const f = (_u, init) => new Promise((_res, rej) => init.signal.addEventListener("abort", () => rej(new DOMException("Aborted", "AbortError"))));
  const r = await enviarCodigo("x", { fetch: f, timeoutMs: 20 });
  assert.equal(r.tipo, "falha_comunicacao");
});

test("502 do proxy com HTML vira falha de comunicação", async () => {
  const f = async () => resp(502, null, { json: false });
  const r = await enviarCodigo("x", { fetch: f });
  assert.equal(r.tipo, "falha_comunicacao");
});

test("500 com JSON do backend vira erro genérico sem detalhes internos", async () => {
  const f = async () => resp(500, { recebido: false, erro: { tipo: "erro_interno", mensagem: "Ocorreu um erro inesperado ao processar a requisição. Tente novamente em instantes." } });
  const r = await enviarCodigo("x", { fetch: f });
  assert.equal(r.ok, false);
  assert.equal(r.tipo, "erro_interno");
  assert.doesNotMatch(r.mensagem, /Traceback|\.py/);
});

test("200 com corpo inesperado não é tratado como sucesso", async () => {
  const f = async () => resp(200, { qualquer: "coisa" });
  const r = await enviarCodigo("x", { fetch: f });
  assert.equal(r.ok, false);
  assert.equal(r.tipo, "erro_inesperado");
});

test("resposta 4xx não-JSON vira erro inesperado ou comunicação, nunca sucesso", async () => {
  const r = await enviarCodigo("x", { fetch: async () => resp(404, null, { json: false }) });
  assert.equal(r.ok, false);
});
