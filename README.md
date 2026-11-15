# Agente de Monitoramento de SRAG

PoC da Indicium HealthCare Inc.: um agente de IA generativa que consulta dados do Open DATASUS e notícias em tempo real para gerar um relatório sobre Síndrome Respiratória Aguda Grave (SRAG).

> Status: em construção (Fase 0 – fundação).

## Objetivo

Relatório com:
- Taxa de aumento de casos
- Taxa de mortalidade
- Taxa de ocupação de UTI
- Taxa de vacinação
- Gráfico de casos diários (últimos 30 dias) e mensais (últimos 12 meses)
- Comentários contextualizados por notícias recentes

## Estrutura

```
src/srag_agent/
  data/         # ingestão e limpeza do CSV do DATASUS
  tools/        # tools do agente (consulta ao banco, notícias)
  agent/        # orquestrador (Claude)
  governance/   # auditoria, guardrails, anonimização
  report/       # geração do relatório e gráficos
tests/
docs/           # diagrama de arquitetura, decisões
```

## Como rodar

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev]"
copy .env.example .env   # preencha ANTHROPIC_API_KEY
```

(Instruções completas serão adicionadas ao final do projeto.)

## Arquitetura, governança, guardrails e dados sensíveis

A documentar nas próximas fases.
