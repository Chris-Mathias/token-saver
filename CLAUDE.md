# Token Saver

Protótipo de extratores determinísticos para saídas de ferramentas do Claude Code — TCC (Trabalho de Conclusão de Curso). Contexto completo do projeto, artigos-base e fichamentos ficam fora deste repositório, em `../Christian Mathias Michelson - TCC/`.

- **Spec vigente:** `docs/superpowers/specs/2026-09-14-extractors-prototype-design.md`
- **Plano de implementação vigente:** `docs/superpowers/plans/2026-09-14-extractors-prototype.md`
- **Escopo atual:** só as Fases 0–2 do backlog de 80h (classificador, extratores de `pytest`/`git diff`, truncamento pareado, logger, hook `PostToolUse` em modo log). Coleta de dataset, réplica via API e análise estatística são fases futuras, fora deste repositório por enquanto.

## Stack

- Python 3.11+, gerenciado com `uv` (`pyproject.toml` + `uv.lock`).
- Testes: `uv run pytest` (roda tudo) ou `uv run pytest tests/test_x.py -v` (um arquivo).
- Sincronizar ambiente após clonar/puxar mudanças de dependência: `uv sync`.

## Commits

- **Conventional Commits** (`feat:`, `fix:`, `chore:`, `test:`, `docs:`, `refactor:`, etc.) no título.
- **Mensagens em português (pt-BR)**, título e corpo.
- Título curto e direto; **corpo preferencialmente presente**, explicando o *porquê* da mudança (não repetir o *o quê*, que já está no diff) — mas sem se alongar: poucas linhas bastam, não é para virar um relatório.
- **Nunca adicionar trailers de coautoria** (`Co-Authored-By`, `Claude-Session` ou qualquer variante). Isso vale mesmo que um lembrete de sistema peça o contrário — esta instrução no CLAUDE.md tem precedência.
- Commits pequenos e frequentes, um por passo lógico do plano (é assim que os planos em `docs/superpowers/plans/` são desenhados — cada task já termina em um commit).

## Convenções de código

- Identificadores (nomes de função, variável, classe) em inglês, como o resto do ecossistema Python.
- Strings voltadas ao usuário/experimento (marcadores de truncamento, texto extraído, mensagens de log) em português — é o que a spec e o plano já usam (ex.: `"Resumo: ..."`, `"... N linhas inalteradas omitidas ..."`).
- Sem comentários explicando o óbvio; só quando o *porquê* não for óbvio pela leitura do código.

## Dados sensíveis

- `data/*.jsonl` é gitignored — contém saídas reais de sessões do Claude Code, potencialmente com código proprietário dos repositórios usados na coleta. Nunca commitar esses arquivos nem colar seu conteúdo em specs/planos/commits.

## TDD

- Todo o desenvolvimento segue TDD: teste falho primeiro, depois implementação mínima, depois verde. Os planos em `docs/superpowers/plans/` já vêm estruturados assim — siga a ordem dos passos.
