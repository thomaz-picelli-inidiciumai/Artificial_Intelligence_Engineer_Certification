"""Cálculo das métricas do relatório de SRAG (funções puras sobre o DataFrame limpo).

Janela padrão: 30 dias terminando em `as_of`. A data de referência é, por padrão,
a última notificação do dataset, e não "hoje", porque os dados do DATASUS têm atraso.
"""

from dataclasses import asdict, dataclass

import pandas as pd

WINDOW_DAYS = 30


@dataclass(frozen=True)
class Metrics:
    as_of: str
    window_days: int
    cases_current: int
    cases_previous: int
    case_growth_rate: float | None  # variação % da janela atual vs. anterior
    mortality_rate: float | None  # óbitos por SRAG / casos com desfecho conhecido
    icu_rate: float | None  # internados em UTI / internados
    vaccination_rate: float | None  # casos vacinados / casos com informação (proxy)

    def to_dict(self) -> dict:
        return asdict(self)


def _ratio(numerator: int, denominator: int) -> float | None:
    return round(100 * numerator / denominator, 2) if denominator else None


def default_as_of(df: pd.DataFrame) -> pd.Timestamp:
    return df["DT_NOTIFIC"].max().normalize()


def _window(df: pd.DataFrame, end: pd.Timestamp, days: int) -> pd.DataFrame:
    start = end - pd.Timedelta(days=days - 1)
    return df[(df["DT_NOTIFIC"] >= start) & (df["DT_NOTIFIC"] <= end)]


def compute_metrics(
    df: pd.DataFrame, as_of: pd.Timestamp | None = None, window_days: int = WINDOW_DAYS
) -> Metrics:
    end = (as_of or default_as_of(df)).normalize()
    current = _window(df, end, window_days)
    previous = _window(df, end - pd.Timedelta(days=window_days), window_days)

    growth = (
        round(100 * (len(current) - len(previous)) / len(previous), 2) if len(previous) else None
    )

    known_outcome = current["EVOLUCAO"].isin([1, 2, 3])
    hospitalized = current["HOSPITAL"] == 1
    known_vaccine = current["VACINA_COV"].isin([1, 2])

    return Metrics(
        as_of=end.date().isoformat(),
        window_days=window_days,
        cases_current=len(current),
        cases_previous=len(previous),
        case_growth_rate=growth,
        mortality_rate=_ratio((current["EVOLUCAO"] == 2).sum(), known_outcome.sum()),
        icu_rate=_ratio((current["UTI"] == 1)[hospitalized].sum(), hospitalized.sum()),
        vaccination_rate=_ratio(
            (current["VACINA_COV"] == 1).sum(), known_vaccine.sum()
        ),
    )


def daily_cases(df: pd.DataFrame, as_of: pd.Timestamp | None = None, days: int = 30) -> pd.Series:
    """Casos por dia nos últimos `days` dias (dias sem casos aparecem com 0)."""
    end = (as_of or default_as_of(df)).normalize()
    window = _window(df, end, days)
    index = pd.date_range(end - pd.Timedelta(days=days - 1), end, freq="D")
    return window.groupby(window["DT_NOTIFIC"].dt.normalize()).size().reindex(index, fill_value=0)


def monthly_cases(
    df: pd.DataFrame, as_of: pd.Timestamp | None = None, months: int = 12
) -> pd.Series:
    """Casos por mês nos últimos `months` meses (inclui o mês corrente de `as_of`)."""
    end = (as_of or default_as_of(df)).normalize()
    last = end.to_period("M")
    periods = pd.period_range(last - (months - 1), last, freq="M")
    counts = df.groupby(df["DT_NOTIFIC"].dt.to_period("M")).size()
    return counts.reindex(periods, fill_value=0)
