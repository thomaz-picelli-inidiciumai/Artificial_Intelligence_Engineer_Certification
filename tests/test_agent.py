import json
from types import SimpleNamespace as NS

import pytest

from srag_agent.agent.orchestrator import AgentError, ReportAgent
from srag_agent.governance.audit import AuditLog
from srag_agent.governance.executor import GovernedExecutor

METRICS = {"metrics": {"case_growth_rate": -21.87, "mortality_rate": 4.57,
                       "icu_rate": 26.58, "vaccination_rate": 40.5}}
GOOD = "Aumento -21,87%. Mortalidade 4,57%. UTI 26,58%. Vacinação 40,50%."
USAGE = NS(input_tokens=1, output_tokens=1)


def _tool(id_, name, **inp):
    return NS(type="tool_use", id=id_, name=name, input=inp)


def _text(t):
    return NS(type="text", text=t)


def _resp(stop, *blocks):
    return NS(stop_reason=stop, content=list(blocks), usage=USAGE, stop_details=None)


class FakeClient:
    def __init__(self, responses):
        self._responses = iter(responses)
        self.calls = []
        self.beta = NS(messages=NS(create=self._create))

    def _create(self, **kwargs):
        self.calls.append({**kwargs, "messages": list(kwargs["messages"])})  # snapshot
        return next(self._responses)


def _agent(tmp_path, responses):
    audit = AuditLog(tmp_path, run_id="a1")
    executor = GovernedExecutor(audit, registry={
        "get_srag_metrics": lambda: METRICS,
        "search_news": lambda max_items=5: [],
    })
    return ReportAgent(executor, audit, client=FakeClient(responses), model="m"), audit


def _events(audit):
    return [json.loads(x)["event"] for x in audit.path.read_text("utf-8").splitlines()]


def test_full_flow_returns_report_and_audits(tmp_path):
    agent, audit = _agent(tmp_path, [
        _resp("tool_use", _tool("1", "get_srag_metrics"), _tool("2", "search_news", max_items=3)),
        _resp("end_turn", _text(GOOD)),
    ])
    assert agent.run() == GOOD
    sent = agent.client.calls[1]["messages"][-1]["content"]
    assert [b["tool_use_id"] for b in sent] == ["1", "2"]  # resultados juntos, na mesma mensagem
    assert _events(audit)[0] == "agent_start" and _events(audit)[-1] == "agent_done"
    assert AuditLog.verify(audit.path)


def test_blocked_tool_goes_back_to_model_as_error(tmp_path):
    agent, audit = _agent(tmp_path, [
        _resp("tool_use", _tool("1", "drop_table")),
        _resp("end_turn", _text(GOOD)),
    ])
    agent.run()
    result = agent.client.calls[1]["messages"][-1]["content"][0]
    assert result["is_error"] and "guardrail" in result["content"]
    assert "tool_blocked" in _events(audit)


def test_report_with_wrong_numbers_gets_one_correction(tmp_path):
    agent, audit = _agent(tmp_path, [
        _resp("tool_use", _tool("1", "get_srag_metrics")),
        _resp("end_turn", _text("Mortalidade 9,99%.")),
        _resp("end_turn", _text(GOOD)),
    ])
    assert agent.run() == GOOD
    assert _events(audit).count("report_check") == 2


def test_persistent_issues_add_warning_and_pii_is_redacted(tmp_path):
    agent, _ = _agent(tmp_path, [
        _resp("tool_use", _tool("1", "get_srag_metrics")),
        _resp("end_turn", _text("Sem números. Contato a@b.com")),
        _resp("end_turn", _text("Ainda sem números. Contato a@b.com")),
    ])
    report = agent.run()
    assert "Aviso de qualidade" in report and "a@b.com" not in report


def test_refusal_and_turn_limit_raise(tmp_path):
    agent, _ = _agent(tmp_path, [_resp("refusal")])
    with pytest.raises(AgentError):
        agent.run()
    loop = [_resp("tool_use", _tool(str(i), "get_srag_metrics")) for i in range(20)]
    agent, _ = _agent(tmp_path, loop)
    with pytest.raises(AgentError):
        agent.run()
