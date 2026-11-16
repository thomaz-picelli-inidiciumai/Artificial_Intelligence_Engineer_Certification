"""Backend alternativo: usa `claude -p` (login da conta Claude Code) no lugar da API.

O Python coleta os dados pelo GovernedExecutor e faz UMA chamada à CLI, com todas as
ferramentas do Claude Code desligadas. Assim o modelo só escreve texto, e uma notícia com
prompt injection não consegue acionar Bash, leitura de arquivos ou rede.
"""

import json
import os
import shutil
import subprocess
import tempfile
from collections.abc import Callable

from srag_agent.agent.orchestrator import AgentError
from srag_agent.agent.prompts import SYSTEM_PROMPT_CLI
from srag_agent.governance.audit import AuditLog
from srag_agent.governance.executor import GovernedExecutor
from srag_agent.governance.guardrails import check_report, redact_pii

TIMEOUT_S = 600
MAX_BUDGET_USD = "2"
NEWS_ITEMS = 5
# Estas variáveis fariam a CLI usar a API (e seus créditos) em vez do login da conta.
_DROPPED_ENV = ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN")


class CliReportAgent:
    def __init__(
        self,
        executor: GovernedExecutor,
        audit: AuditLog,
        model: str | None = None,
        runner: Callable[..., subprocess.CompletedProcess] = subprocess.run,
    ):
        self.executor = executor
        self.audit = audit
        self.model = model or os.getenv("SRAG_CLI_MODEL")
        self.runner = runner
        self.metrics: dict = {}

    def run(self) -> str:
        self.audit.log("agent_start", backend="cli", model=self.model)
        self.metrics = self.executor.run("get_srag_metrics")
        news = self.executor.run("search_news", {"max_items": NEWS_ITEMS})
        prompt = self._build_prompt(news)

        text = self._call_cli(prompt)
        report, _ = redact_pii(text)
        issues = check_report(report, self.metrics["metrics"])
        self.audit.log("report_check", issues=issues)
        if issues:  # uma única correção, como no backend de API
            text = self._call_cli(
                prompt + "\n\nRelatório anterior:\n" + text + "\n\nCorrija os problemas: "
                + "; ".join(issues) + ". Use exatamente os valores fornecidos."
            )
            report, _ = redact_pii(text)
            issues = check_report(report, self.metrics["metrics"])
            self.audit.log("report_check", issues=issues)
            if issues:
                report += "\n\n> Aviso de qualidade: " + "; ".join(issues)
        self.audit.log("agent_done", report_chars=len(report))
        return report

    def _build_prompt(self, news: list[dict]) -> str:
        return (
            "Gere o relatório de SRAG com os dados abaixo.\n\n"
            f"## Métricas e séries\n{json.dumps(self.metrics, ensure_ascii=False, default=str)}\n\n"
            f"## Notícias recentes\n{json.dumps(news, ensure_ascii=False)}"
        )

    def _command(self) -> list[str]:
        exe = shutil.which("claude")
        if not exe:
            raise AgentError("CLI `claude` não encontrada no PATH")
        cmd = [
            exe, "-p",
            "--tools", "",  # nenhuma ferramenta: o modelo só gera texto
            "--system-prompt", SYSTEM_PROMPT_CLI,
            "--output-format", "json",
            "--no-session-persistence",
            "--setting-sources", "",  # não carrega hooks/plugins/CLAUDE.md do ambiente
            "--disable-slash-commands",
            "--effort", "medium",
            "--max-budget-usd", MAX_BUDGET_USD,
        ]
        if self.model:
            cmd += ["--model", self.model]
        return cmd

    def _call_cli(self, prompt: str) -> str:
        env = {k: v for k, v in os.environ.items() if k not in _DROPPED_ENV}
        try:
            with tempfile.TemporaryDirectory() as workdir:  # sem CLAUDE.md nem código por perto
                proc = self.runner(
                    self._command(), input=prompt, capture_output=True, text=True,
                    encoding="utf-8", timeout=TIMEOUT_S, cwd=workdir, env=env,
                )
        except subprocess.TimeoutExpired as exc:
            self.audit.log("cli_timeout", seconds=TIMEOUT_S)
            raise AgentError("a CLI excedeu o tempo limite") from exc
        try:
            data = json.loads(proc.stdout)
        except json.JSONDecodeError as exc:
            self.audit.log("cli_error", returncode=proc.returncode, stderr=proc.stderr[:500])
            raise AgentError("resposta inválida da CLI") from exc
        self.audit.log(
            "cli_response", is_error=data.get("is_error"), usage=data.get("usage"),
            cost_usd=data.get("total_cost_usd"), returncode=proc.returncode,
        )
        if proc.returncode != 0 or data.get("is_error"):
            raise AgentError(f"a CLI retornou erro: {str(data.get('result'))[:300]}")
        return str(data["result"]).strip()
