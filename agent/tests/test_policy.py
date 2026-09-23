import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from policy import apply_policy, _route, _finalize, ACTIONS


def base_state(**overrides):
    state = {
        "verdict": "uncertain",
        "fraud_probability": 0.5,
        "pattern": "none",
        "exposure_usd": 100.0,
        "trigger_type": "risk_score",
        "customer_response": "",
        "evidence": [],
        "evidence_requests": [],
        "evidence_request_count": 0,
        "connected_card_ids": [],
        "connected_device_profiles": [],
        "related_txns": [],
        "jev_classification": {"coordination": 0.0},
        "initial_actions": [],
    }
    state.update(overrides)
    return state


def actions(state):
    return [a["action"] for a in apply_policy(state)["final_actions"]]


def by_action(state):
    return {a["action"]: a for a in apply_policy(state)["final_actions"]}


# --- routes ---
def test_route_table():
    assert _route("ALLOW_TRANSACTION", 0) == "auto"
    assert _route("VERIFY_WITH_CUSTOMER", 0) == "auto"
    assert _route("STEP_UP_AUTH", 0) == "auto"
    assert _route("MONITOR_CONNECTED_CARDS", 0) == "auto"
    assert _route("CREATE_CASE", 0) == "auto"
    assert _route("ESCALATE_TO_ANALYST", 0) == "auto"
    assert _route("CLOSE_NO_FRAUD", 0) == "auto"
    assert _route("GENERATE_REPORT", 0) == "auto"
    assert _route("MONITOR_CARD", 0) == "auto"
    assert _route("WARN_CUSTOMER", 0) == "auto"
    assert _route("DECLINE_TRANSACTION", 0) == "L1"
    assert _route("DECLINE_TRANSACTION", 99999) == "L1"
    assert _route("BLOCK_CARD", 2500) == "L1"
    assert _route("BLOCK_CARD", 2500.01) == "L2"
    assert _route("BLOCK_ALL_CARDS", 0) == "L2"
    assert _route("FILE_REPORT", 0) == "L2"


def test_every_action_object_shape():
    state = base_state(fraud_probability=0.9, verdict="fraud", pattern="card_not_present_fraud", exposure_usd=3000)
    for a in apply_policy(state)["final_actions"]:
        assert set(a.keys()) == {"action", "route", "reason"}
        assert a["action"] in ACTIONS
        assert a["route"] in ("auto", "L1", "L2")
        assert a["reason"]


# --- R1 verify before block ---
def test_r1_single_signal_low_probability_verifies_not_blocks():
    state = base_state(verdict="uncertain", fraud_probability=0.45,
                       evidence=[{"claim": "risk score 0.45", "source": "graph", "ref": "q", "entity_ids": ["1"]}])
    result = apply_policy(state)["final_actions"]
    names = [a["action"] for a in result]
    assert "VERIFY_WITH_CUSTOMER" in names
    assert "BLOCK_CARD" not in names
    assert "CREATE_CASE" in names  # fp >= 0.30 -> case required (section 3a)


def test_r1_high_probability_two_signals_can_block():
    state = base_state(verdict="fraud", fraud_probability=0.9,
                       evidence=[{"claim": "a", "source": "graph", "ref": "q1", "entity_ids": []},
                                 {"claim": "b", "source": "graph", "ref": "q2", "entity_ids": []}])
    names = actions(state)
    assert "BLOCK_CARD" in names
    assert "VERIFY_WITH_CUSTOMER" not in names


def test_r1_two_signals_low_probability_still_verifies():
    state = base_state(verdict="uncertain", fraud_probability=0.55,
                       evidence=[{"claim": "a", "source": "graph", "ref": "q1", "entity_ids": []},
                                 {"claim": "b", "source": "graph", "ref": "q2", "entity_ids": []}])
    assert "VERIFY_WITH_CUSTOMER" in actions(state)


