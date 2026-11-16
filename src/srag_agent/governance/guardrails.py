"""Guardrails: conteúdo não confiável, dados sensíveis, validação de chamadas e do relatório."""

import re
from dataclasses import dataclass, field

# --- Prompt injection em conteúdo externo (notícias) -------------------------------------
_INJECTION_PATTERNS = [
    r"ignore\s+(all\s+|any\s+)?(previous|prior|above)\s+(instructions|prompts?)",
    r"disregard\s+(all\s+|any\s+)?(previous|prior|above)",
    r"ignor[ea]\s+(todas?\s+)?(as\s+)?(instruç(ões|oes)|ordens)\s+(anteriores|acima)",
    r"desconsidere\s+(as\s+)?(instruç(ões|oes)|ordens)",
    r"you\s+are\s+now\b",
    r"voc[eê]\s+agora\s+[eé]\b",
    r"(system|developer)\s+prompt",
    r"prompt\s+do\s+sistema",
    r"reveal\s+(your|the)\s+(prompt|instructions|api\s*key)",
    r"revele\s+(seu|o)\s+(prompt|instruç|chave)",
    r"</?\s*(system|assistant|tool_use|tool_result)\s*>",
]
_INJECTION_RE = re.compile("|".join(_INJECTION_PATTERNS), re.IGNORECASE)
REMOVED = "[trecho removido por guardrail]"


def neutralize_untrusted(text: str) -> tuple[str, int]:
    """Remove trechos com cara de instrução. Retorna (texto seguro, nº de trechos removidos)."""
    return _INJECTION_RE.subn(REMOVED, text)


def wrap_untrusted(text: str) -> str:
    """Delimita conteúdo externo para o modelo tratá-lo como dado, nunca como instrução."""
    return f"<conteudo_externo>{text}</conteudo_externo>"


# --- Dados sensíveis ---------------------------------------------------------------------
_PII_PATTERNS = {
    "cpf": re.compile(r"\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b"),
    "email": re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b"),
    "telefone": re.compile(r"\(?\b\d{2}\)?\s?9?\d{4}-?\d{4}\b"),
    "chave_api": re.compile(r"\bsk-[A-Za-z0-9_-]{16,}\b"),
}


def redact_pii(text: str) -> tuple[str, list[str]]:
    """Mascara CPF, e-mail, telefone e chaves de API. Retorna (texto, tipos encontrados)."""
    found = []
    for name, pattern in _PII_PATTERNS.items():
        text, count = pattern.subn(f"[{name.upper()} OCULTO]", text)
        if count:
            found.append(name)
    return text, found


# --- Chamadas de tools -------------------------------------------------------------------
class GuardrailViolation(Exception):
    """Uma regra de segurança foi violada; a ação é bloqueada e auditada."""


@dataclass
class ToolPolicy:
    allowed: frozenset[str] = frozenset({"get_srag_metrics", "search_news"})
    max_tool_calls: int = 6
    max_news_items: int = 10
    calls_made: int = field(default=0, init=False)

    def check(self, name: str, tool_input: dict) -> None:
        if name not in self.allowed:
            raise GuardrailViolation(f"tool não permitida: {name}")
        if self.calls_made >= self.max_tool_calls:
            raise GuardrailViolation(f"limite de {self.max_tool_calls} chamadas de tool excedido")
        if name == "search_news":
            n = tool_input.get("max_items", 5)
            if not isinstance(n, int) or isinstance(n, bool) or not 1 <= n <= self.max_news_items:
                raise GuardrailViolation(f"max_items inválido: {n!r}")
        elif tool_input:
            raise GuardrailViolation(f"{name} não aceita parâmetros")
        self.calls_made += 1


# --- Saída do relatório ------------------------------------------------------------------
def check_report(text: str, metrics: dict) -> list[str]:
    """Problemas encontrados no relatório (lista vazia = aprovado)."""
    issues = []
    for key, label in {
        "case_growth_rate": "taxa de aumento de casos",
        "mortality_rate": "taxa de mortalidade",
        "icu_rate": "taxa de ocupação de UTI",
        "vaccination_rate": "taxa de vacinação",
    }.items():
        value = metrics.get(key)
        if value is not None and f"{value:.2f}".replace(".", ",") not in text.replace(".", ","):
            issues.append(f"valor de {label} ({value}) não aparece no relatório")
    _, pii = redact_pii(text)
    issues.extend(f"possível dado sensível no relatório: {p}" for p in pii)
    return issues
