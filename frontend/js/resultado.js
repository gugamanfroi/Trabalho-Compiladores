/* Renderização do resultado da análise léxica: resumo, erros, código destacado,
   tabela de tokens e passo a passo. Todo texto vindo do servidor ou do código do
   usuário entra na página via textContent (nunca como HTML). */
(function (root, factory) {
  if (typeof module === "object" && module.exports) module.exports = factory(require("./tokens.js"));
  else root.Resultado = factory(root.Tokens);
})(typeof self !== "undefined" ? self : this, function (Tokens) {
  var LIMITE_VISUAL = 5000; // acima disso, só a tabela (limitada) é exibida
  var VELOCIDADES = { lenta: 1200, normal: 700, rapida: 250 };
  var timer = null;

  function el(tag, attrs, filhos) {
    var e = document.createElement(tag);
    Object.keys(attrs || {}).forEach(function (k) {
      if (k === "class") e.className = attrs[k];
      else if (k === "text") e.textContent = attrs[k];
      else if (k.slice(0, 2) === "on") e.addEventListener(k.slice(2), attrs[k]);
      else e.setAttribute(k, attrs[k]);
    });
    (filhos || []).forEach(function (f) {
      if (f) e.appendChild(typeof f === "string" ? document.createTextNode(f) : f);
    });
    return e;
  }

  function parar() { if (timer) { clearInterval(timer); timer = null; } }

  // ------------------------------------------------------------ código
  /** Monta o código em linhas numeradas, com um <span> por segmento. */
  function construirCodigo(codigo, eventos) {
    var linhas = Tokens.segmentar(codigo, eventos);
    var raiz = el("div", { class: "codigo-view", role: "region", "aria-label": "Código-fonte com tokens destacados" });
    var spans = [], marcadores = [];
    linhas.forEach(function (l) {
      var linha = el("div", { class: "linha" }, [el("span", { class: "num", text: String(l.numero), "aria-hidden": "true" })]);
      var texto = el("span", { class: "texto" });
      l.segmentos.forEach(function (s) {
        var cls = "seg";
        if (s.tipo && s.tipo !== "ERRO") cls += " tk-" + s.tipo;
        if (s.classe) cls += " " + s.classe;
        if (s.erro) cls += " erro-lexico";
        var e = el("span", { class: cls, text: s.texto });
        if (s.tipo) e.setAttribute("data-tipo", s.tipo);
        if (s.erro) e.setAttribute("data-erro", "1");
        if (s.evs.length) { e.setAttribute("data-ev", s.evs.join(" ")); spans.push({ el: e, evs: s.evs }); }
        texto.appendChild(e);
      });
      if (l.fim !== null) {
        var m = el("span", { class: "seg marcador tk-NOVA_LINHA", text: "↵", "aria-hidden": "true", title: "NOVA_LINHA" });
        m.setAttribute("data-ev", String(l.fim));
        texto.appendChild(m);
        marcadores.push({ el: m, evs: [l.fim] });
      }
      linha.appendChild(texto);
      raiz.appendChild(linha);
    });
    return { el: raiz, itens: spans.concat(marcadores) };
  }

  /** Marca cada trecho como lido / atual / pendente conforme o passo (atual = índice do evento, -1 = nenhum). */
  function aplicarPasso(view, atual) {
    view.itens.forEach(function (it) {
      var e = it.el, max = Math.max.apply(null, it.evs);
      e.classList.remove("lido", "atual", "pendente");
      if (it.evs.indexOf(atual) !== -1) e.classList.add("atual");
      else if (max < atual) e.classList.add("lido");
      else e.classList.add("pendente");
    });
  }

  // ------------------------------------------------------------ pedaços
  function legenda(resumo, erros, estruturais) {
    var cont = el("ul", { class: "legenda", "aria-label": "Tokens por categoria" });
    Tokens.CATEGORIAS.forEach(function (c) {
      var n = (resumo.por_categoria || {})[c.tipo] || 0;
      if (!n || (c.estrutural && !estruturais)) return;
      cont.appendChild(el("li", { class: "legenda-item tk-" + c.tipo, "data-tipo": c.tipo }, [
        el("i", { "aria-hidden": "true" }), c.rotulo + " ", el("b", { text: String(n) }),
      ]));
    });
    if (erros.length) {
      cont.appendChild(el("li", { class: "legenda-item erro-item", "data-tipo": "ERRO" }, [
        el("i", { "aria-hidden": "true" }), "Erro léxico ", el("b", { text: String(erros.length) }),
      ]));
    }
    return cont;
  }

  function listaErros(erros) {
    var ul = el("ul", { class: "erros-lista" });
    erros.forEach(function (e) {
      ul.appendChild(el("li", { "data-subtipo": e.subtipo || "" }, [
        el("code", { class: "erro-lexema", text: Tokens.tamanho(e.lexema) > 24 ? e.lexema.slice(0, 24) + "…" : e.lexema }),
        el("span", { class: "erro-msg", text: e.mensagem }),
      ]));
    });
    return el("section", { class: "erros", "aria-label": "Erros léxicos" }, [
      el("h3", { text: "Erros léxicos (" + erros.length + ")" }), ul,
    ]);
  }

  function resumoNumerico(dados) {
    var est = dados.estatisticas || {}, r = dados.resumo || {};
    var dl = el("dl", { class: "numeros" });
    [["Linhas recebidas", est.linhas], ["Caracteres recebidos", est.caracteres],
     ["Tokens", r.total_tokens], ["Erros léxicos", r.total_erros]].forEach(function (par) {
      dl.appendChild(el("dt", { text: par[0] }));
      dl.appendChild(el("dd", { text: String(par[1]) }));
    });
    return dl;
  }

  // ------------------------------------------------------------ principal
  function renderizar(container, codigo, dados, opcoes) {
    parar();
    opcoes = opcoes || {};
    var tokens = dados.tokens || [], erros = dados.erros || [], resumo = dados.resumo || {};
    var eventos = Tokens.construirEventos(tokens, erros);
    var visual = eventos.length <= LIMITE_VISUAL;
    var estado = {
      estruturais: true, passo: 0, velocidade: "normal",
      indiceEvento: {}, // índice do token na lista -> índice do evento
    };
    eventos.forEach(function (ev, i) { if (ev.tipo === "token") estado.indiceEvento[ev.tokenIndex] = i; });

    container.textContent = "";
    container.setAttribute("data-estado", dados.sucesso ? "sucesso" : "erro-lexico");

    container.appendChild(el("p", {
      class: "resultado-titulo",
      text: dados.sucesso ? "Análise léxica concluída" : "Análise léxica encontrou erros",
    }));
    container.appendChild(el("p", { class: "resultado-msg", text: dados.mensagem || "" }));
    container.appendChild(resumoNumerico(dados));
    if (erros.length) container.appendChild(listaErros(erros));

    // controle compartilhado: mostrar tokens de estrutura
    var chk = el("input", { type: "checkbox", id: "chk-estruturais", checked: "checked" });
    var rotuloChk = el("label", { class: "chk", for: "chk-estruturais" }, [
      chk, " Mostrar tokens de estrutura (↵ ⇥ ⇤ ∎)",
    ]);

    var abas = el("div", { class: "abas", role: "tablist", "aria-label": "Visualizações do resultado" });
    var paineis = {};
    function criarAba(id, titulo) {
      var b = el("button", { type: "button", role: "tab", class: "aba", id: "aba-" + id,
        "aria-controls": "painel-" + id, "aria-selected": "false", "data-aba": id, text: titulo });
      var p = el("div", { role: "tabpanel", class: "painel-aba", id: "painel-" + id, "aria-labelledby": "aba-" + id });
      p.hidden = true;
      b.addEventListener("click", function () { selecionar(id); });
      abas.appendChild(b);
      paineis[id] = { botao: b, painel: p };
      return p;
    }
    function selecionar(id) {
      Object.keys(paineis).forEach(function (k) {
        var ativo = k === id;
        paineis[k].botao.setAttribute("aria-selected", ativo ? "true" : "false");
        paineis[k].botao.tabIndex = ativo ? 0 : -1;
        paineis[k].painel.hidden = !ativo;
      });
      if (id !== "passos") { parar(); atualizarBotaoExecutar(); }
    }

    // ---- aba: código destacado
    var pCodigo = visual ? criarAba("codigo", "Código destacado") : null;
    var viewEstatica = null, sequencia = null;
    if (visual) {
      viewEstatica = construirCodigo(codigo, eventos);
      sequencia = el("div", { class: "sequencia", "aria-label": "Sequência de tokens" });
      pCodigo.appendChild(legenda(resumo, erros, true));
      pCodigo.appendChild(viewEstatica.el);
      pCodigo.appendChild(el("h4", { class: "sub", text: "Sequência de tokens produzida pelo scanner" }));
      pCodigo.appendChild(sequencia);
    }

    // ---- aba: tabela
    var pTabela = criarAba("tabela", "Tabela de tokens");
    var tbody = el("tbody");
    var aviso = el("p", { class: "nota", hidden: "hidden" });
    var tabela = el("table", { id: "tabela-tokens" }, [
      el("thead", {}, [el("tr", {}, ["#", "Tipo", "Lexema", "Linha", "Coluna"].map(function (h) { return el("th", { scope: "col", text: h }); }))]),
      tbody,
    ]);
    pTabela.appendChild(el("p", { class: "nota", text: "Cada linha é um token: o lexema é o trecho do código; o tipo é a categoria em que o scanner o classificou." }));
    pTabela.appendChild(el("div", { class: "tabela-scroll", tabindex: "0", role: "region", "aria-label": "Tabela de tokens" }, [tabela]));
    pTabela.appendChild(aviso);

    function atualizarTabelaESequencia() {
      tbody.textContent = "";
      if (sequencia) sequencia.textContent = "";
      var visiveis = tokens.map(function (t, i) { return { t: t, i: i }; })
        .filter(function (x) { return estado.estruturais || !Tokens.ehEstrutural(x.t.tipo); });
      visiveis.slice(0, LIMITE_VISUAL).forEach(function (x, n) {
        var t = x.t;
        var tr = el("tr", { class: "token-linha tk-" + t.tipo, "data-tipo": t.tipo }, [
          el("td", { text: String(x.i + 1) }),
          el("td", {}, [el("span", { class: "badge", text: t.tipo })]),
          el("td", {}, [el("code", { class: "lexema", text: Tokens.simbolo(t), title: Tokens.rotulo(t.tipo) })]),
          el("td", { text: String(t.linha) }),
          el("td", { text: String(t.coluna) }),
        ]);
        if (visual) {
          tr.classList.add("clicavel");
          tr.title = "Ver este token no passo a passo";
          tr.addEventListener("click", function () { irParaEvento(estado.indiceEvento[x.i]); });
        }
        tbody.appendChild(tr);
      });
      aviso.hidden = visiveis.length <= LIMITE_VISUAL;
      if (!aviso.hidden) aviso.textContent = "Programa grande: exibindo apenas os primeiros " + LIMITE_VISUAL +
        " de " + visiveis.length + " tokens. Destaque colorido e passo a passo foram desativados.";
      if (sequencia) {
        visiveis.slice(0, 300).forEach(function (x) {
          sequencia.appendChild(el("span", { class: "chip tk-" + x.t.tipo, "data-tipo": x.t.tipo, title: x.t.tipo, text: Tokens.simbolo(x.t) }));
        });
        if (visiveis.length > 300) sequencia.appendChild(el("span", { class: "chip mais", text: "… +" + (visiveis.length - 300) }));
      }
    }

    // ---- aba: passo a passo
    var execBtn = null, irParaEvento = function () {};
    function atualizarBotaoExecutar() {
      if (!execBtn) return;
      execBtn.textContent = timer ? "⏸ Pausar" : "▶ Executar";
      execBtn.setAttribute("aria-pressed", timer ? "true" : "false");
    }
    if (visual) {
      var pPassos = criarAba("passos", "Passo a passo");
      var viewPasso = construirCodigo(codigo, eventos);
      var N = eventos.length;
      var progresso = el("p", { class: "progresso", "aria-live": "polite" });
      var cartao = el("div", { class: "cartao-passo", "aria-live": "polite" });
      var btn = function (id, rot, fn) { return el("button", { type: "button", id: id, class: "secundario pequeno", text: rot, onclick: fn }); };
      var bIni, bAnt, bProx, bFim;

      function ir(p) {
        estado.passo = Math.max(0, Math.min(N, p));
        aplicarPasso(viewPasso, estado.passo - 1);
        progresso.textContent = estado.passo === 0 ? "Passo 0 de " + N + " — nada foi lido ainda" : "Passo " + estado.passo + " de " + N;
        cartao.textContent = "";
        if (estado.passo === 0) {
          cartao.setAttribute("data-erro", "0");
          cartao.appendChild(el("p", { class: "cartao-titulo", text: "O scanner ainda não começou" }));
          cartao.appendChild(el("p", { text: "Ele lê o código da esquerda para a direita, caractere por caractere, agrupando-os em lexemas. Clique em “Próximo” ou “Executar”." }));
        } else {
          var ex = Tokens.explicar(eventos[estado.passo - 1]);
          cartao.setAttribute("data-erro", ex.erro ? "1" : "0");
          cartao.appendChild(el("p", { class: "cartao-titulo", text: ex.titulo }));
          cartao.appendChild(el("p", { text: ex.texto }));
          var atual = viewPasso.el.querySelector(".atual");
          if (atual && atual.scrollIntoView) atual.scrollIntoView({ block: "nearest", inline: "nearest" });
        }
        bIni.disabled = bAnt.disabled = estado.passo === 0;
        bProx.disabled = bFim.disabled = estado.passo === N;
        if (estado.passo === N) { parar(); atualizarBotaoExecutar(); }
      }
      irParaEvento = function (ev) { selecionar("passos"); ir(ev + 1); };

      bIni = btn("btn-inicio", "⏮ Início", function () { parar(); atualizarBotaoExecutar(); ir(0); });
      bAnt = btn("btn-anterior", "◀ Anterior", function () { parar(); atualizarBotaoExecutar(); ir(estado.passo - 1); });
      bProx = btn("btn-proximo", "Próximo ▶", function () { parar(); atualizarBotaoExecutar(); ir(estado.passo + 1); });
      bFim = btn("btn-fim", "Fim ⏭", function () { parar(); atualizarBotaoExecutar(); ir(N); });
      execBtn = btn("btn-executar", "▶ Executar", function () {
        if (timer) { parar(); atualizarBotaoExecutar(); return; }
        if (estado.passo >= N) ir(0);
        timer = setInterval(function () { ir(estado.passo + 1); }, VELOCIDADES[estado.velocidade]);
        atualizarBotaoExecutar();
      });
      var vel = el("select", { id: "sel-velocidade", "aria-label": "Velocidade da execução automática" }, [
        el("option", { value: "lenta", text: "Lenta" }), el("option", { value: "normal", text: "Normal", selected: "selected" }),
        el("option", { value: "rapida", text: "Rápida" }),
      ]);
      vel.addEventListener("change", function () {
        estado.velocidade = vel.value;
        if (timer) { parar(); execBtn.click(); }
      });

      pPassos.appendChild(el("p", { class: "nota", text: "Veja o scanner percorrer o código: o que já foi lido fica colorido, o trecho atual fica em destaque e o restante aparece apagado." }));
      pPassos.appendChild(el("div", { class: "controles-passo" }, [bIni, bAnt, bProx, bFim, execBtn, vel]));
      pPassos.appendChild(progresso);
      pPassos.appendChild(viewPasso.el);
      pPassos.appendChild(cartao);
      ir(0);
    }

    atualizarTabelaESequencia();
    chk.addEventListener("change", function () {
      estado.estruturais = chk.checked;
      atualizarTabelaESequencia();
      var leg = pCodigo && pCodigo.querySelector(".legenda");
      if (leg) pCodigo.replaceChild(legenda(resumo, erros, chk.checked), leg);
    });

    container.appendChild(rotuloChk);
    container.appendChild(abas);
    Object.keys(paineis).forEach(function (k) { container.appendChild(paineis[k].painel); });
    selecionar(visual ? "codigo" : "tabela");
    container.appendChild(el("p", {
      class: "nota", text: "A análise sintática (verificar se a estrutura do programa está correta) será implementada na Etapa 4.",
    }));
  }

  return { renderizar: renderizar, parar: parar, LIMITE_VISUAL: LIMITE_VISUAL };
});
