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
      titulo: "4. Erro de sintaxe (não léxico)",
      descricao: "Operadores consecutivos (+*): todos os tokens são válidos, então o scanner não reclama. Quem detectará este erro é o parser (Etapa 4).",
      codigo: "resultado = 10 +* 5\nprint(resultado)\n",
    },
    {
      id: "tokens",
      titulo: "5. Todas as categorias de token",
      descricao: "Palavras reservadas, identificadores, inteiro e real, string, operadores compostos, delimitadores e comentário.",
      codigo:
        "# preço com desconto\npreco = 12.5\nnome = \"Ana\"\ntotal = (preco * 2) // 3 + 4 ** 2\n" +
        "if total >= 10 and nome != \"Bia\":\n    total -= 1\n",
    },
    {
      id: "erros-lexicos",
      titulo: "6. Erros léxicos",
      descricao: "Símbolo fora do subconjunto (@), identificador começando com dígito, string sem fechar e parêntese aberto.",
      codigo: "valor = 10 @ 2\n12abc = 5\ntexto = \"sem fechar\ntotal = (1 + 2\n",
    },
    {
      id: "indentacao",
      titulo: "7. Blocos e indentação",
      descricao: "Blocos aninhados: o recuo gera os tokens INDENTACAO e DESINDENTACAO.",
      codigo: "n = 3\nwhile n > 0:\n    if n == 2:\n        n = n - 2\n    n = n - 1\nprint(n)\n",
    },
  ];
});
