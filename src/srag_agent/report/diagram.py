"""Gera o diagrama conceitual da arquitetura (PDF e PNG): python -m srag_agent.report.diagram"""

import math
import textwrap
from collections.abc import Callable
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import (
    Arc,
    Circle,
    Ellipse,
    FancyArrowPatch,
    FancyBboxPatch,
    Rectangle,
    Wedge,
)

OUT_DIR = Path("docs")
WIDTH, HEIGHT = 100, 82
BODY_PT, TITLE_PT = 8, 9.5
FIG_W_IN = 16
IN_PER_UNIT = FIG_W_IN / WIDTH

# (preenchimento, borda)
COLORS = {
    "agent": ("#dbeafe", "#1d4ed8"),
    "gov": ("#fef3c7", "#b45309"),
    "tool": ("#dcfce7", "#15803d"),
    "ext": ("#ede9fe", "#6d28d9"),
    "data": ("#e0f2fe", "#0369a1"),
    "user": ("#f1f5f9", "#475569"),
}
GROUP_FILL = {"agent": "#f3f8ff", "gov": "#fffbeb", "tool": "#f3fcf6", "ext": "#f7f5ff"}


# ---- Ícones -------------------------------------------------------------------------------
def user_icon(ax, cx, cy, color, s=4.6):
    ax.add_patch(Circle((cx, cy + 0.42 * s), 0.3 * s, facecolor=color, edgecolor=color, zorder=5))
    ax.add_patch(Wedge((cx, cy - 0.62 * s), 0.66 * s, 0, 180, facecolor=color, edgecolor=color, zorder=5))


def database_icon(ax, cx, cy, color, w=6.4, h=6.0):
    eh = h * 0.30
    ytop, ybot = cy + h / 2 - eh / 2, cy - h / 2 + eh / 2
    ax.add_patch(Rectangle((cx - w / 2, ybot), w, ytop - ybot, facecolor=color, edgecolor=color, zorder=4))
    ax.add_patch(Ellipse((cx, ybot), w, eh, facecolor=color, edgecolor=color, zorder=4))
    for frac in (1 / 3, 2 / 3):
        ax.add_patch(Arc((cx, ybot + (ytop - ybot) * frac), w, eh, theta1=180, theta2=360,
                         edgecolor="white", linewidth=1.4, zorder=5))
    ax.add_patch(Ellipse((cx, ytop), w, eh, facecolor="white", edgecolor=color, linewidth=1.6, zorder=6))


def globe_icon(ax, cx, cy, color, r=3.2):
    ax.add_patch(Circle((cx, cy), r, facecolor="white", edgecolor=color, linewidth=1.8, zorder=5))
    ax.add_patch(Ellipse((cx, cy), r * 0.95, 2 * r, fill=False, edgecolor=color, linewidth=1.2, zorder=6))
    ax.plot([cx, cx], [cy - r, cy + r], color=color, linewidth=1.2, zorder=6)
    for dy in (-0.55 * r, 0, 0.55 * r):
        half = math.sqrt(r * r - dy * dy)
        ax.plot([cx - half, cx + half], [cy + dy, cy + dy], color=color, linewidth=1.2, zorder=6)


Icon = Callable[..., None]


