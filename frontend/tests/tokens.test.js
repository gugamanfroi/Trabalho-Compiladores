const test = require("node:test");
const assert = require("node:assert/strict");
const T = require("../js/tokens.js");

const tk = (tipo, lexema, linha, coluna) => ({ tipo, lexema, linha, coluna });
const er = (lexema, linha, coluna, mensagem = "msg") => ({ tipo: "ERRO_LEXICO", lexema, linha, coluna, mensagem });

test("categorias: 11 categorias, estruturais identificadas", () => {
  assert.equal(T.CATEGORIAS.length, 11);
  for (const t of ["NOVA_LINHA", "INDENTACAO", "DESINDENTACAO", "FIM_ARQUIVO"]) assert.equal(T.ehEstrutural(t), true, t);
  for (const t of ["IDENTIFICADOR", "OPERADOR", "LITERAL_STRING"]) assert.equal(T.ehEstrutural(t), false, t);
  assert.equal(T.ehEstrutural("INEXISTENTE"), false);
  assert.equal(T.rotulo("PALAVRA_RESERVADA"), "Palavra reservada");
  assert.equal(T.rotulo("XYZ"), "XYZ");
});

test("símbolos dos tokens estruturais são visíveis", () => {
  assert.equal(T.simbolo(tk("NOVA_LINHA", "\n", 1, 1)), "↵");
  assert.equal(T.simbolo(tk("INDENTACAO", "    ", 2, 1)), "⇥ 4");
  assert.equal(T.simbolo(tk("DESINDENTACAO", "", 3, 1)), "⇤");
  assert.equal(T.simbolo(tk("FIM_ARQUIVO", "", 4, 1)), "∎");
  assert.equal(T.simbolo(tk("IDENTIFICADOR", "numero", 1, 1)), "numero");
});

test("construirEventos intercala erros na ordem de leitura; em empate o token vem primeiro", () => {
  const tokens = [tk("IDENTIFICADOR", "a", 1, 1), tk("DELIMITADOR", "(", 1, 5), tk("FIM_ARQUIVO", "", 3, 1)];
  const erros = [er("(", 1, 5), er("@", 2, 2)];
  const ev = T.construirEventos(tokens, erros);
  assert.deepEqual(ev.map((e) => e.tipo + ":" + e.item.lexema), ["token:a", "token:(", "erro:(", "erro:@", "token:"]);
  assert.equal(ev[1].tokenIndex, 1);
  assert.deepEqual(T.construirEventos([], []), []);
  assert.equal(T.construirEventos(undefined, undefined).length, 0);
});

test("segmentar: tokens, espaços e comentário da linha", () => {
  const codigo = "x = 10  # nota\n";
  const tokens = [tk("IDENTIFICADOR", "x", 1, 1), tk("OPERADOR", "=", 1, 3), tk("LITERAL_INTEIRO", "10", 1, 5),
    tk("NOVA_LINHA", "\n", 1, 15), tk("FIM_ARQUIVO", "", 2, 1)];
  const linhas = T.segmentar(codigo, T.construirEventos(tokens, []));
  assert.equal(linhas.length, 1); // a linha vazia final é descartada
  const segs = linhas[0].segmentos;
  assert.deepEqual(segs.map((s) => s.texto), ["x", " ", "=", " ", "10", "  ", "# nota"]);
  assert.equal(segs[0].tipo, "IDENTIFICADOR");
  assert.equal(segs[1].tipo, null);
  assert.equal(segs[6].classe, "comentario");
  assert.equal(segs.map((s) => s.texto).join(""), "x = 10  # nota"); // nada se perde nem se duplica
  assert.equal(linhas[0].fim, 3); // índice do evento NOVA_LINHA
});

