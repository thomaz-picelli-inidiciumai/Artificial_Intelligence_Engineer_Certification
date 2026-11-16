import json
import subprocess

import pytest

from srag_agent.agent.cli_agent import CliReportAgent
from srag_agent.agent.factory import create_agent
from srag_agent.agent.orchestrator import AgentError, ReportAgent
from srag_agent.governance.audit import AuditLog
from srag_agent.governance.executor import GovernedExecutor

METRICS = {"metrics": {"case_growth_rate": -21.87, "mortality_rate": 4.57,
                       "icu_rate": 26.58, "vaccination_rate": 40.5}}
GOOD = "Aumento -21,87%. Mortalidade 4,57%. UTI 26,58%. Vacinação 40,50%."


def _ok(text, is_error=False, returncode=0):
    out = json.dumps({"result": text, "is_error": is_error, "usage": {"output_tokens": 5},
                      "total_cost_usd": 0.01})
    return subprocess.CompletedProcess([], returncode, stdout=out, stderr="")


class FakeRunner:
    def __init__(self, *results):
        self._results = iter(results)
        self.calls = []

    def __call__(self, cmd, **kwargs):
        self.calls.append((cmd, kwargs))
        return next(self._results)


def _agent(tmp_path, runner):
    audit = AuditLog(tmp_path, run_id="c1")
    executor = GovernedExecutor(audit, registry={
        "get_srag_metrics": lambda: METRICS,
        "search_news": lambda max_items=5: [{"title": "x", "summary": "y"}],
    })
    return CliReportAgent(executor, audit, model="opus", runner=runner), audit


def _events(audit):
    return [json.loads(x)["event"] for x in audit.path.read_text("utf-8").splitlines()]


def test_cli_call_is_locked_down_and_returns_report(tmp_path, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "valor-de-teste")
    runner = FakeRunner(_ok(GOOD))
    agent, audit = _agent(tmp_path, runner)
    assert agent.run() == GOOD
    cmd, kwargs = runner.calls[0]
    assert cmd[cmd.index("--tools") + 1] == ""  # nenhuma ferramenta
    assert "--no-session-persistence" in cmd and "--model" in cmd
    assert "ANTHROPIC_API_KEY" not in kwargs["env"]  # força o login da conta
    assert "case_growth_rate" in kwargs["input"]  # dados coletados vão no prompt
    assert "cli_response" in _events(audit) and AuditLog.verify(audit.path)


def test_bad_numbers_trigger_one_correction(tmp_path):
    runner = FakeRunner(_ok("Mortalidade 9,99%."), _ok(GOOD))
    agent, audit = _agent(tmp_path, runner)
    assert agent.run() == GOOD
    assert len(runner.calls) == 2 and _events(audit).count("report_check") == 2


def test_persistent_issues_add_warning_and_redact_pii(tmp_path):
    agent, _ = _agent(tmp_path, FakeRunner(_ok("sem números a@b.com"), _ok("ainda sem a@b.com")))
    report = agent.run()
    assert "Aviso de qualidade" in report and "a@b.com" not in report


def test_cli_errors_raise_agent_error(tmp_path):
    agent, _ = _agent(tmp_path, FakeRunner(_ok("Credit balance is too low", is_error=True)))
    with pytest.raises(AgentError):
        agent.run()
    bad = subprocess.CompletedProcess([], 1, stdout="não é json", stderr="boom")
    agent, _ = _agent(tmp_path, FakeRunner(bad))
    with pytest.raises(AgentError):
        agent.run()


def test_factory_selects_backend(tmp_path, monkeypatch):
    audit = AuditLog(tmp_path, run_id="f1")
    executor = GovernedExecutor(audit, registry={})
    monkeypatch.setenv("ANTHROPIC_API_KEY", "valor-de-teste")
    assert isinstance(create_agent(executor, audit, "cli"), CliReportAgent)
    assert isinstance(create_agent(executor, audit, "api"), ReportAgent)
    with pytest.raises(ValueError):
        create_agent(executor, audit, "outro")
