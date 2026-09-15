# Token Saver — Protótipo de Extratores Determinísticos (Fases 0–2)

**Status:** aprovado para implementação
**Data:** 2026-09-14
**Escopo desta spec:** Fases 0–2 do backlog de 80h do TCC (~28h) — delimitação, extrator de testes, extrator de diff + baseline de truncamento pareado + logger.
**Fora desta spec (próximos passos):** coleta de dataset ao vivo (Fase 3), réplica contrafactual via API (Fase 4), análise estatística com teste de McNemar (Fase 5), escrita do TCC (Fases 6–7). Essas fases exigem decisões adicionais (repositórios-alvo, modelo Claude para as sessões e para a réplica, chave de API) que ficam deliberadamente em aberto até o usuário decidir avançar para a etapa de validação.

## 1. Contexto e motivação

O TCC "Token Saver" investiga se a extração determinística por tipo de comando preserva mais a fidelidade da próxima decisão de um agente de codificação (Claude Code) do que um truncamento genérico, no mesmo orçamento de tokens — a pergunta de pesquisa e o desenho experimental completo estão descritos no documento de escopo de 80h do TCC (`Token Saver — Escopo de TCC (80h)`, artifact `e80d6415-9725-496c-a675-3bd6edd49763`).

O recorte teórico que sustenta o projeto vem de dois artigos-base do referencial: Lindenbauer et al. (2025), que mostram que ~84% dos tokens de um turno de agente de SE são saídas de ferramentas (observações) e que compressão simples e determinística rivaliza com sumarização por LLM; e Wang et al. (2026, SWE-Pruner), que demonstram que a granularidade de linha/hunk (não a poda por token isolado) é o que preserva a estrutura sintática do conteúdo comprimido. O Token Saver ocupa o eixo de compressão de **observação** (não de histórico), com extração determinística condicionada ao tipo de comando em vez de um modelo neural treinado.

Esta spec cobre apenas a construção do protótipo determinístico em si — o hook, o classificador, os dois extratores (pytest e `git diff`), o gerador de truncamento pareado e o logger. A validação experimental (coleta de dados reais, réplica contrafactual, teste estatístico) é trabalho subsequente e não está especificada aqui.

## 2. Decisões já tomadas

- **Linguagem/stack:** Python 3.11+, gerenciado com `uv` (pyproject.toml + uv.lock).
- **Test runner coberto:** pytest (saída padrão de console, não JUnit XML — é isso que o agente efetivamente vê na saída da tool Bash).
- **Arquitetura:** núcleo de extração desacoplado do adaptador de hook (pacote `token_saver` importável + hook fino em `hooks/post_tool_use.py`), para que a Fase 4 (fora de escopo aqui) possa reimportar os mesmos extratores sem duplicar lógica.
- **Contagem de tokens:** aproximação local via `tiktoken` (cl100k_base) por padrão, atrás de uma interface plugável — documentado como aproximação, a ser trocado pelo endpoint `count_tokens` da Anthropic antes de qualquer experimento real (Fase 4).
- **Controle de versão:** repositório git local inicializado em `Token-Saver/`, branch `main`, sem remoto por enquanto.
- **Dados de sessão real** (quando a Fase 3 acontecer) nunca vão para o git — `data/*.jsonl` fica no `.gitignore` porque pode conter código proprietário dos repositórios usados na coleta.

## 3. Componentes

### 3.1 `classifier.py`

```
classify_command(command: str) -> CommandType  # TEST_RUNNER | GIT_DIFF | UNKNOWN
```

Classificação por regex sobre a string do comando executado pela tool Bash:
- contém `pytest` (como palavra/token do comando, não substring solta) → `TEST_RUNNER`
- contém `git diff` → `GIT_DIFF`
- qualquer outra coisa → `UNKNOWN`

Comandos `UNKNOWN` não geram entrada no log — só eventos classificados interessam ao dataset do experimento (consistente com a metodologia da Fase 3, que trata cada chamada de test runner ou `git diff` como "evento candidato").

### 3.2 `extractors/pytest_extractor.py`

