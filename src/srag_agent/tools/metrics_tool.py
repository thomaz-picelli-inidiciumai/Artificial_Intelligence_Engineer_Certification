"""Tool do agente: consulta as métricas de SRAG no banco (somente leitura)."""

from pathlib import Path

import pandas as pd

from srag_agent.data.metrics import compute_metrics, daily_cases, monthly_cases
from srag_agent.data.store import DEFAULT_DB, read_cases

TOOL_SPEC = {
    "name": "get_srag_metrics",
    "description": (
        "Retorna as métricas de SRAG calculadas sobre os dados do Open DATASUS: taxa de aumento "
        "de casos, mortalidade, ocupação de UTI e vacinação, mais as séries diária (30 dias) e "
        "mensal (12 meses). Não recebe dados pessoais."
    ),
    "input_schema": {"type": "object", "properties": {}, "required": []},
}


def get_srag_metrics(db_path: Path = DEFAULT_DB) -> dict:
    df = read_cases(db_path)
    metrics = compute_metrics(df)
    as_of = pd.Timestamp(metrics.as_of)
    return {
        "metrics": metrics.to_dict(),
        "daily_cases_30d": {d.date().isoformat(): int(n) for d, n in daily_cases(df, as_of).items()},
        "monthly_cases_12m": {str(p): int(n) for p, n in monthly_cases(df, as_of).items()},
        "notes": [
            "Mês corrente parcial e desfechos recentes em aberto (mortalidade subestimada).",
            "Vacinação é proxy: % de casos de SRAG vacinados contra COVID, não cobertura populacional.",
        ],
    }
