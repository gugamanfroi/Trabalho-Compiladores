# Registro de testes — Etapa 2

Data da execução: 20/10/2026 · Python 3.12.3, Node 22, Playwright 1.56 (Chromium).

## Resumo da última execução completa (`./scripts/run_tests.sh`)
| Módulo | Tipo | Comando | Aprovados | Reprovados |
|---|---|---|---|---|
| Backend: validação e API (`backend/tests`) | unitário + endpoints | `cd backend && python3 -m unittest discover -s tests -t .` | 30 | 0 |
| Frontend: validação, exemplos, cliente HTTP (`frontend/tests`) | unitário | `cd frontend && node --test tests/*.test.js` | 22 | 0 |
| Interface e fluxo completo (`tests/e2e`) | interface + integração + ponta a ponta (navegador real + backend real) | `python3 -m unittest discover -s tests/e2e -t tests/e2e` | 32 | 0 |
| Implantação (`tests/deploy/smoke_test.py`) | smoke test | `python3 tests/deploy/smoke_test.py <url>` | 10 verificações OK **contra o ambiente local de teste** | 0 |
| Docker Compose (`tests/deploy/check_compose.sh`) | implantação | — | **não executado** (Docker indisponível no ambiente de desenvolvimento) | — |

Total automatizado: **84 testes aprovados, 0 reprovados**.

## O que é coberto
- **API:** código válido, caracteres especiais, código com erro sintático (aceito), campo extra, vazio, só espaços, campo ausente, tipos errados, corpo não-objeto, JSON malformado, corpo vazio, content-type incorreto, limite de tamanho, 404/405, erro interno sem vazamento de detalhes, regressão de `GET /` e `/health`.
- **Frontend (unitário):** validação (vazio, espaços, tamanho), exemplos (≥ 3, únicos, válidos), cliente HTTP com `fetch` simulado (sucesso, 400/422, rede fora, timeout, 502 HTML, 500, resposta inesperada).
- **Interface/E2E:** elementos exigidos, campo monoespaçado, carregamento de cada exemplo, substituição de conteúdo, edição, limpar, contador, envio real ao backend (corpo da requisição verificado), botão desabilitado durante o envio, mensagens de erro (vazio, espaços, rede, 502, 500, backend fora do ar), estado consistente após falha, texto do servidor exibido como texto (sem HTML).

## Falhas encontradas durante o desenvolvimento
| Onde | Problema | Causa | Correção |
|---|---|---|---|
| `test_api.test_codigo_valido` | esperava 24 caracteres | erro de contagem **no teste** (o correto é 25) | valor do teste corrigido |
| `smoke_test.py` | esperava 25 caracteres | idem (texto com `\n` final = 26) | valor do teste corrigido |
| Contador de linhas da interface | mostrava 5 linhas; o servidor informava 4 | o contador contava a linha vazia após o `\n` final | `app.js` corrigido + teste `test_contador_de_linhas_coincide_com_o_do_servidor` |
| Execução do `node --test` | `tests/` tratado como arquivo no Node 22 | uso incorreto do comando | passou a usar `tests/*.test.js` |

## Verificação de sensibilidade dos testes (mutação manual)
Para confirmar que os testes detectam defeitos, o código foi quebrado propositalmente e restaurado em seguida:
| Mutação | Detectada? |
|---|---|
| Frontend deixa de validar entrada vazia | Sim (UI e JS unitário) |
| Backend deixa de validar entrada só com espaços | Sim (5 falhas) |
| Interface usa `innerHTML` em vez de `textContent` | **Não** na primeira tentativa → criado `test_texto_vindo_do_servidor_e_exibido_como_texto_nao_como_html`; depois, Sim |

## Pendências / limitações dos testes
- Executar `tests/deploy/check_compose.sh` em uma máquina com Docker e registrar o resultado aqui.
- Os testes de interface usam um servidor de teste (Python) que imita o proxy do Nginx; a configuração real `frontend/nginx.conf` só é exercitada pelo teste de implantação acima.
- Não há medição de cobertura de código.