class Diagram:
    def __init__(self):
        self.fig, self.ax = plt.subplots(figsize=(FIG_W_IN, FIG_W_IN * HEIGHT / WIDTH))
        self.ax.set_xlim(0, WIDTH)
        self.ax.set_ylim(0, HEIGHT)
        self.ax.set_aspect("equal")
        self.ax.axis("off")
        self.boxes: dict[str, tuple[float, float, float, float]] = {}
        self.texts: list[tuple[str, object]] = []

    def group(self, kind, x0, y0, x1, y1, label):
        _, edge = COLORS[kind]
        self.ax.add_patch(FancyBboxPatch(
            (x0, y0), x1 - x0, y1 - y0, boxstyle="round,pad=0,rounding_size=1.6",
            facecolor=GROUP_FILL[kind], edgecolor=edge, linewidth=1.4, linestyle=(0, (5, 3)), zorder=0))
        t = self.ax.text(x0 + 1.2, y1 - 1.0, label, ha="left", va="top", fontsize=TITLE_PT + 0.5,
                         fontweight="bold", color=edge, zorder=2)
        self.boxes[f"group:{label}"] = (x0, y0, x1, y1)
        self.texts.append((f"group:{label}", t))

    def node(self, key, kind, x0, y0, x1, y1, title, body, icon: Icon | None = None, icon_h=0.0):
        face, edge = COLORS[kind]
        self.ax.add_patch(FancyBboxPatch(
            (x0, y0), x1 - x0, y1 - y0, boxstyle="round,pad=0,rounding_size=1.0",
            facecolor=face, edgecolor=edge, linewidth=1.6, zorder=3))
        cx = (x0 + x1) / 2
        if icon:
            icon(self.ax, cx, y1 - 1.0 - icon_h / 2, edge)
        top = y1 - 1.0 - (icon_h + 0.8 if icon else 0)
        chars = max(10, int((x1 - x0 - 1.6) * IN_PER_UNIT * 72 / (BODY_PT * 0.66)))
        wrapped = "\n".join(textwrap.fill(p, chars) for p in body.split("\n"))
        t1 = self.ax.text(cx, top, title, ha="center", va="top", fontsize=TITLE_PT,
                          fontweight="bold", color=edge, zorder=7)
        t2 = self.ax.text(cx, top - 3.0, wrapped, ha="center", va="top", fontsize=BODY_PT,
                          color="#1f2937", linespacing=1.3, zorder=7)
        self.boxes[key] = (x0, y0, x1, y1)
        self.texts += [(key, t1), (key, t2)]

    def arrow(self, a, b, label=None, both=False, color="#374151", width=1.6, label_pos=0.5):
        self.ax.add_patch(FancyArrowPatch(
            a, b, arrowstyle="<|-|>" if both else "-|>", mutation_scale=14,
            linewidth=width, color=color, zorder=8, shrinkA=0, shrinkB=0))
        if label:
            self.ax.text(a[0] + (b[0] - a[0]) * label_pos, a[1] + (b[1] - a[1]) * label_pos, label,
                         fontsize=7.5, ha="center", va="center", color=color, style="italic", zorder=9,
                         bbox={"facecolor": "white", "edgecolor": "none", "pad": 1.2})

    def overflows(self) -> list[str]:
        """Textos que passam da borda da sua caixa (verificação automática de layout)."""
        self.fig.canvas.draw()
        inv = self.ax.transData.inverted()
        renderer = self.fig.canvas.get_renderer()
        bad = []
        for key, text in self.texts:
            bb = text.get_window_extent(renderer)
            (x0, y0), (x1, y1) = inv.transform((bb.x0, bb.y0)), inv.transform((bb.x1, bb.y1))
            bx0, by0, bx1, by1 = self.boxes[key]
            if x0 < bx0 + 0.2 or x1 > bx1 - 0.2 or y0 < by0 + 0.2 or y1 > by1:
                bad.append(key)
        return bad


