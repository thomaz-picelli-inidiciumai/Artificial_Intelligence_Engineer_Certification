import pandas as pd
import pytest

from srag_agent.data.cleaning import clean
from srag_agent.data.metrics import compute_metrics, daily_cases, monthly_cases


def _raw(rows: list[dict]) -> pd.DataFrame:
    base = {
        "DT_SIN_PRI": None, "SG_UF_NOT": "SP", "HOSPITAL": "1", "UTI": "2",
        "EVOLUCAO": "1", "DT_EVOLUCA": None, "VACINA_COV": "2",
    }
    return pd.DataFrame([{**base, **r} for r in rows])


def test_clean_handles_invalid_values():
    raw = _raw([
        {"DT_NOTIFIC": "10/01/2025", "UTI": "7", "EVOLUCAO": None},
        {"DT_NOTIFIC": "data-ruim"},
        {"DT_NOTIFIC": "10/01/2025", "DT_EVOLUCA": "01/01/2025"},
    ])
    df = clean(raw)
    assert len(df) == 2  # data inválida descartada
    assert df.loc[0, "UTI"] == 9 and df.loc[0, "EVOLUCAO"] == 9
    assert pd.isna(df.loc[1, "DT_EVOLUCA"])  # desfecho antes da notificação


def test_metrics_values():
    as_of = pd.Timestamp("2025-03-31")
    rows = (
        # janela anterior (01/02 a 02/03): 2 casos
        [{"DT_NOTIFIC": "15/02/2025"}] * 2
        # janela atual (02/03 a 31/03): 4 casos
        + [{"DT_NOTIFIC": "10/03/2025", "EVOLUCAO": "2", "UTI": "1", "VACINA_COV": "1"}]
        + [{"DT_NOTIFIC": "11/03/2025", "EVOLUCAO": "1", "UTI": "2"}] * 2
        + [{"DT_NOTIFIC": "12/03/2025", "EVOLUCAO": "9", "HOSPITAL": "2", "VACINA_COV": "9"}]
    )
    m = compute_metrics(clean(_raw(rows)), as_of=as_of)
    assert (m.cases_current, m.cases_previous) == (4, 2)
    assert m.case_growth_rate == 100.0
    assert m.mortality_rate == pytest.approx(33.33)  # 1 óbito / 3 com desfecho
    assert m.icu_rate == pytest.approx(33.33)  # 1 UTI / 3 internados
    assert m.vaccination_rate == pytest.approx(33.33)  # 1 vacinado / 3 com informação


def test_growth_is_none_without_previous_window():
    df = clean(_raw([{"DT_NOTIFIC": "10/03/2025"}]))
    assert compute_metrics(df, as_of=pd.Timestamp("2025-03-31")).case_growth_rate is None


def test_series_shapes_fill_gaps():
    df = clean(_raw([{"DT_NOTIFIC": "10/03/2025"}, {"DT_NOTIFIC": "10/01/2025"}]))
    as_of = pd.Timestamp("2025-03-31")
    daily = daily_cases(df, as_of)
    monthly = monthly_cases(df, as_of)
    assert len(daily) == 30 and daily.sum() == 1
    assert len(monthly) == 12 and monthly.sum() == 2
