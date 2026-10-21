const test = require("node:test");
const assert = require("node:assert/strict");
const { validarCodigo, MENSAGENS, TAMANHO_MAXIMO } = require("../js/validacao.js");

test("aceita código válido", () => {
  assert.deepEqual(validarCodigo("numero = 10\nprint(numero)\n"), { valido: true });
});

test("aceita código com erro sintático (não presume validade)", () => {
  assert.equal(validarCodigo("x = 10 +* 5").valido, true);
});

test("aceita caracteres especiais", () => {
  assert.equal(validarCodigo('print("ação ✓ <b>&amp;</b>")\t# \\').valido, true);
});

test("rejeita texto vazio", () => {
  const r = validarCodigo("");
  assert.equal(r.valido, false);
  assert.equal(r.tipo, "entrada_vazia");
  assert.equal(r.mensagem, "Informe um código-fonte antes de solicitar a análise.");
});

test("rejeita somente espaços, tabs e quebras de linha", () => {
  for (const t of ["   ", "\t", "\n\n", " \r\n\t "]) {
    const r = validarCodigo(t);
    assert.equal(r.valido, false, JSON.stringify(t));
    assert.equal(r.tipo, "entrada_somente_espacos");
  }
});

test("rejeita valores que não são texto", () => {
  for (const v of [null, undefined, 10, [], {}]) {
    assert.equal(validarCodigo(v).tipo, "entrada_vazia");
  }
});

test("respeita o limite de tamanho (igual ao do backend)", () => {
  assert.equal(TAMANHO_MAXIMO, 100000);
  assert.equal(validarCodigo("a".repeat(TAMANHO_MAXIMO)).valido, true);
  assert.equal(validarCodigo("a".repeat(TAMANHO_MAXIMO + 1)).tipo, "codigo_muito_grande");
});

test("mensagem de falha de comunicação é a especificada", () => {
  assert.equal(
    MENSAGENS.falha_comunicacao,
    "Não foi possível comunicar com o servidor. Verifique a conexão e tente novamente."
  );
});
