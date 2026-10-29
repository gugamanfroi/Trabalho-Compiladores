# Registro de testes

Ambiente das execuções: Python 3.12.3, Node 22, Playwright 1.56 (Chromium), Linux. Docker **não** estava
disponível no ambiente de desenvolvimento.

# Etapa 3 — Análise léxica

## Resumo da última execução completa (`./scripts/run_tests.sh`)
| Módulo | Tipo | Comando | Aprovados | Reprovados |
|---|---|---|---|---|
| `backend/tests/test_scanner.py` | unitário do scanner | `cd backend && python3 -m unittest tests.test_scanner` | 70 | 0 |
| `backend/tests/test_api.py` | endpoints (inclui contrato léxico e regressão da Etapa 2) | `... tests.test_api` | 31 | 0 |
| `backend/tests/test_validators.py` | unitário (Etapa 2) | `... tests.test_validators` | 9 | 0 |
| `frontend/tests/*.test.js` | unitário do frontend (`tokens`, `api`, `validacao`, `exemplos`) | `cd frontend && node --test tests/*.test.js` | 33 (11 + 10 + 8 + 4) | 0 |
| `tests/e2e/test_ui.py` | interface + integração + ponta a ponta (navegador real + backend real) | `python3 -m unittest discover -s tests/e2e -t tests/e2e` | 54 (22 novos da Etapa 3 + 32 de regressão) | 0 |
| `tests/deploy/smoke_test.py` | implantação | `python3 tests/deploy/smoke_test.py <url>` | 13 verificações OK **no ambiente local de teste** | 0 |
| `tests/deploy/check_compose.sh` | Docker Compose | — | **não executado** | — |

**Total automatizado: 197 testes aprovados, 0 reprovados.**

## O que o scanner testa (unitários)
Todas as 35 palavras reservadas (e igualdade com `keyword.kwlist`); identificadores válidos/inválidos (inclusive
Unicode); literais inteiro, real e string (escapes, `#` dentro de string); números malformados; cada operador e
delimitador e o "maior casamento"; comentários e espaços; linha/coluna (inclusive caracteres multibyte e tabs); INDENT/DEDENT,
blocos aninhados, linhas em branco, parênteses e continuação com `\`; CR/LF/CRLF; erros léxicos de cada subtipo,
acúmulo de vários erros em ordem, recuperação e mensagens sem detalhes internos; bordas (vazio, só espaços, só
comentários, token no fim sem `\n`, caractere de controle, emoji, *surrogate* isolado, entrada de ~90 mil caracteres).
**Teste diferencial:** 15 programas comparados com o `tokenize` do CPython (tipos, lexemas e posições).

## Regressão
- As 84 verificações das Etapas 1 e 2 foram executadas antes de qualquer alteração (linha de base: **84/84**).
- Após integrar o scanner, 1 teste falhou, **por mudança intencional de requisito**: o texto de `mensagem` deixou
  de ser "Código recebido com sucesso." e passou a descrever a análise léxica (`test_api.test_codigo_valido`,
  atualizado). Idem em `test_ui` (`test_exemplo_completo_do_inicio_ao_fim`: mensagem e nota "próximas etapas" → "Etapa 4";
  e os testes que esperavam `data-estado="sucesso"` para todos os exemplos, pois o exemplo 6 agora termina em `erro-lexico`).
- Nenhum teste de validação (vazio, espaços, 400/413/422/500, falha de comunicação) precisou mudar.

## Falhas encontradas durante o desenvolvimento
| Onde | Problema | Causa | Correção |
|---|---|---|---|
| `test_api.test_caracteres_especiais...` | caso `"\x0b\x0c"` retornou 422 | erro **do teste**: é só "espaço em branco" para o validador (Etapa 2) | trocado por `x\x0b= 1` |
| `tokens.test.js` (emoji) | colunas esperadas erradas | erro **do teste** (contagem manual) | fixture corrigido |
| `test_ui` (4 testes novos) | cores, `<b>` da legenda, nº de cliques no passo a passo | erros **dos testes** (seletor amplo / expectativa errada) | testes corrigidos |
| **Layout mobile** | página com 436 px de largura numa tela de 391 px | `grid-template-columns: 1fr` deixava o conteúdo largo esticar o container | `minmax(0, 1fr)` em `style.css`; teste `test_layout_mobile_sem_rolagem_horizontal_da_pagina` |

## Verificação de sensibilidade dos testes (mutação manual)
O código foi quebrado de propósito e restaurado. Mutações **não detectadas na primeira tentativa** geraram novos testes.

| Mutação | Resultado |
|---|---|
| Scanner: remover `//`; deslocar coluna; não emitir DEDENT final; quebra em `()` gerar NOVA_LINHA; remover `while`; aceitar zeros à esquerda; desligar "maior casamento"; não emitir NOVA_LINHA final; omitir erro de indentação | detectadas |
| Scanner: não ignorar comentário | detectada (a 1ª tentativa nem foi aplicada por erro no padrão; refeita) |
| Scanner: erros fora de ordem; string aberta virando token; tab = 1 coluna | **sobreviveram** → criados `test_erro_de_parentese_aberto_e_ordenado...`, asserção "string aberta não vira token" e `test_tab_e_oito_espacos...` → detectadas |
| Frontend: `innerHTML` no lugar de `textContent`; coluna deslocada na segmentação; timer do passo a passo não parado; erros fora dos eventos; tamanho em UTF-16 | detectadas |

## Limitações e pendências
- **Executar `tests/deploy/check_compose.sh` em uma máquina com Docker** e anotar aqui o resultado (build, `up --wait`, smoke test).
- A suíte foi executada somente com Python 3.12. A imagem Docker usa Python 3.9: a sintaxe foi verificada com
  `ast.parse(feature_version=(3, 9))`, mas o comportamento em 3.9 não foi executado. O teste comparativo com o `tokenize` tem uma
  parte estrita (posições de tokens estruturais) que só roda em Python ≥ 3.12.
- Os testes de interface usam um servidor Python que imita o proxy do Nginx; o `frontend/nginx.conf` real só é exercitado pelo teste de implantação.
- Não há medição de cobertura de código nem teste em navegadores além do Chromium.

---

# Etapa 2 — Interface e comunicação (histórico)
Execução da época: backend 30, JS 22, interface 32 = **84 aprovados, 0 reprovados**; smoke test 10 verificações no ambiente local.
Falhas então encontradas e corrigidas: contagem de caracteres errada em dois testes; contador de linhas da interface
divergente do servidor (`app.js` corrigido); `node --test tests/` incorreto no Node 22 (glob). Mutações então verificadas:
frontend sem validação de vazio, backend sem validação de espaços e `innerHTML` (esta só detectada após criar
`test_texto_vindo_do_servidor_e_exibido_como_texto_nao_como_html`).
