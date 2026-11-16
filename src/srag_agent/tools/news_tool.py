"""Tool do agente: busca notícias recentes sobre SRAG em feeds RSS."""

import html
import logging
import re
from collections.abc import Callable
from urllib.parse import quote

import feedparser

logger = logging.getLogger(__name__)

FEEDS = {
    "Google News": (
        "https://news.google.com/rss/search?q="
        + quote("síndrome respiratória aguda grave OR SRAG OR influenza OR VSR")
        + "&hl=pt-BR&gl=BR&ceid=BR:pt-419"
    ),
    "G1 Saúde": "https://g1.globo.com/rss/g1/saude/",
    # A Fiocruz não publica RSS oficial; usamos o Google News restrito ao domínio do portal.
    "Fiocruz": (
        "https://news.google.com/rss/search?q="
        + quote("site:portal.fiocruz.br (InfoGripe OR SRAG OR influenza OR covid)")
        + "&hl=pt-BR&gl=BR&ceid=BR:pt-419"
    ),
}
KEYWORDS = ("srag", "síndrome respiratória", "influenza", "gripe", "covid", "vsr", "sincicial")
MAX_SUMMARY_CHARS = 300

TOOL_SPEC = {
    "name": "search_news",
    "description": (
        "Busca notícias recentes (RSS: Google News, G1 Saúde, Fiocruz) sobre SRAG e vírus "
        "respiratórios, para contextualizar as métricas. Retorna título, fonte, data, link e resumo."
    ),
    "input_schema": {
        "type": "object",
        "properties": {"max_items": {"type": "integer", "minimum": 1, "maximum": 10}},
        "required": [],
    },
}

Parser = Callable[[str], object]


def _clean_text(text: str) -> str:
    """Remove HTML e limita o tamanho: notícias são conteúdo não confiável."""
    plain = re.sub(r"<[^>]+>", " ", html.unescape(text or ""))
    return re.sub(r"\s+", " ", plain).strip()[:MAX_SUMMARY_CHARS]


def _is_relevant(title: str, summary: str) -> bool:
    haystack = f"{title} {summary}".lower()
    return any(k in haystack for k in KEYWORDS)


def search_news(max_items: int = 5, parser: Parser = feedparser.parse) -> list[dict]:
    """Agrega feeds, filtra por relevância e devolve os itens mais recentes."""
    items: list[dict] = []
    for source, url in FEEDS.items():
        try:
            feed = parser(url)
        except Exception:  # um feed fora do ar não derruba o relatório
            logger.warning("Falha ao ler o feed %s", source, exc_info=True)
            continue
        for entry in getattr(feed, "entries", []):
            title = _clean_text(entry.get("title", ""))
            summary = _clean_text(entry.get("summary", ""))
            if title and _is_relevant(title, summary):
                items.append(
                    {
                        "title": title,
                        "source": source,
                        "published": entry.get("published", ""),
                        "link": entry.get("link", ""),
                        "summary": summary,
                        "_sort": tuple(entry.get("published_parsed") or ()),
                    }
                )
    items.sort(key=lambda i: i["_sort"], reverse=True)
    return [{k: v for k, v in i.items() if k != "_sort"} for i in items[:max_items]]