# --- R2 customer denies ---
def test_r2_denial_blocks_and_creates_case():
    state = base_state(verdict="fraud", fraud_probability=0.8, customer_response="denied",
                       evidence=[{"claim": "risk", "source": "graph", "ref": "q", "entity_ids": []},
                                 {"claim": "customer denied", "source": "customer", "ref": "er:1", "entity_ids": []}],
                       exposure_usd=500.0)
    routed = by_action(state)
    assert "BLOCK_CARD" in routed
    assert routed["BLOCK_CARD"]["route"] == "L1"  # exposure 500 <= 2500
    assert "CREATE_CASE" in routed
    assert "FILE_REPORT" not in routed  # exposure <= 1000, no shared device


def test_r2_denial_files_report_over_1000():
    state = base_state(verdict="fraud", fraud_probability=0.8, customer_response="denied",
                       exposure_usd=1500.0,
                       evidence=[{"claim": "risk", "source": "graph", "ref": "q", "entity_ids": []},
                                 {"claim": "customer denied", "source": "customer", "ref": "er:1", "entity_ids": []}])
    routed = by_action(state)
    assert routed["FILE_REPORT"]["route"] == "L2"


def test_r2_denial_files_report_on_shared_device_even_low_exposure():
    state = base_state(verdict="fraud", fraud_probability=0.8, customer_response="denied",
                       exposure_usd=200.0, connected_device_profiles=["SAMSUNG | Android"],
                       evidence=[{"claim": "shared device", "source": "graph", "ref": "q", "entity_ids": []},
                                 {"claim": "customer denied", "source": "customer", "ref": "er:1", "entity_ids": []}])
    assert "FILE_REPORT" in actions(state)
    assert "MONITOR_CONNECTED_CARDS" in actions(state)


def test_block_card_route_depends_on_exposure():
    low = base_state(verdict="fraud", fraud_probability=0.9, customer_response="denied", exposure_usd=2000.0,
                     evidence=[{"claim": "a", "source": "graph", "ref": "q", "entity_ids": []},
                               {"claim": "b", "source": "customer", "ref": "e", "entity_ids": []}])
    high = dict(low, exposure_usd=3000.0)
    assert by_action(low)["BLOCK_CARD"]["route"] == "L1"
    assert by_action(high)["BLOCK_CARD"]["route"] == "L2"


# --- R3 customer confirms ---
def test_r3_confirmation_closes_no_fraud():
    state = base_state(verdict="fraud", fraud_probability=0.9, customer_response="confirmed",
                       exposure_usd=2000.0, trigger_type="customer_report",
                       evidence=[{"claim": "a", "source": "graph", "ref": "q", "entity_ids": []},
                                 {"claim": "customer confirmed", "source": "customer", "ref": "er:1", "entity_ids": []}])
    routed = by_action(state)
    assert "CLOSE_NO_FRAUD" in routed
    assert "BLOCK_CARD" not in routed
    assert "DECLINE_TRANSACTION" not in routed
    assert not apply_policy(state)["sar_required"]


# --- R4 no reply ---
def test_r4_no_reply_monitor_and_decline_no_escalation_under_500():
    state = base_state(verdict="uncertain", fraud_probability=0.4, customer_response="no_reply",
                       exposure_usd=400.0,
                       evidence=[{"claim": "a", "source": "graph", "ref": "q", "entity_ids": []},
                                 {"claim": "b", "source": "graph", "ref": "q2", "entity_ids": []}])
    routed = by_action(state)
    assert "MONITOR_CARD" in routed
    assert "DECLINE_TRANSACTION" in routed
    assert "ESCALATE_TO_ANALYST" not in routed


def test_r4_no_reply_escalates_over_500():
    state = base_state(verdict="uncertain", fraud_probability=0.5, customer_response="no_reply",
                       exposure_usd=600.0,
                       evidence=[{"claim": "a", "source": "graph", "ref": "q", "entity_ids": []},
                                 {"claim": "b", "source": "graph", "ref": "q2", "entity_ids": []}])
    assert "ESCALATE_TO_ANALYST" in actions(state)


