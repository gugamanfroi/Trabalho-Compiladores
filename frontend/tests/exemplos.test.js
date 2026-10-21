const test = require("node:test");
const assert = require("node:assert/strict");
const Exemplos = require("../js/exemplos.js");
const { validarCodigo } = require("../js/validacao.js");

test("há pelo menos três exemplos", () => {
  assert.ok(Exemplos.length >= 3);
});

test("cada exemplo tem id, título, descrição e código não vazios", () => {
  for (const ex of Exemplos) {
    for (const campo of ["id", "titulo", "descricao", "codigo"]) {
      assert.equal(typeof ex[campo], "string", `${ex.id}.${campo}`);
      assert.ok(ex[campo].trim().length > 0, `${ex.id}.${campo} vazio`);
    }
  }
});

test("ids e códigos são únicos", () => {
  assert.equal(new Set(Exemplos.map((e) => e.id)).size, Exemplos.length);
  assert.equal(new Set(Exemplos.map((e) => e.codigo)).size, Exemplos.length);
});

test("todos os exemplos passam na validação de entrada", () => {
  for (const ex of Exemplos) assert.equal(validarCodigo(ex.codigo).valido, true, ex.id);
});
