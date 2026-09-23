import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import graph as graph_mod
import llm as llm_mod
import memory as memory_mod
import validate_answers

from answer_writer import build_answer
from mock_tg import FakeTigerGraph
import pytest


def stub_synth(state):
    txn = state.get("flagged_txn") or {}
    related = state.get("related_txns") or []
    smalls = [t for t in related if abs(float(t.get("amount", 0) or 0)) < 5]
    flagged_id = str(txn.get("txn_id", ""))
    if len(smalls) >= 3:
        pattern, conf = "card_testing", 0.88
    else:
        pattern, conf = "none", 0.4
    risk = float(txn.get("risk_score", 0) or 0)
    fp = round(min(0.95, max(0.05, 0.45 * risk + 0.55 * conf)), 2)
    customer = state.get("customer_response") or ""
    if customer == "confirmed":
        fp, verdict = 0.08, "legitimate"
    elif customer == "denied":
        fp, verdict = max(fp, 0.78), "fraud"
    else:
        verdict = "fraud" if fp >= 0.85 else ("legitimate" if fp <= 0.15 else "uncertain")
    affected = [flagged_id] if flagged_id else []
    if pattern == "card_testing" and verdict != "legitimate":
        affected.extend(t["txn_id"] for t in smalls if t["txn_id"] != flagged_id)
    return {
        "fraud_probability": fp,
        "pattern": pattern,
        "pattern_description": "Mixed-channel activity inconsistent with cardholder history." if pattern == "undocumented" else "",
        "verdict": verdict,
        "affected_txn_ids": affected,
        "first_suspicious_txn_id": affected[0] if affected else "",
        "confidence_drivers": [f"Pattern {pattern}", f"risk score {risk} as prior"],
        "tokens": 120,
    }


def stub_outputs(state):
    return {
        "summary": f"Stub summary for {state.get('case_id')}.",
        "sar_narrative": f"Stub SAR narrative for {state.get('case_id')}." if state.get("sar_required") else "",
        "stop_reason": state.get("stop_reason", "Stub."),
        "tokens": 300,
    }


@pytest.fixture
def flow_env(monkeypatch):
    tg = FakeTigerGraph()
    monkeypatch.setattr(graph_mod, "tg_client", tg)
    monkeypatch.setattr(llm_mod, "synthesize_evidence", stub_synth)
    monkeypatch.setattr(llm_mod, "generate_outputs", stub_outputs)
    monkeypatch.setattr(memory_mod, "persist_investigation_case", lambda conn, state: "HHG-002")
    return tg


def run_case(case_id="HHG-002", txn_id="3478782", trigger="risk_score"):
    return dict(graph_mod.run_investigation(case_id, txn_id, trigger))


def test_end_to_end_flow(flow_env):
    state = run_case()
    assert state["case_id"] == "HHG-002"
    assert state["verdict"] in ("fraud", "legitimate", "uncertain")
    assert 0.0 <= state["fraud_probability"] <= 1.0
    assert state["pattern"] in ("card_testing", "card_not_present_fraud", "card_not_present_new_device",
                                "out_of_region_use", "account_takeover", "undocumented", "none")


def test_initial_actions_recorded_before_requests(flow_env):
    state = run_case()
    assert state["initial_actions"]
    for action in state["initial_actions"]:
        assert action["route"] in ("auto", "L1", "L2")
        assert action["reason"]


def test_exposure_sum_of_affected_only(flow_env):
    state = run_case()
    amounts = {"3478782": 292.36, "3478101": 2.4, "3478090": 1.1, "3478001": 0.95}
    expected = round(sum(abs(amounts[t]) for t in state["affected_txn_ids"]), 2)
    assert state["exposure_usd"] == expected


def test_tool_calls_counted(flow_env):
    state = run_case()
    assert state["tool_calls"] > 0


def test_graph_visualization_built(flow_env):
    state = run_case()
    ids = {n["id"] for n in state["graph_nodes"]}
    assert "txn-3478782" in ids
    assert any(n["type"] == "device" for n in state["graph_nodes"])
    assert any(n["type"] == "case" for n in state["graph_nodes"])
    assert any(e["label"] == "SIMILAR_TO" for e in state["graph_edges"]) or not state["similar_prior_cases"]


def test_evidence_request_loop_when_mid_probability(flow_env):
    state = run_case()
    if 0.15 < state["fraud_probability"] < 0.85 and state["customer_response"] in ("denied", "confirmed", "no_reply"):
        assert state["evidence_requests"], "mid-probability case should have requested evidence"
        req = state["evidence_requests"][0]
        assert req["type"] in ("customer_validation", "step_up_auth", "analyst_info")
        assert isinstance(req["asked_after_step"], int)
        assert req["assumed_response"]


def test_customer_evidence_added(flow_env):
    state = run_case()
    if state["customer_response"]:
        assert any(e["source"] == "customer" for e in state["evidence"])


def test_persist_case(flow_env):
    state = run_case()
    assert state["written_to_graph"] is True
    assert state["graph_case_id"] == "HHG-002"


def test_sar_matches_final_actions(flow_env):
    state = run_case()
    assert state["sar_required"] == any(a["action"] == "FILE_REPORT" for a in state["final_actions"])


def test_stop_reason_set(flow_env):
    state = run_case()
    assert state["stop_reason"]
    assert "section 6" in state["stop_reason"]


def test_answer_passes_validator(flow_env):
    import answer_writer
    state = run_case()
    answer = answer_writer.build_answer(state)
    import validate_answers as va
    errors = va.validate_answer(answer)
    assert not errors, errors


def test_answer_writer_uses_graph_data(flow_env):
    import answer_writer
    state = run_case()
    answer = answer_writer.build_answer(state)
    assert answer["graph_data"]["nodes"] == state["graph_nodes"]
    assert answer["case_id"] == state["case_id"]