# --- R5 card testing ---
def test_r5_testing_decline_and_step_up():
    state = base_state(verdict="fraud", fraud_probability=0.85, pattern="card_testing",
                       exposure_usd=10.0,
                       related_txns=[{"amount": 2.4}, {"amount": 1.1}, {"amount": 0.95}])
    routed = by_action(state)
    assert "DECLINE_TRANSACTION" in routed
    assert "STEP_UP_AUTH" in routed
    assert "BLOCK_CARD" not in routed


def test_r5_blocks_when_over_100_cleared():
    state = base_state(verdict="fraud", fraud_probability=0.85, pattern="card_testing",
                       exposure_usd=120.0,
                       related_txns=[{"amount": 2.4}, {"amount": 1.1}, {"amount": 120.0}])
    assert "BLOCK_CARD" in actions(state)


# --- R6 shared origin ---
def test_r6_shared_origin_case_report_monitor():
    state = base_state(verdict="fraud", fraud_probability=0.75, connected_device_profiles=["device-x"],
                       connected_card_ids=["C01042-K1"], exposure_usd=100.0)
    routed = by_action(state)
    assert "CREATE_CASE" in routed
    assert "FILE_REPORT" in routed
    assert "MONITOR_CONNECTED_CARDS" in routed


# --- R7 disputed but legitimate ---
def test_r7_disputed_legitimate_no_block():
    state = base_state(verdict="legitimate", fraud_probability=0.1, trigger_type="customer_report",
                       exposure_usd=482.0)
    routed = by_action(state)
    assert "CREATE_CASE" in routed
    assert "VERIFY_WITH_CUSTOMER" in routed
    assert "WARN_CUSTOMER" in routed
    assert "BLOCK_CARD" not in routed
    assert "DECLINE_TRANSACTION" not in routed
    assert not apply_policy(state)["sar_required"]


# --- R8 uncertain escalation ---
def test_r8_uncertain_escalates_over_500():
    state = base_state(verdict="uncertain", fraud_probability=0.5, exposure_usd=600.0,
                       evidence=[{"claim": "a", "source": "graph", "ref": "q", "entity_ids": []},
                                 {"claim": "b", "source": "graph", "ref": "q2", "entity_ids": []}])
    assert "ESCALATE_TO_ANALYST" in actions(state)


def test_r8_no_escalation_small_exposure_settled_evidence():
    state = base_state(verdict="uncertain", fraud_probability=0.4, exposure_usd=100.0,
                       evidence=[{"claim": "a", "source": "graph", "ref": "q", "entity_ids": []},
                                 {"claim": "b", "source": "graph", "ref": "q2", "entity_ids": []}])
    assert "ESCALATE_TO_ANALYST" not in actions(state)


def test_r8_conflicting_evidence_escalates_even_small_exposure():
    state = base_state(verdict="uncertain", fraud_probability=0.6, customer_response="no_reply",
                       exposure_usd=100.0,
                       evidence=[{"claim": "a", "source": "graph", "ref": "q", "entity_ids": []},
                                 {"claim": "b", "source": "graph", "ref": "q2", "entity_ids": []}])
    assert "ESCALATE_TO_ANALYST" in actions(state)


# --- R9 undocumented ---
def test_r9_undocumented_coordinated():
    state = base_state(verdict="fraud", fraud_probability=0.8, pattern="undocumented",
                       exposure_usd=50.0, jev_classification={"coordination": 0.8})
    routed = by_action(state)
    assert "CREATE_CASE" in routed
    assert "FILE_REPORT" in routed
    assert "ESCALATE_TO_ANALYST" in routed


def test_r9_not_fired_without_coordination():
    state = base_state(verdict="uncertain", fraud_probability=0.5, pattern="undocumented",
                       exposure_usd=50.0, jev_classification={"coordination": 0.1})
    assert "FILE_REPORT" not in actions(state)


