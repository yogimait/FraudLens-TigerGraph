import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from answer_writer import build_answer


def full_state(**overrides):
    state = {
        "case_id": "HHG-002",
        "case_data": {"TransactionID": "3478782", "customer_id": "C11891", "card_id": "C11891-K1"},
        "trigger_type": "risk_score",
        "flagged_txn": {"txn_id": "3478782", "ts": "2016-11-22 23:27:07", "amount": 292.36, "risk_score": 0.79},
        "related_txns": [
            {"txn_id": "3478101", "ts": "2016-11-22 23:10:00", "amount": 2.4},
            {"txn_id": "3478090", "ts": "2016-11-22 22:58:00", "amount": 1.1},
        ],
        "verdict": "fraud",
        "fraud_probability": 0.86,
        "pattern": "card_testing",
        "pattern_description": "",
        "affected_txn_ids": ["3478101", "3478090", "3478782"],
        "first_suspicious_txn_id": "3478001",
        "connected_card_ids": ["C01042-K1"],
        "connected_device_profiles": ["SAMSUNG SM-G892A | Android 7.0"],
        "exposure_usd": 295.86,
        "evidence": [
            {"claim": "Three small authorizations then a larger purchase",
             "source": "graph", "ref": "get_card_recent_window", "entity_ids": ["3478101"]},
            {"claim": "Customer denied the activity", "source": "customer",
             "ref": "evidence_request:1", "entity_ids": []},
        ],
        "evidence_requests": [{"type": "customer_validation", "asked_after_step": 5,
                               "assumed_response": "Simulated response recorded: denied. Assumed reply within 24h."}],
        "evidence_request_count": 1,
        "customer_response": "denied",
        "initial_actions": [
            {"action": "VERIFY_WITH_CUSTOMER", "route": "auto", "reason": "R1: weak signal verify first"},
        ],
        "final_actions": [
            {"action": "BLOCK_CARD", "route": "L1", "reason": "R2: customer denied"},
            {"action": "CREATE_CASE", "route": "auto", "reason": "R2"},
            {"action": "FILE_REPORT", "route": "L2", "reason": "R2: shared device links to another card"},
            {"action": "MONITOR_CONNECTED_CARDS", "route": "auto", "reason": "R6: shared device"},
        ],
        "sar_required": True,
        "sar_reason": "R2: confirmed unauthorized use",
        "sar_narrative": "Formal narrative standing on its own for the regulator.",
        "sar_subjects": ["C11891", "C11891-K1", "C01042-K1"],
        "similar_prior_cases": [{"case_id": "CC-0141", "verdict": "confirmed_fraud", "pattern": "card_testing",
                                 "similarity": 0.8, "summary": "similar"}],
        "rag_context": [{"ref": "policy:R5", "text": "...", "score": 0.9}],
        "summary": "Card testing confirmed.",
        "stop_reason": "Customer denial settled the verdict.",
        "written_to_graph": True,
        "graph_case_id": "HHG-002",
        "graph_nodes": [{"id": "txn-3478782", "type": "transaction", "label": "Txn 3478782", "data": {}}],
        "graph_edges": [{"source": "card-C11891-K1", "target": "txn-3478782", "label": "MADE"}],
        "tool_calls": 9,
        "tokens": 4200,
        "latency_s": 12.34,
        "jev_classification": {"engine": "heuristic", "pattern": "card_testing", "confidence": 0.88},
        "step": 9,
    }
    state.update(overrides)
    return state


def test_top_level_fields_present():
    answer = build_answer(full_state())
    for field in ("case_id", "case", "evidence_requests", "next_best_actions", "sar",
                  "stop_reason", "tool_calls", "tokens", "latency_s", "graph_data", "metadata"):
        assert field in answer, field


def test_case_fields_present():
    case = build_answer(full_state())["case"]
    for field in ("status", "verdict", "fraud_probability", "pattern", "pattern_description",
                  "affected_txn_ids", "first_suspicious_txn_id", "connected_card_ids",
                  "connected_device_profiles", "exposure_usd", "evidence", "similar_prior_cases",
                  "summary", "written_to_graph", "graph_case_id"):
        assert field in case, field


def test_sar_fields_present():
    sar = build_answer(full_state())["sar"]
    for field in ("file", "reason", "narrative", "subjects", "total_amount_usd", "activity_dates"):
        assert field in sar, field


