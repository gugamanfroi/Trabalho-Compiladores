/* Validação da entrada no frontend (o backend valida novamente). */
(function (root, factory) {
  if (typeof module === "object" && module.exports) module.exports = factory();
  else root.Validacao = factory();
})(typeof self !== "undefined" ? self : this, function () {
  var TAMANHO_MAXIMO = 100000;

  var MENSAGENS = {
    entrada_vazia: "Informe um código-fonte antes de solicitar a análise.",
    entrada_somente_espacos:
      "O código informado contém apenas espaços em branco. Digite um programa para ser analisado.",
    codigo_muito_grande:
      "O código excede o limite de " + TAMANHO_MAXIMO + " caracteres.",
    falha_comunicacao:
      "Não foi possível comunicar com o servidor. Verifique a conexão e tente novamente.",
    erro_inesperado:
      "Ocorreu um erro inesperado. Tente novamente em instantes.",
  };

  function validarCodigo(texto) {
    if (typeof texto !== "string" || texto === "")
      return { valido: false, tipo: "entrada_vazia", mensagem: MENSAGENS.entrada_vazia };
    if (texto.trim() === "")
      return { valido: false, tipo: "entrada_somente_espacos", mensagem: MENSAGENS.entrada_somente_espacos };
    if (texto.length > TAMANHO_MAXIMO)
      return { valido: false, tipo: "codigo_muito_grande", mensagem: MENSAGENS.codigo_muito_grande };
    return { valido: true };
  }

  return { TAMANHO_MAXIMO: TAMANHO_MAXIMO, MENSAGENS: MENSAGENS, validarCodigo: validarCodigo };
});
