"""Monta o relatório final em HTML autocontido (gráficos embutidos em base64)."""

import base64
import html
import re
from pathlib import Path

import markdown

from srag_agent.report.charts import daily_chart, monthly_chart

DEFAULT_DIR = Path("reports")

CARDS = [
    ("case_growth_rate", "Variação de casos", "Janela atual vs. anterior"),
    ("mortality_rate", "Mortalidade", "Óbitos / casos com desfecho"),
    ("icu_rate", "Ocupação de UTI", "Internados em UTI / internados"),
    ("vaccination_rate", "Vacinação", "Casos vacinados (proxy)"),
]

CSS = """
body{font-family:system-ui,sans-serif;max-width:900px;margin:2rem auto;padding:0 1rem;color:#1f2328}
h1{margin-bottom:.2rem}.sub{color:#59636e;margin-top:0}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:12px;margin:1.5rem 0}
.card{border:1px solid #d1d9e0;border-radius:8px;padding:12px}
.card b{display:block;font-size:1.8rem}.card span{color:#59636e;font-size:.8rem}
img{max-width:100%;margin:.5rem 0}blockquote{border-left:4px solid #d4a72c;padding-left:1rem;color:#59636e}
"""


def _fmt(value: float | None) -> str:
    return "n/d" if value is None else f"{value:.2f}".replace(".", ",") + "%"


def _embed(path: Path) -> str:
    data = base64.b64encode(path.read_bytes()).decode("ascii")
    return f'<img alt="{html.escape(path.stem)}" src="data:image/png;base64,{data}">'


def render_markdown(text: str) -> str:
    """Markdown -> HTML sem HTML cru e sem links que não sejam http(s)."""
    escaped = html.escape(text)
    escaped = re.sub(r"(?m)^&gt; ", "> ", escaped)  # preserva citações em bloco
    rendered = markdown.markdown(escaped, extensions=["tables"])
    return re.sub(r'href="(?!https?://)[^"]*"', 'href="#"', rendered)


def build_report(report_md: str, payload: dict, out_dir: Path = DEFAULT_DIR) -> Path:
    """Gera gráficos e o HTML final. Retorna o caminho do HTML."""
    out_dir.mkdir(parents=True, exist_ok=True)
    metrics = payload["metrics"]
    as_of = metrics["as_of"]
    daily = daily_chart(payload["daily_cases_30d"], out_dir / f"casos-diarios-{as_of}.png")
    monthly = monthly_chart(payload["monthly_cases_12m"], out_dir / f"casos-mensais-{as_of}.png")

    cards = "".join(
        f'<div class="card"><span>{label}</span><b>{_fmt(metrics[key])}</b><span>{hint}</span></div>'
        for key, label, hint in CARDS
    )
    page = f"""<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">
<title>Relatório de SRAG — {as_of}</title><style>{CSS}</style></head><body>
<h1>Relatório de SRAG</h1>
<p class="sub">Dados do Open DATASUS até {as_of} · janela de {metrics["window_days"]} dias</p>
<div class="cards">{cards}</div>
{_embed(daily)}{_embed(monthly)}
{render_markdown(report_md)}
</body></html>"""
    out = out_dir / f"relatorio-{as_of}.html"
    out.write_text(page, encoding="utf-8")
    (out_dir / f"relatorio-{as_of}.md").write_text(report_md, encoding="utf-8")
    return out