# --- R10 guard ---
def test_r10_block_all_cards_never_recommended_without_two_confirmed_cards():
    state = base_state(confirmed_compromised_card_count=1)
    result = _finalize(state, {"BLOCK_ALL_CARDS": ("R2: test", 2)})
    assert result == []

    state2 = base_state(confirmed_compromised_card_count=2)
    result2 = _finalize(state2, {"BLOCK_ALL_CARDS": ("R10: two confirmed compromised cards", 2)})
    assert result2[0]["action"] == "BLOCK_ALL_CARDS"
    assert result2[0]["route"] == "L2"


# --- section 3a triggers ---
def test_case_created_at_probability_threshold():
    state = base_state(verdict="uncertain", fraud_probability=0.35, exposure_usd=50.0)
    assert "CREATE_CASE" in actions(state)


def test_case_not_created_below_threshold_without_other_triggers():
    state = base_state(verdict="legitimate", fraud_probability=0.1, exposure_usd=0.0)
    names = actions(state)
    assert "CREATE_CASE" not in names
    assert "CLOSE_NO_FRAUD" in names


def test_case_created_on_evidence_request():
    state = base_state(verdict="uncertain", fraud_probability=0.2, evidence_request_count=1,
                       evidence_requests=[{"type": "customer_validation"}])
    assert "CREATE_CASE" in actions(state)


def test_case_created_on_customer_dispute_even_legitimate():
    state = base_state(verdict="legitimate", fraud_probability=0.05, trigger_type="customer_report")
    assert "CREATE_CASE" in actions(state)


# --- legitimate verdict ---
def test_legitimate_risk_score_case_allows_and_closes():
    state = base_state(verdict="legitimate", fraud_probability=0.1, trigger_type="risk_score")
    routed = by_action(state)
    assert routed["ALLOW_TRANSACTION"]["route"] == "auto"
    assert "CLOSE_NO_FRAUD" in routed
    assert "BLOCK_CARD" not in routed
    assert not apply_policy(state)["sar_required"]


# --- ordering and dedup ---
def test_actions_ordered_by_execution_order():
    state = base_state(verdict="fraud", fraud_probability=0.9, customer_response="denied",
                       exposure_usd=1500.0, connected_device_profiles=["device-x"],
                       evidence=[{"claim": "a", "source": "graph", "ref": "q", "entity_ids": []},
                                 {"claim": "customer denied", "source": "customer", "ref": "er:1", "entity_ids": []}])
    names = actions(state)
    order = ["ALLOW_TRANSACTION", "VERIFY_WITH_CUSTOMER", "STEP_UP_AUTH", "WARN_CUSTOMER",
             "MONITOR_CARD", "MONITOR_CONNECTED_CARDS", "DECLINE_TRANSACTION", "BLOCK_CARD",
             "BLOCK_ALL_CARDS", "CREATE_CASE", "GENERATE_REPORT", "FILE_REPORT",
             "ESCALATE_TO_ANALYST", "CLOSE_NO_FRAUD"]
    idx = [order.index(n) for n in names]
    assert idx == sorted(idx)


def test_dedup_keeps_highest_severity_route():
    state = base_state(verdict="fraud", fraud_probability=0.9, customer_response="denied",
                       exposure_usd=3000.0, connected_device_profiles=["device-x"],
                       evidence=[{"claim": "a", "source": "graph", "ref": "q", "entity_ids": []},
                                 {"claim": "customer denied", "source": "customer", "ref": "er:1", "entity_ids": []}])
    routed = by_action(state)
    assert routed["BLOCK_CARD"]["route"] == "L2"  # exposure 3000 wins over default L1


def test_sar_required_matches_file_report():
    filing = base_state(verdict="fraud", fraud_probability=0.9, exposure_usd=2000.0)
    assert apply_policy(filing)["sar_required"] is True
    not_filing = base_state(verdict="uncertain", fraud_probability=0.4, exposure_usd=100.0)
    assert apply_policy(not_filing)["sar_required"] is False