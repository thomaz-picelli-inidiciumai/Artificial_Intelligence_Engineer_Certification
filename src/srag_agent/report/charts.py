"""Gráficos do relatório (matplotlib, backend sem interface gráfica)."""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

COLOR = "#1f6feb"
COLOR_PARTIAL = "#9ec1f7"


def _style(ax, title: str, ylabel: str) -> None:
    ax.set_title(title, fontsize=12, loc="left", fontweight="bold")
    ax.set_ylabel(ylabel)
    ax.grid(axis="y", alpha=0.3)
    ax.spines[["top", "right"]].set_visible(False)


def daily_chart(daily: dict[str, int], path: Path) -> Path:
    """Casos diários dos últimos 30 dias."""
    days, counts = list(daily), list(daily.values())
    fig, ax = plt.subplots(figsize=(9, 3.6))
    ax.plot(days, counts, color=COLOR, linewidth=2, marker="o", markersize=3)
    ax.fill_between(days, counts, color=COLOR, alpha=0.12)
    _style(ax, f"Casos diários de SRAG — últimos {len(days)} dias", "Casos notificados")
    ax.set_xticks(days[::3])
    ax.set_xticklabels([d[5:] for d in days[::3]], rotation=45, fontsize=8)
    ax.set_ylim(bottom=0)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return path


def monthly_chart(monthly: dict[str, int], path: Path) -> Path:
    """Casos mensais dos últimos 12 meses; o último mês (parcial) fica em tom claro."""
    months, counts = list(monthly), list(monthly.values())
    colors = [COLOR] * (len(months) - 1) + [COLOR_PARTIAL]
    fig, ax = plt.subplots(figsize=(9, 3.6))
    bars = ax.bar(months, counts, color=colors)
    ax.bar_label(bars, fmt="{:,.0f}".format, fontsize=7, padding=2)
    _style(ax, f"Casos mensais de SRAG — últimos {len(months)} meses", "Casos notificados")
    ax.set_xticks(range(len(months)))
    ax.set_xticklabels(months, rotation=45, fontsize=8)
    ax.text(0.99, 0.95, "último mês parcial", transform=ax.transAxes, ha="right",
            fontsize=8, color="#555")
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return path
