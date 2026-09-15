# Token Saver

Protótipo de extratores determinísticos para saídas de ferramentas do Claude Code — TCC, Fases 0–2 do escopo de 80h (classificador, extratores de `pytest`/`git diff`, truncamento pareado, logger).

Spec: `docs/superpowers/specs/2026-09-14-extractors-prototype-design.md`
Plano de implementação: `docs/superpowers/plans/2026-09-14-extractors-prototype.md`

## Setup

```bash
uv sync
```

## Rodar os testes

```bash
uv run pytest
```

## Hook

O hook `PostToolUse` (`hooks/post_tool_use.py`) roda em **modo log**: observa chamadas da tool `Bash` que casem com `pytest` ou `git diff`, grava um evento por chamada em `data/events.jsonl` (comando, saída bruta, versão truncada pareada S2a, versão extraída S2b, contagem de tokens de cada uma), e nunca altera o que o agente vê. Registrado em `.claude/settings.json` (escopo de projeto).

`data/*.jsonl` é gitignored — pode conter código dos repositórios usados durante a coleta.

## Fora de escopo (por enquanto)

Coleta de dataset ao vivo em múltiplos repositórios, réplica contrafactual via API, análise estatística (teste de McNemar) — ver a spec para o raciocínio completo.