def build_diagram() -> Diagram:
    d = Diagram()
    d.ax.text(50, 80.2, "SRAG Agent — Arquitetura da solução", ha="center", fontsize=17,
              fontweight="bold", color="#111827")
    d.ax.text(50, 77.2, "Indicium HealthCare Inc. · PoC de monitoramento de SRAG com IA generativa",
              ha="center", fontsize=9.5, color="#4b5563")

    # ---- Fluxo principal: usuário -> agente -> usuário -------------------------------------
    d.group("agent", 14, 55, 86, 74, "Agente Principal (Orquestrador) — fluxo principal")
    steps = [
        ("Coletar métricas", "Chama a tool de métricas pela governança"),
        ("Coletar notícias", "Chama a tool de notícias pela governança"),
        ("Redigir com LLM", "Claude via API (tool use) ou claude -p"),
        ("Validar saída", "Confere as 4 métricas e mascara dados sensíveis"),
        ("Gerar relatório", "Gráficos diário e mensal + HTML"),
    ]
    centers = []
    for i, (title, body) in enumerate(steps):
        x0 = 16 + i * 14
        d.node(f"step{i}", "agent", x0, 55.8, x0 + 12, 70.0, f"{i + 1}. {title}", body)
        centers.append(x0 + 6)
    for i in range(4):
        d.arrow((16 + i * 14 + 12, 62.5), (16 + (i + 1) * 14, 62.5))

    d.node("user_in", "user", 0.8, 55.8, 12.4, 70.0, "Usuário", "Entrada:\npython -m srag_agent",
           icon=user_icon, icon_h=5.4)
    d.node("user_out", "user", 87.6, 55.8, 99.2, 70.0, "Usuário", "Saída:\nrelatório HTML",
           icon=user_icon, icon_h=5.4)
    d.arrow((12.4, 62.5), (16, 62.5), color="#0f172a", width=2.2)
    d.arrow((84, 62.5), (87.6, 62.5), color="#0f172a", width=2.2)

    # ---- Governança --------------------------------------------------------------------------
    d.group("gov", 14, 38, 86, 51, "Governança e auditoria")
    d.node("gov", "gov", 16, 39, 59, 48, "GovernedExecutor — único caminho para as tools",
           "Allowlist · limite de 6 chamadas · validação de parâmetros\n"
           "Notícias: remove prompt injection e delimita como dado")
    d.node("audit", "gov", 65, 39, 84, 48, "Log de auditoria",
           "JSONL por execução, com hash encadeado")
    d.arrow((59, 43.5), (65, 43.5), label="eventos", label_pos=0.5)
    d.arrow((centers[0], 55.8), (centers[0], 48), color="#b45309")
    d.arrow((centers[1], 55.8), (centers[1], 48), color="#b45309")

    # ---- Tools -------------------------------------------------------------------------------
    d.group("tool", 14, 22, 86, 35, "Tools do agente")
    d.node("tmetrics", "tool", 16, 23, 48, 32, "get_srag_metrics",
           "Taxas de aumento de casos, mortalidade, UTI e vacinação\n"
           "Séries de 30 dias (diária) e 12 meses (mensal)")
    d.node("tnews", "tool", 52, 23, 84, 32, "search_news",
           "Agrega feeds RSS e filtra por palavras-chave de SRAG\n"
           "Remove HTML e limita o tamanho dos resumos")
    d.arrow((30, 39), (30, 32), color="#15803d")
    d.arrow((55, 39), (64, 32), color="#15803d")

    # ---- Dados e fontes externas -------------------------------------------------------------
    d.group("ext", 1, 0.8, 86, 19.5, "Dados e fontes externas")
    d.node("datasus", "ext", 3, 2, 21, 16.5, "Open DATASUS",
           "dadosabertos.saude.gov.br\nCSVs de SRAG 2025 e 2026", icon=globe_icon, icon_h=6.4)
    d.node("duck", "data", 28, 2, 46, 16.5, "DuckDB",
           "Somente leitura\n8 colunas, sem identificadores", icon=database_icon, icon_h=6.0)
    d.node("news", "ext", 56, 2, 84, 16.5, "Fontes de notícias",
           "RSS: Google News, G1 Saúde\nFiocruz (via Google News)", icon=globe_icon, icon_h=6.4)
    d.arrow((21, 9), (28, 9), label="CSV + limpeza", color="#6d28d9", label_pos=0.5)
    d.arrow((37, 16.5), (37, 23), label="SELECT", color="#0369a1")
    d.arrow((70, 16.5), (70, 23), label="RSS", color="#6d28d9")
    return d


def save(out_dir: Path = OUT_DIR) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    d = build_diagram()
    paths = [out_dir / "arquitetura.pdf", out_dir / "arquitetura.png"]
    for p in paths:
        d.fig.savefig(p, dpi=160, bbox_inches="tight")
    plt.close(d.fig)
    return paths


if __name__ == "__main__":
    bad = build_diagram().overflows()
    if bad:
        raise SystemExit(f"Texto fora da caixa em: {bad}")
    for path in save():
        print(path)
