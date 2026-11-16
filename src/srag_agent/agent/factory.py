"""Escolhe o backend de LLM: SRAG_BACKEND=api (padrão, tool use) ou cli (claude -p)."""

import os

from srag_agent.agent.cli_agent import CliReportAgent
from srag_agent.agent.orchestrator import ReportAgent
from srag_agent.governance.audit import AuditLog
from srag_agent.governance.executor import GovernedExecutor

BACKENDS = ("api", "cli")


def create_agent(
    executor: GovernedExecutor, audit: AuditLog, backend: str | None = None
) -> ReportAgent | CliReportAgent:
    backend = (backend or os.getenv("SRAG_BACKEND", "api")).lower()
    if backend == "api":
        return ReportAgent(executor, audit)
    if backend == "cli":
        return CliReportAgent(executor, audit)
    raise ValueError(f"SRAG_BACKEND inválido: {backend!r} (use um de {BACKENDS})")
