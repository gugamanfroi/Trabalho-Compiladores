/* Lógica de apresentação dos tokens (sem DOM): categorias, eventos, segmentação
   do código para o destaque colorido e textos do passo a passo. */
(function (root, factory) {
  if (typeof module === "object" && module.exports) module.exports = factory();
  else root.Tokens = factory();
})(typeof self !== "undefined" ? self : this, function () {
  var CATEGORIAS = [
    { tipo: "PALAVRA_RESERVADA", rotulo: "Palavra reservada", estrutural: false },
    { tipo: "IDENTIFICADOR", rotulo: "Identificador", estrutural: false },
    { tipo: "LITERAL_INTEIRO", rotulo: "Literal inteiro", estrutural: false },
    { tipo: "LITERAL_REAL", rotulo: "Literal real", estrutural: false },
    { tipo: "LITERAL_STRING", rotulo: "Literal string", estrutural: false },
    { tipo: "OPERADOR", rotulo: "Operador", estrutural: false },
    { tipo: "DELIMITADOR", rotulo: "Delimitador", estrutural: false },
    { tipo: "NOVA_LINHA", rotulo: "Nova linha", estrutural: true },
    { tipo: "INDENTACAO", rotulo: "Indentação (abre bloco)", estrutural: true },
    { tipo: "DESINDENTACAO", rotulo: "Desindentação (fecha bloco)", estrutural: true },
    { tipo: "FIM_ARQUIVO", rotulo: "Fim do arquivo", estrutural: true },
  ];

  function categoria(tipo) {
    for (var i = 0; i < CATEGORIAS.length; i++) if (CATEGORIAS[i].tipo === tipo) return CATEGORIAS[i];
    return null;
  }
  function rotulo(tipo) { var c = categoria(tipo); return c ? c.rotulo : tipo; }
  function ehEstrutural(tipo) { var c = categoria(tipo); return !!(c && c.estrutural); }
  function tamanho(texto) { return Array.from(String(texto)).length; } // em caracteres (como o backend)

  /** Texto exibido para o lexema (tokens estruturais ganham um símbolo visível). */
  function simbolo(token) {
    switch (token.tipo) {
      case "NOVA_LINHA": return "↵";
      case "INDENTACAO": return "⇥ " + tamanho(token.lexema);
      case "DESINDENTACAO": return "⇤";
      case "FIM_ARQUIVO": return "∎";
      default: return token.lexema;
    }
  }

  function antes(a, b) { return a.linha < b.linha || (a.linha === b.linha && a.coluna < b.coluna); }

  /** Intercala tokens e erros em ordem de leitura. Em empate de posição, o token vem primeiro. */
  function construirEventos(tokens, erros) {
    var eventos = [], j = 0;
    erros = erros || [];
    (tokens || []).forEach(function (t, i) {
      while (j < erros.length && antes(erros[j], t)) eventos.push({ tipo: "erro", item: erros[j++] });
      eventos.push({ tipo: "token", item: t, tokenIndex: i });
    });
    while (j < erros.length) eventos.push({ tipo: "erro", item: erros[j++] });
    return eventos;
  }

  function dividirLacuna(texto, segs) {
    var i = texto.indexOf("#");
    if (i > 0) segs.push({ texto: texto.slice(0, i), tipo: null, classe: null, evs: [], erro: false });
    if (i >= 0) segs.push({ texto: texto.slice(i), tipo: null, classe: "comentario", evs: [], erro: false });
    else if (texto) segs.push({ texto: texto, tipo: null, classe: null, evs: [], erro: false });
  }

  /**
   * Divide o código em linhas e cada linha em segmentos:
   *   { texto, tipo, classe, evs:[índices de eventos], erro }
   * Trechos fora de qualquer token (espaços, comentários) viram segmentos sem eventos.
   * `fim` é o índice do evento NOVA_LINHA da linha (desenhado como ↵ após o texto).
   */
  function segmentar(codigo, eventos) {
    var linhas = String(codigo).split(/\r\n|\r|\n/);
    if (linhas.length > 1 && linhas[linhas.length - 1] === "") linhas.pop();
    var info = linhas.map(function () { return { spans: [], fim: null }; });

    eventos.forEach(function (ev, idx) {
      var it = ev.item, L = it.linha - 1;
      if (L < 0 || L >= linhas.length) return;
      if (ev.tipo === "token") {
        if (it.tipo === "NOVA_LINHA") { info[L].fim = idx; return; }
        if (it.tipo === "DESINDENTACAO" || it.tipo === "FIM_ARQUIVO") return;
      }
      var len = tamanho(it.lexema);
      if (len === 0) return;
      info[L].spans.push({
        inicio: it.coluna - 1, len: len, idx: idx, erro: ev.tipo === "erro",
        tipo: ev.tipo === "token" ? it.tipo : "ERRO",
      });
    });

    return linhas.map(function (texto, k) {
      var chars = Array.from(texto), segs = [], cursor = 0;
      info[k].spans
        .sort(function (a, b) { return a.inicio - b.inicio; })
        .forEach(function (sp) {
          var ult = segs.length ? segs[segs.length - 1] : null;
          if (ult && ult.inicio === sp.inicio && ult.len === sp.len) { // token e erro no mesmo trecho
            ult.evs.push(sp.idx);
            if (sp.erro) ult.erro = true;
            if (sp.tipo !== "ERRO") ult.tipo = sp.tipo;
            return;
          }
          if (sp.inicio < cursor) return; // sobreposição parcial: ignora
          if (sp.inicio > cursor) dividirLacuna(chars.slice(cursor, sp.inicio).join(""), segs);
          segs.push({
            texto: chars.slice(sp.inicio, sp.inicio + sp.len).join(""), tipo: sp.tipo,
            classe: null, evs: [sp.idx], erro: sp.erro, inicio: sp.inicio, len: sp.len,
          });
          cursor = sp.inicio + sp.len;
        });
      if (cursor < chars.length) dividirLacuna(chars.slice(cursor).join(""), segs);
      return { numero: k + 1, segmentos: segs, fim: info[k].fim };
    });
  }

  var REGRAS = {
    PALAVRA_RESERVADA:
      "Ele combina com a lista de palavras reservadas do Python. Por isso não pode ser usado como nome de variável.",
    IDENTIFICADOR:
      "Começa com letra ou “_” e segue com letras, dígitos ou “_”. Como não está na lista de palavras reservadas, é um nome (de variável ou função).",
    LITERAL_INTEIRO: "É uma sequência de dígitos, sem ponto decimal: um número inteiro escrito direto no código.",
    LITERAL_REAL: "São dígitos, um ponto e mais dígitos: um número real escrito direto no código.",
    LITERAL_STRING: "É um texto entre aspas simples ou duplas, fechado na mesma linha.",
    OPERADOR:
      "Representa uma operação ou comparação. O scanner sempre tenta o maior operador possível: lê “==” de uma vez, e não dois “=”.",
    DELIMITADOR: "É um sinal de pontuação que organiza o código: ( ) , :",
    NOVA_LINHA:
      "Em Python, o fim da linha termina a instrução. Linhas em branco, comentários e quebras dentro de parênteses não geram este token.",
    INDENTACAO: "A linha começa mais à direita que a anterior: um bloco foi aberto. Em Python, o recuo faz parte da gramática.",
    DESINDENTACAO:
      "A linha voltou a um recuo menor: um bloco foi fechado. Pode haver vários seguidos, um para cada bloco que fecha.",
    FIM_ARQUIVO: "O código acabou. Antes de terminar, o scanner fecha os blocos que ainda estavam abertos.",
  };

  /** Explicação de um evento do scanner para o passo a passo. */
  function explicar(ev) {
    var it = ev.item, pos = "linha " + it.linha + ", coluna " + it.coluna;
    if (ev.tipo === "erro") {
      return { titulo: "Erro léxico em " + pos, texto: it.mensagem, erro: true };
    }
    var estrutural = ehEstrutural(it.tipo);
    var titulo = estrutural
      ? "O scanner gerou o token " + it.tipo + " (" + pos + ")"
      : "O scanner leu o lexema “" + it.lexema + "” (" + pos + ") e o classificou como " + it.tipo;
    return { titulo: titulo, texto: REGRAS[it.tipo] || "", erro: false };
  }

  return {
    CATEGORIAS: CATEGORIAS, categoria: categoria, rotulo: rotulo, ehEstrutural: ehEstrutural,
    simbolo: simbolo, construirEventos: construirEventos, segmentar: segmentar, explicar: explicar,
    tamanho: tamanho,
  };
});
