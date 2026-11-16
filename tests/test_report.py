from srag_agent.report.builder import build_report, render_markdown

PAYLOAD = {
    "metrics": {"as_of": "2026-11-08", "window_days": 30, "case_growth_rate": -21.87,
                "mortality_rate": 4.57, "icu_rate": None, "vaccination_rate": 40.5},
    "daily_cases_30d": {f"2026-10-{d:02d}": d * 10 for d in range(10, 31)},
    "monthly_cases_12m": {f"2026-{m:02d}": m * 1000 for m in range(1, 12)},
}


def test_build_report_creates_html_charts_and_markdown(tmp_path):
    out = build_report("## Resumo\nTexto do relatório.", PAYLOAD, tmp_path)
    page = out.read_text(encoding="utf-8")
    assert out.name == "relatorio-2026-11-08.html"
    assert page.count("data:image/png;base64,") == 2  # os dois gráficos embutidos
    assert "-21,87%" in page and "n/d" in page  # None vira n/d
    assert "<h2>Resumo</h2>" in page
    assert (tmp_path / "casos-diarios-2026-11-08.png").stat().st_size > 1000
    assert (tmp_path / "casos-mensais-2026-11-08.png").stat().st_size > 1000


def test_render_markdown_blocks_raw_html_and_unsafe_links():
    html = render_markdown("<script>alert(1)</script>\n[x](javascript:alert(1)) [ok](https://a.com)")
    assert "<script>" not in html
    assert "javascript:" not in html
    assert 'href="https://a.com"' in html


def test_render_markdown_keeps_blockquote_and_tables():
    html = render_markdown("> Aviso\n\n| a | b |\n|---|---|\n| 1 | 2 |")
    assert "<blockquote>" in html and "<table>" in html
