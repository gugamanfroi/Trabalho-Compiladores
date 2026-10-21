/* Interface: liga os elementos da página aos módulos de validação, exemplos e API. */
(function () {
  var $ = function (id) { return document.getElementById(id); };
  var campo = $("codigo");
  var seletor = $("seletor-exemplo");
  var descricao = $("descricao-exemplo");
  var botao = $("btn-analisar");
  var botaoLimpar = $("btn-limpar");
  var contador = $("contador");
  var resultado = $("resultado");

  var TEXTO_INICIAL =
    "Escreva ou escolha um programa e clique em Analisar código. O resultado aparece aqui.";

  function atualizarContador() {
    var t = campo.value;
    var linhas = t === "" ? 0 : t.split("\n").length - (t.slice(-1) === "\n" ? 1 : 0); // igual a str.splitlines() do backend
    contador.textContent = linhas + (linhas === 1 ? " linha" : " linhas") + " · " + t.length + " caracteres";
  }

  function mostrar(estado, titulo, detalhes) {
    resultado.setAttribute("data-estado", estado);
    resultado.textContent = "";
    var t = document.createElement("p");
    t.className = "resultado-titulo";
    t.textContent = titulo;
    resultado.appendChild(t);
    (detalhes || []).forEach(function (el) { resultado.appendChild(el); });
  }

  function paragrafo(texto, classe) {
    var p = document.createElement("p");
    if (classe) p.className = classe;
    p.textContent = texto;
    return p;
  }

  function mostrarSucesso(r) {
    var est = (r.dados && r.dados.estatisticas) || {};
    var dl = document.createElement("dl");
    [["Linhas recebidas", est.linhas], ["Caracteres recebidos", est.caracteres]].forEach(function (par) {
      var dt = document.createElement("dt"); dt.textContent = par[0];
      var dd = document.createElement("dd"); dd.textContent = String(par[1]);
      dl.appendChild(dt); dl.appendChild(dd);
    });
    mostrar("sucesso", r.mensagem, [
      dl,
      paragrafo("As análises léxica, sintática e semântica serão adicionadas nas próximas etapas.", "nota"),
    ]);
  }

  function mostrarErro(r) {
    var estado = r.tipo === "falha_comunicacao" ? "erro-comunicacao"
      : r.tipo === "erro_inesperado" || r.tipo === "erro_interno" ? "erro-inesperado"
      : "erro-entrada";
    var titulos = {
      "erro-entrada": "Verifique a entrada",
      "erro-comunicacao": "Falha de comunicação",
      "erro-inesperado": "Erro inesperado",
    };
    mostrar(estado, titulos[estado], [paragrafo(r.mensagem)]);
  }

  async function analisar() {
    var v = Validacao.validarCodigo(campo.value);
    if (!v.valido) return mostrarErro({ tipo: v.tipo, mensagem: v.mensagem });

    botao.disabled = true;
    botao.textContent = "Analisando…";
    mostrar("carregando", "Enviando o código para o servidor…");
    try {
      var r = await Api.enviarCodigo(campo.value);
      if (r.ok) mostrarSucesso(r); else mostrarErro(r);
    } catch (e) {
      mostrarErro({ tipo: "erro_inesperado", mensagem: Validacao.MENSAGENS.erro_inesperado });
    } finally {
      botao.disabled = false;
      botao.textContent = "Analisar código";
    }
  }

  function carregarExemplo() {
    var ex = Exemplos.find(function (e) { return e.id === seletor.value; });
    if (!ex) { descricao.textContent = ""; return; }
    campo.value = ex.codigo;
    descricao.textContent = ex.descricao;
    atualizarContador();
    mostrar("inicial", TEXTO_INICIAL);
    campo.focus();
  }

  // Preenche o seletor
  Exemplos.forEach(function (ex) {
    var o = document.createElement("option");
    o.value = ex.id; o.textContent = ex.titulo;
    seletor.appendChild(o);
  });

  seletor.addEventListener("change", carregarExemplo);
  campo.addEventListener("input", atualizarContador);
  botao.addEventListener("click", analisar);
  botaoLimpar.addEventListener("click", function () {
    campo.value = ""; seletor.value = ""; descricao.textContent = "";
    atualizarContador(); mostrar("inicial", TEXTO_INICIAL); campo.focus();
  });

  atualizarContador();
  mostrar("inicial", TEXTO_INICIAL);
})();
