"""Agente orquestrador: loop de tool use com Claude, sempre via GovernedExecutor."""

import json
import os

import anthropic

from srag_agent.agent.prompts import SYSTEM_PROMPT
from srag_agent.governance.audit import AuditLog
from srag_agent.governance.executor import GovernedExecutor
from srag_agent.governance.guardrails import GuardrailViolation, check_report, redact_pii
from srag_agent.tools.metrics_tool import TOOL_SPEC as METRICS_SPEC
from srag_agent.tools.news_tool import TOOL_SPEC as NEWS_SPEC

DEFAULT_MODEL = "claude-opus-5-5"
MAX_TURNS = 8
MAX_TOKENS = 16000
TOOLS = [METRICS_SPEC, NEWS_SPEC]
FALLBACK_BETA = "server-side-fallback-2026-07-01"


class AgentError(Exception):
    """O agente não conseguiu concluir o relatório."""


class ReportAgent:
    def __init__(
        self,
        executor: GovernedExecutor,
        audit: AuditLog,
        client: anthropic.Anthropic | None = None,
        model: str | None = None,
    ):
        self.executor = executor
        self.audit = audit
        self.client = client or anthropic.Anthropic()  # lê ANTHROPIC_API_KEY do ambiente
        self.model = model or os.getenv("SRAG_MODEL", DEFAULT_MODEL)
        self.metrics: dict = {}

    def run(self) -> str:
        messages = [{"role": "user", "content": "Gere o relatório de SRAG."}]
        self.audit.log("agent_start", model=self.model)
        corrected = False
        for turn in range(1, MAX_TURNS + 1):
            response = self._call_model(messages)
            self.audit.log(
                "model_response", turn=turn, stop_reason=response.stop_reason,
                input_tokens=response.usage.input_tokens, output_tokens=response.usage.output_tokens,
            )
            if response.stop_reason == "refusal":
                self.audit.log("agent_refused", details=str(response.stop_details))
                raise AgentError("o modelo recusou a solicitação")
            messages.append({"role": "assistant", "content": response.content})

            if response.stop_reason == "tool_use":
                messages.append({"role": "user", "content": self._run_tools(response.content)})
                continue
            if response.stop_reason != "end_turn":
                raise AgentError(f"parada inesperada: {response.stop_reason}")

            report, _ = redact_pii(self._text(response.content))
            issues = check_report(report, self.metrics.get("metrics", {}))
            self.audit.log("report_check", issues=issues)
            if issues and not corrected:
                corrected = True
                messages.append({"role": "user", "content": (
                    "Corrija o relatório. Problemas encontrados: " + "; ".join(issues)
                    + ". Use exatamente os valores retornados pela tool.")})
                continue
            if issues:
                report += "\n\n> Aviso de qualidade: " + "; ".join(issues)
            self.audit.log("agent_done", turns=turn, report_chars=len(report))
            return report
        raise AgentError(f"limite de {MAX_TURNS} turnos excedido")

    def _call_model(self, messages: list[dict]):
        return self.client.beta.messages.create(
            model=self.model,
            max_tokens=MAX_TOKENS,
            system=SYSTEM_PROMPT,
            tools=TOOLS,
            messages=messages,
            output_config={"effort": "medium"},
            betas=[FALLBACK_BETA],
            fallbacks="default",
        )

    def _run_tools(self, content: list) -> list[dict]:
        results = []
        for block in content:
            if block.type != "tool_use":
                continue
            try:
                output = self.executor.run(block.name, dict(block.input))
                if block.name == "get_srag_metrics":
                    self.metrics = output
                body = {"type": "tool_result", "tool_use_id": block.id,
                        "content": json.dumps(output, ensure_ascii=False, default=str)}
            except GuardrailViolation as exc:
                body = {"type": "tool_result", "tool_use_id": block.id,
                        "content": f"Bloqueado por guardrail: {exc}", "is_error": True}
            except Exception as exc:  # noqa: BLE001 - o erro volta ao modelo e já foi auditado
                body = {"type": "tool_result", "tool_use_id": block.id,
                        "content": f"Erro ao executar a tool: {exc}", "is_error": True}
            results.append(body)
        return results

    @staticmethod
    def _text(content: list) -> str:
        return "\n".join(b.text for b in content if b.type == "text").strip()
