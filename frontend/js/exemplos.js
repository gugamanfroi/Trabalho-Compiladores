/* Programas de exemplo: subconjunto de Python (atribuições, aritmética, if). */
(function (root, factory) {
  if (typeof module === "object" && module.exports) module.exports = factory();
  else root.Exemplos = factory();
})(typeof self !== "undefined" ? self : this, function () {
  return [
    {
      id: "declaracao",
      titulo: "1. Atribuição de variável",
      descricao: "Atribuição de um literal inteiro a uma variável e uso em print().",
      codigo: "numero = 10\nprint(numero)\n",
    },
    {
      id: "aritmetica",
      titulo: "2. Operações aritméticas",
      descricao: "Operadores +, -, *, / e // com precedência e parênteses.",
      codigo:
        "a = 10\nb = 5\nresultado = a + b * 2\nmedia = (a + b) / 2\nprint(resultado)\nprint(media)\n",
    },
    {
      id: "condicional",
      titulo: "3. Estrutura condicional",
      descricao: "Comando if com comparação e bloco indentado.",
      codigo: "numero = 10\nif numero > 0:\n    numero = numero + 1\nprint(numero)\n",
    },
    {
      id: "erro",
      titulo: "4. Com erro intencional",
      descricao: "Operadores consecutivos (+*) — um erro que as próximas etapas deverão detectar.",
      codigo: "resultado = 10 +* 5\nprint(resultado)\n",
    },
  ];
});
