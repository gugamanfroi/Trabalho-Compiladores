# Tutorial: entendendo a análise léxica com o Compilador Educacional

Guia para quem está começando em Compiladores. Dá para fazer tudo em ~15 minutos usando a própria aplicação.

## 1. A ideia
Um compilador não lê um programa como nós. Primeiro ele **separa o texto em pedaços com significado**. Essa
primeira fase se chama **análise léxica** e quem a faz é o **scanner** (ou *lexer*).

| Termo | Significado | Exemplo em `numero = 10` |
|---|---|---|
| **Lexema** | O trecho exato do código | `numero`, `=`, `10` |
| **Token** | O lexema **+ a categoria** (+ linha e coluna) | `numero` → `IDENTIFICADOR` |
| **Categoria** | O "tipo" do token | identificador, operador, literal inteiro… |

O scanner **ignora** o que não importa ao programa (espaços, comentários `#`) e **não verifica se o programa
faz sentido**. Isso é papel do *parser* (Etapa 4). Por isso `x = 10 +* 5` passa no scanner: todos os
pedaços são válidos, apenas estão em ordem errada.

## 2. Como o scanner decide (maior casamento)
Ele lê da esquerda para a direita e, a cada posição, olha o primeiro caractere:

1. **Letra ou `_`** → lê letras/dígitos/`_` e vê se o lexema está na lista de palavras reservadas
   (`if` → `PALAVRA_RESERVADA`; `numero` → `IDENTIFICADOR`).
2. **Dígito** → lê o número; se houver `.` seguido de dígitos é `LITERAL_REAL`, senão `LITERAL_INTEIRO`.
3. **Aspa** → lê até a aspa de fechamento → `LITERAL_STRING`.
4. **Símbolo** → tenta o **maior operador possível**: em `a**=b` lê `**=` (um token), não `*`, `*`, `=`.
5. **Espaço / `#`** → pula. **Qualquer outra coisa** → erro léxico, registra e continua.

## 3. O que é especial no Python
Em Python, o **recuo** e o **fim de linha** fazem parte da linguagem. Por isso o scanner também gera:

| Token | Símbolo | Quando |
|---|---|---|
| `NOVA_LINHA` | `↵` | termina uma instrução |
| `INDENTACAO` | `⇥` | a linha começa mais à direita que a anterior (abre bloco) |
| `DESINDENTACAO` | `⇤` | a linha volta para a esquerda (fecha bloco; pode haver vários seguidos) |
| `FIM_ARQUIVO` | `∎` | o código acabou |

Regras que surpreendem: linhas em branco e linhas só com comentário **não** geram `NOVA_LINHA`; uma quebra de
linha **dentro de parênteses** é ignorada (a instrução continua); `\` no fim da linha também continua a instrução.

## 4. Passeio pela aplicação
1. Abra `http://localhost:8080` e escolha **"5. Todas as categorias de token"** → **Analisar código**.
2. Na aba **Código destacado**, veja as cores por categoria e a **legenda com contagens**. Abaixo, a
   *sequência de tokens* mostra a "tradução" do seu código.
3. Na aba **Tabela de tokens**, confira tipo, lexema, linha e coluna de cada um. Desmarque *Mostrar tokens de
   estrutura* para ver só o que está escrito no código. **Clique numa linha** para ir ao passo a passo.
4. Na aba **Passo a passo**, use ▶ **Próximo** (ou **Executar**) e acompanhe o scanner: o que já foi lido fica
   colorido, o trecho atual fica em destaque e o cartão explica **por que** ele virou aquele token.
5. Escolha **"6. Erros léxicos"**: quatro erros aparecem **de uma vez**, cada um com linha e coluna, e o
   scanner continua lendo depois de cada erro.

## 5. Exercícios (prediga antes de executar!)
Digite cada programa, **antes** de analisar, preveja os tokens e depois confira. As respostas foram obtidas com o
próprio scanner.

| # | Programa | Pergunta | Resposta |
|---|---|---|---|
| 1 | `x = 3 + 4` | Quantos tokens (com estrutura)? | **7**: `x` `=` `3` `+` `4` `↵` `∎` |
| 2 | `a=b==c` | Sem espaços, como fica? | **7**: `a` `=` `b` `==` `c` `↵` `∎` (`==` é um token só) |
| 3 | `total = 5 // 2 # divisão` | O comentário vira token? | **Não**: 7 tokens, `//` é um `OPERADOR` |
| 4 | `if x >= 10:` + linha seguinte `    y = 1` | Quantos tokens? Há `INDENTACAO`? | **13**; sim, 1 `INDENTACAO` e 1 `DESINDENTACAO` |
| 5 | `x = (1 +` / `     2)` (2 linhas) | Aparece `INDENTACAO` na linha 2? | **Não**; só há 1 `NOVA_LINHA` (quebra dentro de parênteses) |
| 6 | `nome = 'Ana'` | Aspas simples valem? | **Sim**: `LITERAL_STRING` (5 tokens) |
| 7 | `x = 07` | Por que dá erro? | `NUMERO_MALFORMADO`: zeros à esquerda não são permitidos em Python 3 |
| 8 | `x = 10 +* 5` | O scanner acusa erro? | **Não** — é erro de *sintaxe*; quem detecta é o parser (Etapa 4) |
| 9 | `y = 2 @ 3` | Erro? De que tipo? | `FORA_DO_SUBCONJUNTO`: `@` existe em Python, mas não neste projeto |

## 6. Para ir além
- Compare o resultado com `python -m tokenize arquivo.py` (módulo da biblioteca padrão): para programas sem erro
  léxico, os testes automatizados do projeto exigem que os tokens coincidam.
- Tente quebrar o scanner: `"abc` (string aberta), `12abc`, `$`, `)))`. O que ele reporta?
- Próximo passo da disciplina: o **parser** receberá esta lista de tokens e verificará se eles formam um programa
  válido (Etapa 4).