test("segmentar: o texto reconstruído é idêntico ao código, linha a linha", () => {
  const codigo = "if a:\n    b = 'c'  # d\n\nz = 1";
  const tokens = [tk("PALAVRA_RESERVADA", "if", 1, 1), tk("IDENTIFICADOR", "a", 1, 4), tk("DELIMITADOR", ":", 1, 5),
    tk("NOVA_LINHA", "\n", 1, 6), tk("INDENTACAO", "    ", 2, 1), tk("IDENTIFICADOR", "b", 2, 5), tk("OPERADOR", "=", 2, 7),
    tk("LITERAL_STRING", "'c'", 2, 9), tk("NOVA_LINHA", "\n", 2, 20), tk("DESINDENTACAO", "", 4, 1),
    tk("IDENTIFICADOR", "z", 4, 1), tk("OPERADOR", "=", 4, 3), tk("LITERAL_INTEIRO", "1", 4, 5), tk("NOVA_LINHA", "", 4, 6),
    tk("FIM_ARQUIVO", "", 5, 1)];
  const linhas = T.segmentar(codigo, T.construirEventos(tokens, []));
  assert.deepEqual(linhas.map((l) => l.segmentos.map((s) => s.texto).join("")), codigo.split("\n"));
  assert.equal(linhas[1].segmentos[0].tipo, "INDENTACAO");
});

test("segmentar: colunas contam caracteres, não unidades UTF-16 (emoji)", () => {
  const codigo = 's = "😀" + x';
  const tokens = [tk("IDENTIFICADOR", "s", 1, 1), tk("OPERADOR", "=", 1, 3), tk("LITERAL_STRING", '"😀"', 1, 5),
    tk("OPERADOR", "+", 1, 9), tk("IDENTIFICADOR", "x", 1, 11)];
  const [l] = T.segmentar(codigo, T.construirEventos(tokens, []));
  assert.deepEqual(l.segmentos.filter((s) => s.tipo).map((s) => s.texto), ["s", "=", '"😀"', "+", "x"]);
});

test("segmentar: erro e token no mesmo trecho viram um só segmento com os dois eventos", () => {
  const eventos = T.construirEventos([tk("DELIMITADOR", "(", 1, 5)], [er("(", 1, 5)]);
  const [l] = T.segmentar("a = (1", eventos);
  const seg = l.segmentos.find((s) => s.texto === "(");
  assert.deepEqual(seg.evs, [0, 1]);
  assert.equal(seg.erro, true);
  assert.equal(seg.tipo, "DELIMITADOR");
});

test("segmentar: erro léxico isolado", () => {
  const [l] = T.segmentar("a = @", T.construirEventos([tk("IDENTIFICADOR", "a", 1, 1)], [er("@", 1, 5)]));
  const seg = l.segmentos[l.segmentos.length - 1];
  assert.equal(seg.texto, "@");
  assert.equal(seg.erro, true);
  assert.equal(seg.tipo, "ERRO");
});

test("segmentar: lida com CRLF, código vazio e posições fora do código", () => {
  assert.equal(T.segmentar("a\r\nb\r\n", []).length, 2);
  assert.equal(T.segmentar("", []).length, 1);
  const fora = T.construirEventos([tk("IDENTIFICADOR", "z", 99, 1)], []);
  assert.doesNotThrow(() => T.segmentar("a = 1", fora));
});

test("explicar: token comum, estrutural e erro", () => {
  const ev = T.construirEventos([tk("IDENTIFICADOR", "numero", 1, 1), tk("NOVA_LINHA", "\n", 1, 7)], [er("@", 2, 1, "Erro léxico na linha 2, coluna 1: x")]);
  const a = T.explicar(ev[0]);
  assert.match(a.titulo, /“numero”.*linha 1, coluna 1.*IDENTIFICADOR/);
  assert.equal(a.erro, false);
  assert.ok(a.texto.length > 10);
  const b = T.explicar(ev[1]);
  assert.match(b.titulo, /NOVA_LINHA/);
  const c = T.explicar(ev[2]);
  assert.equal(c.erro, true);
  assert.equal(c.texto, "Erro léxico na linha 2, coluna 1: x");
});

test("explicar: toda categoria tem uma explicação", () => {
  for (const c of T.CATEGORIAS) {
    const ex = T.explicar({ tipo: "token", item: tk(c.tipo, "x", 1, 1) });
    assert.ok(ex.texto.length > 10, c.tipo);
  }
});