def test_sar_consistent_with_final_actions():
    answer = build_answer(full_state())
    has_report = any(a["action"] == "FILE_REPORT" for a in answer["next_best_actions"]["final"])
    assert answer["sar"]["file"] == has_report == True
    assert answer["sar"]["narrative"]
    assert answer["sar"]["total_amount_usd"] == answer["case"]["exposure_usd"]
    assert answer["sar"]["activity_dates"] == ["2016-11-22", "2016-11-22"]


def test_sar_zeroed_when_not_filing():
    state = full_state(final_actions=[{"action": "CLOSE_NO_FRAUD", "route": "auto", "reason": "R3"}],
                       sar_required=False, sar_reason="R3a: no filing trigger met")
    answer = build_answer(state)
    sar = answer["sar"]
    assert sar["file"] is False
    assert sar["narrative"] == ""
    assert sar["subjects"] == []
    assert sar["total_amount_usd"] == 0
    assert sar["activity_dates"] == []


def test_sar_file_must_not_be_true_when_no_file_report_action():
    state = full_state(sar_required=True, sar_narrative="n",
                       final_actions=[{"action": "BLOCK_CARD", "route": "L1", "reason": "R2: denied"}])
    answer = build_answer(state)
    assert answer["sar"]["file"] is False
    assert answer["sar"]["narrative"] == ""


def test_status_mapping():
    assert build_answer(full_state())["case"]["status"] == "closed_fraud"
    legit = build_answer(full_state(verdict="legitimate",
                                    final_actions=[{"action": "CLOSE_NO_FRAUD", "route": "auto", "reason": "R3: confirmed"}]))
    assert legit["case"]["status"] == "closed_legitimate"
    uncertain_open = build_answer(full_state(
        verdict="uncertain",
        final_actions=[{"action": "VERIFY_WITH_CUSTOMER", "route": "auto", "reason": "R1: verify"}]))
    assert uncertain_open["case"]["status"] == "open"
    uncertain_escalated = build_answer(full_state(
        verdict="uncertain",
        final_actions=[{"action": "ESCALATE_TO_ANALYST", "route": "auto", "reason": "R8: uncertain and exposed"}]))
    assert uncertain_escalated["case"]["status"] == "escalated"


def test_legitimate_zeroing():
    state = full_state(verdict="legitimate", fraud_probability=0.05,
                       affected_txn_ids=[], exposure_usd=0.0,
                       final_actions=[{"action": "ALLOW_TRANSACTION", "route": "auto", "reason": "R1: consistent with history"},
                                      {"action": "CLOSE_NO_FRAUD", "route": "auto", "reason": "R3: no fraud evidence"}],
                       evidence_requests=[])
    case = build_answer(state)["case"]
    assert case["affected_txn_ids"] == []
    assert case["exposure_usd"] == 0
    assert build_answer(state)["sar"]["file"] is False


def test_no_requests_means_final_equals_initial():
    state = full_state(evidence_requests=[], final_actions=[
        {"action": "BLOCK_CARD", "route": "L1", "reason": "R2: something else"},
        {"action": "CREATE_CASE", "route": "auto", "reason": "R2"}])
    answer = build_answer(state)
    assert answer["next_best_actions"]["final"] == answer["next_best_actions"]["initial"]
    assert answer["next_best_actions"]["what_changed"] == "nothing"


def test_what_changed_describes_diff():
    answer = build_answer(full_state())
    changed = answer["next_best_actions"]["what_changed"]
    assert changed != "nothing"
    assert "BLOCK_CARD" in changed
    assert "customer_validation" in changed


def test_evidence_requests_passthrough():
    answer = build_answer(full_state())
    assert answer["evidence_requests"] == [{
        "type": "customer_validation", "asked_after_step": 5,
        "assumed_response": "Simulated response recorded: denied. Assumed reply within 24h."}]


def test_metadata_shape():
    meta = build_answer(full_state())["metadata"]
    assert isinstance(meta["duration_seconds"], (int, float))
    assert meta["jev_classification"]["pattern"] == "card_testing"


def test_similar_prior_cases_list_of_strings():
    answer = build_answer(full_state())
    assert answer["case"]["similar_prior_cases"] == ["CC-0141"]


def test_pattern_description_only_for_undocumented():
    assert build_answer(full_state())["case"]["pattern_description"] == ""
    doc = build_answer(full_state(pattern="undocumented", pattern_description="Coordinated abuse across cards."))
    assert doc["case"]["pattern_description"].startswith("Coordinated")