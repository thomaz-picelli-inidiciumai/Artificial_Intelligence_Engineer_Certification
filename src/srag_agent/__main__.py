"""Ponto de entrada: python -m srag_agent"""

import sys

import anthropic
from dotenv import load_dotenv

from srag_agent.agent.orchestrator import AgentError, ReportAgent
from srag_agent.governance.audit import AuditLog
from srag_agent.governance.executor import GovernedExecutor


def main() -> int:
    load_dotenv()
    audit = AuditLog()
    agent = ReportAgent(GovernedExecutor(audit), audit)
    try:
        report = agent.run()
    except AgentError as exc:
        print(f"Falha ao gerar o relatório: {exc}", file=sys.stderr)
        return 1
    except anthropic.APIStatusError as exc:
        audit.log("api_error", status=exc.status_code, message=exc.message)
        print(f"Erro da API Anthropic ({exc.status_code}): {exc.message}", file=sys.stderr)
        return 1
    print(report)
    print(f"\n[auditoria: {audit.path}]", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
