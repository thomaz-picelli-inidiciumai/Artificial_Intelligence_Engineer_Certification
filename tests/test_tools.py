from types import SimpleNamespace

import pandas as pd

from srag_agent.data.store import build_database
from srag_agent.tools.metrics_tool import get_srag_metrics
from srag_agent.tools.news_tool import FEEDS, search_news


def test_news_filters_cleans_and_sorts():
    entries = [
        {"title": "SRAG sobe <b>no Sul</b>", "summary": "<p>Casos de influenza</p>", "link": "a",
         "published": "x", "published_parsed": (2026, 11, 1, 0, 0, 0, 0, 0, 0)},
        {"title": "Futebol", "summary": "gol", "link": "b"},
        {"title": "Fiocruz alerta para VSR", "summary": "", "link": "c",
         "published": "y", "published_parsed": (2026, 11, 5, 0, 0, 0, 0, 0, 0)},
    ]
    feeds_count = len(FEEDS)
    result = search_news(max_items=10, parser=lambda url: SimpleNamespace(entries=entries))
    assert len(result) == 2 * feeds_count  # irrelevante filtrado, repetido por feed
    assert result[0]["link"] == "c"  # mais recente primeiro
    assert "<" not in result[-1]["title"]


def test_news_survives_broken_feed():
    def broken(url):
        raise RuntimeError("fora do ar")

    assert search_news(parser=broken) == []


def test_metrics_tool_reads_from_duckdb(tmp_path):
    csv = tmp_path / "srag.csv"
    today = pd.Timestamp.today().normalize() - pd.Timedelta(days=2)
    pd.DataFrame(
        {
            "DT_NOTIFIC": [today.strftime("%d/%m/%Y")] * 2,
            "DT_SIN_PRI": [None] * 2, "SG_UF_NOT": ["SP"] * 2, "HOSPITAL": ["1"] * 2,
            "UTI": ["1", "2"], "EVOLUCAO": ["2", "1"], "DT_EVOLUCA": [None] * 2,
            "VACINA_COV": ["1", "2"],
        }
    ).to_csv(csv, sep=";", index=False, encoding="latin-1")
    db = tmp_path / "srag.duckdb"
    assert build_database([csv], db) == 2
    out = get_srag_metrics(db)
    assert out["metrics"]["cases_current"] == 2
    assert out["metrics"]["mortality_rate"] == 50.0
    assert len(out["daily_cases_30d"]) == 30 and len(out["monthly_cases_12m"]) == 12
