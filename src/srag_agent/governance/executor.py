"""Executor governado: único caminho pelo qual o agente chama tools.

Aplica allowlist e limites, neutraliza conteúdo externo e audita cada decisão.
"""

from collections.abc import Callable

from srag_agent.governance.audit import AuditLog
from srag_agent.governance.guardrails import (
    GuardrailViolation,
    ToolPolicy,
    neutralize_untrusted,
    wrap_untrusted,
)
from srag_agent.tools.metrics_tool import get_srag_metrics
from srag_agent.tools.news_tool import search_news

REGISTRY: dict[str, Callable[..., object]] = {
    "get_srag_metrics": get_srag_metrics,
    "search_news": search_news,
}


class GovernedExecutor:
    def __init__(self, audit: AuditLog, policy: ToolPolicy | None = None,
                 registry: dict[str, Callable[..., object]] | None = None):
        self.audit = audit
        self.policy = policy or ToolPolicy()
        self.registry = registry or REGISTRY

    def run(self, name: str, tool_input: dict | None = None) -> object:
        tool_input = tool_input or {}
        try:
            self.policy.check(name, tool_input)
        except GuardrailViolation as exc:
            self.audit.log("tool_blocked", tool=name, input=tool_input, reason=str(exc))
            raise
        self.audit.log("tool_call", tool=name, input=tool_input)
        try:
            result = self.registry[name](**tool_input)
        except Exception as exc:
            self.audit.log("tool_error", tool=name, error=repr(exc))
            raise
        if name == "search_news":
            result = self._sanitize_news(result)
        self.audit.log("tool_result", tool=name, summary=self._summarize(result))
        return result

    def _sanitize_news(self, items: list[dict]) -> list[dict]:
        removed_total = 0
        safe = []
        for item in items:
            clean = dict(item)
            for key in ("title", "summary"):
                clean[key], removed = neutralize_untrusted(clean[key])
                removed_total += removed
                clean[key] = wrap_untrusted(clean[key])
            safe.append(clean)
        if removed_total:
            self.audit.log("injection_neutralized", removed=removed_total)
        return safe

    @staticmethod
    def _summarize(result: object) -> dict:
        if isinstance(result, list):
            return {"items": len(result)}
        if isinstance(result, dict):
            return {"keys": sorted(result)}
        return {"type": type(result).__name__}