```
extract_pytest(raw_output: str) -> ExtractionResult
```

Parseia a saída padrão de console do pytest:
- extrai a linha de resumo final (ex.: `5 passed, 2 failed in 1.23s`) → contadores estruturados;
- para cada falha na seção `FAILURES`, extrai o bloco completo do traceback, preservando `arquivo:linha` de cada frame;
- descarta as linhas verbosas de `PASSED`/`.`/`F` por teste individual — não carregam sinal decisório adicional além do contador.

`ExtractionResult` contém o texto condensado final (contador + tracebacks completos das falhas) e metadados (nº de testes, nº de falhas).

### 3.3 `extractors/git_diff_extractor.py`

```
extract_git_diff(raw_output: str, context_lines: int = 1) -> ExtractionResult
```

Parseia diff unificado (saída de `git diff`):
- mantém hunks com mudanças (`+`/`-`) na íntegra;
- dentro de cada hunk, se houver uma sequência de linhas de contexto inalteradas maior que `context_lines`, colapsa o excedente em um marcador de texto (`"... N linhas inalteradas omitidas ..."`), mantendo `context_lines` linhas de contexto em cada extremidade da sequência;
- cabeçalhos de arquivo (`diff --git`, `---`, `+++`, `@@ ... @@`) são sempre preservados.

Casos de borda a cobrir nos testes: múltiplos arquivos no mesmo diff, múltiplos hunks no mesmo arquivo, arquivo binário (diff sem hunks de texto — a saída do git já sinaliza isso, o extrator deve preservar a linha `Binary files ... differ` sem tentar parsear hunks), arquivo novo/removido (diff só de adição ou só de remoção).

### 3.4 `tokenizer.py`

```
count_tokens(text: str) -> int
```

Implementação padrão via `tiktoken.get_encoding("cl100k_base")`. Interface desenhada para permitir troca futura por uma implementação exata (endpoint `count_tokens` da Anthropic), sem alterar os chamadores (`truncate.py`, `logger.py`).

### 3.5 `truncate.py`

```
paired_truncate(raw_output: str, target_tokens: int) -> str
```

Gera a versão S2a (baseline de truncamento): corta a saída bruta para aproximadamente `target_tokens` (usando o mesmo `tokenizer.count_tokens`), preservando o prefixo e anexando um marcador indicando quantos tokens/caracteres foram cortados. `target_tokens` é sempre o tamanho em tokens da versão S2b daquele mesmo evento — a comparação nunca deve favorecer S2a ou S2b por ter mais orçamento.

### 3.6 `logger.py`

```
log_event(event: EventRecord, path: Path) -> None
```

Acrescenta uma linha JSON a `data/events.jsonl` por evento processado, com: timestamp, comando, tipo classificado, saída bruta, saída S2a, saída S2b, contagem de tokens de cada uma das três versões, e um campo opcional `extractor_error` quando a extração falhar.

### 3.7 `hooks/post_tool_use.py`

Adaptador fino, ponto de entrada real do hook `PostToolUse` do Claude Code:
1. lê o payload JSON do stdin (contrato do hook: inclui `tool_name`, `tool_input`, `tool_response`, entre outros campos padrão do Claude Code);
2. ignora silenciosamente (exit 0, sem log) qualquer evento cujo `tool_name` não seja `Bash`;
3. extrai o comando executado e a saída bruta da resposta da ferramenta;
4. chama `classify_command`; se `UNKNOWN`, sai sem logar;
5. se `TEST_RUNNER` ou `GIT_DIFF`, roda o extrator correspondente (S2b), depois `paired_truncate` usando a contagem de tokens de S2b como alvo (S2a), conta tokens das três versões, e grava o evento via `logger.log_event`;
6. **sempre** sai com código 0 e sem imprimir nada que altere o comportamento do hook — este protótipo roda em modo log: a sessão real do usuário nunca é modificada, apenas observada e registrada.

O contrato exato de stdin/stdout do hook `PostToolUse` (nomes de campos, semântica de códigos de saída) deve ser conferido contra a documentação atual do Claude Code no momento da implementação, já que hooks são uma superfície que muda com alguma frequência entre versões.

## 4. Fluxo de dados

```
Bash executa comando
  → Claude Code dispara hook PostToolUse
  → hooks/post_tool_use.py lê stdin
  → filtra tool_name == "Bash"
  → classifica o comando
  → [se reconhecido] roda extrator → S2b
  → gera truncamento pareado no tamanho de S2b → S2a
  → conta tokens de bruto/S2a/S2b
  → grava linha em data/events.jsonl
  → sai sem alterar a resposta real da ferramenta
```

## 5. Tratamento de erros

- Qualquer exceção dentro de um extrator é capturada; o evento **ainda é gravado** em `data/events.jsonl`, mas com `s2b_output` vazio e o campo `extractor_error` preenchido com a mensagem da exceção — descartar silenciosamente esconderia falhas de parsing que precisam ser visíveis durante o desenvolvimento dos extratores. Em nenhum caso a exceção deve propagar e interromper a sessão real do usuário.
- Falha na contagem de tokens cai para uma estimativa `len(texto) // 4` com flag `approx_fallback: true` no registro logado.
- O hook sempre retorna código de saída 0 nesta fase (modo log-only); não há cenário em que o protótipo deva bloquear ou alterar uma tool call real.

## 6. Testes

Abordagem TDD (fixtures de texto puro, sem necessidade de uma sessão real do Claude Code):

- `tests/fixtures/pytest_output/`: saída com tudo passando, saída com falhas (uma e múltiplas), erro de coleta (`ERRORS`, sem rodar nenhum teste).
- `tests/fixtures/git_diff/`: hunk único, múltiplos hunks no mesmo arquivo, múltiplos arquivos, arquivo binário, arquivo novo, arquivo removido.
- `tests/test_classifier.py`: tabela de comandos-exemplo → tipo esperado, incluindo casos ambíguos (ex.: comando que contém `pytest` como parte de um path, não como invocação).
- `tests/test_pytest_extractor.py`, `tests/test_git_diff_extractor.py`: comparação exata contra saída esperada para cada fixture.
- `tests/test_truncate.py`: verifica que o resultado de `paired_truncate` fica dentro de uma tolerância pequena do `target_tokens` pedido.
- `tests/test_hook_post_tool_use.py`: teste de integração do adaptador com um payload JSON simulado no stdin, verificando a linha gravada em `data/events.jsonl` — sem depender de uma instalação real do Claude Code.

## 7. Estrutura do projeto

```
Token-Saver/
  pyproject.toml, uv.lock         # uv, Python 3.11+, dependência de runtime: tiktoken
  .gitignore                      # .venv/, __pycache__/, data/*.jsonl
  README.md
  src/token_saver/
    __init__.py
    classifier.py
    tokenizer.py
    truncate.py
    logger.py
    extractors/
      __init__.py
      pytest_extractor.py
      git_diff_extractor.py
  hooks/
    post_tool_use.py
  tests/
    fixtures/
      pytest_output/*.txt
      git_diff/*.diff
    test_classifier.py
    test_pytest_extractor.py
    test_git_diff_extractor.py
    test_truncate.py
    test_hook_post_tool_use.py
  data/
    .gitkeep                      # data/*.jsonl é gitignored
  docs/superpowers/specs/
    2026-09-14-extractors-prototype-design.md   # esta spec
```

## 8. Critério de conclusão desta fase

O protótipo desta spec está pronto quando: os dois extratores passam em todos os casos de fixture (incluindo os casos de borda listados na seção 6), o truncamento pareado respeita o orçamento de tokens de S2b dentro de uma tolerância definida na implementação, o hook roda em modo log sobre uma sessão real do Claude Code sem alterar o comportamento observado pelo usuário, e `data/events.jsonl` acumula eventos classificados corretamente. Isso corresponde ao fim da Fase 2 do backlog de 80h (~28h acumuladas) — a partir daí, a continuação natural é uma nova spec para a Fase 3 (coleta de dataset ao vivo), que exigirá decidir repositórios-alvo e reabrir a questão de acesso à API.
