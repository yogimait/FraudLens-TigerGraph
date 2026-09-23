"""Strict validator for cases/*.json against the hackathon answer schema.

Usage:
  python validate_answers.py [--cases-dir cases] [--known-ids file]

Prints a per-file report and exits 1 on any violation.
"""
import argparse
import glob
import json
import os
import re
import sys

ACTIONS = {
    "ALLOW_TRANSACTION", "DECLINE_TRANSACTION", "MONITOR_CARD",
    "MONITOR_CONNECTED_CARDS", "WARN_CUSTOMER", "VERIFY_WITH_CUSTOMER",
    "STEP_UP_AUTH", "BLOCK_CARD", "BLOCK_ALL_CARDS", "GENERATE_REPORT",
    "CREATE_CASE", "FILE_REPORT", "ESCALATE_TO_ANALYST", "CLOSE_NO_FRAUD",
}
ROUTES = {"auto", "L1", "L2"}
STATUSES = {"open", "closed_fraud", "closed_legitimate", "escalated"}
VERDICTS = {"fraud", "legitimate", "uncertain"}
PATTERNS = {"card_testing", "card_not_present_fraud", "card_not_present_new_device",
            "out_of_region_use", "account_takeover", "undocumented", "none"}
SOURCES = {"graph", "document", "customer", "external"}
REQUEST_TYPES = {"customer_validation", "step_up_auth", "analyst_info"}
RULE_CITATION = re.compile(r"R\d")
DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _is_num(value) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _is_str_list(value) -> bool:
    return isinstance(value, list) and all(isinstance(x, str) for x in value)


def validate_answer(data, known_ids=None) -> list:
    errors: list = []
    add = errors.append

    if not isinstance(data, dict):
        return ["top level: not a JSON object"]

    for field in ("case_id", "case", "evidence_requests", "next_best_actions", "sar",
                  "stop_reason", "tool_calls", "tokens", "latency_s"):
        if field not in data:
            add(f"top level: missing '{field}'")
    if not isinstance(data.get("case_id"), str) or not data.get("case_id"):
        add("case_id: must be a non-empty string")
    if not isinstance(data.get("stop_reason"), str) or not data.get("stop_reason"):
        add("stop_reason: must be a non-empty string")
    if not isinstance(data.get("tool_calls"), int) or isinstance(data.get("tool_calls"), bool) or data["tool_calls"] < 0:
        add("tool_calls: must be a non-negative int")
    if not isinstance(data.get("tokens"), int) or isinstance(data.get("tokens"), bool) or data["tokens"] < 0:
        add("tokens: must be a non-negative int")
    if not _is_num(data.get("latency_s")) or data["latency_s"] < 0:
        add("latency_s: must be a non-negative number")

    case = data.get("case")
    if not isinstance(case, dict):
        add("case: must be an object")
        case = {}
    for field in ("status", "verdict", "fraud_probability", "pattern", "pattern_description",
                  "affected_txn_ids", "first_suspicious_txn_id", "connected_card_ids",
                  "connected_device_profiles", "exposure_usd", "evidence",
                  "similar_prior_cases", "summary", "written_to_graph", "graph_case_id"):
        if field not in case:
            add(f"case: missing '{field}'")
    if case.get("status") not in STATUSES:
        add(f"case.status: {case.get('status')!r} not in {sorted(STATUSES)}")
    if case.get("verdict") not in VERDICTS:
        add(f"case.verdict: {case.get('verdict')!r} not in {sorted(VERDICTS)}")
    if not _is_num(case.get("fraud_probability")) or not (0.0 <= case["fraud_probability"] <= 1.0):
        add("case.fraud_probability: must be a number in [0,1]")
    if case.get("pattern") not in PATTERNS:
        add(f"case.pattern: {case.get('pattern')!r} not in {sorted(PATTERNS)}")
    if case.get("pattern") == "undocumented" and not case.get("pattern_description"):
        add("case.pattern_description: required non-empty when pattern is 'undocumented'")
    if case.get("pattern") != "undocumented" and case.get("pattern_description"):
        add("case.pattern_description: must be \"\" unless pattern is 'undocumented'")
    for field in ("affected_txn_ids", "connected_card_ids", "connected_device_profiles", "similar_prior_cases"):
        if not _is_str_list(case.get(field)):
            add(f"case.{field}: must be a list of strings")
    if not isinstance(case.get("first_suspicious_txn_id"), str):
        add("case.first_suspicious_txn_id: must be a string")
    if not _is_num(case.get("exposure_usd")) or case["exposure_usd"] < 0:
        add("case.exposure_usd: must be a non-negative number")
    if not isinstance(case.get("written_to_graph"), bool):
        add("case.written_to_graph: must be a boolean")
    if not isinstance(case.get("graph_case_id"), str):
        add("case.graph_case_id: must be a string")
    if not isinstance(case.get("summary"), str) or not case.get("summary"):
        add("case.summary: must be a non-empty string")

    affected = case.get("affected_txn_ids") or []
    exposure = case.get("exposure_usd")
    verdict = case.get("verdict")
    if verdict == "legitimate":
        if affected:
            add("case.affected_txn_ids: must be empty for a legitimate verdict")
        if exposure not in (0, 0.0):
            add("case.exposure_usd: must be 0 for a legitimate verdict")
    if known_ids is not None:
        unknown = [t for t in affected if t not in known_ids]
        if unknown:
            add(f"case.affected_txn_ids: ids not in known set: {unknown}")

    evidence = case.get("evidence", [])
    if not isinstance(evidence, list):
        add("case.evidence: must be a list")
    else:
        for i, e in enumerate(evidence):
            if not isinstance(e, dict):
                add(f"case.evidence[{i}]: must be an object")
                continue
            for field in ("claim", "source", "ref", "entity_ids"):
                if field not in e:
                    add(f"case.evidence[{i}]: missing '{field}'")
            if not isinstance(e.get("claim"), str) or not e.get("claim"):
                add(f"case.evidence[{i}].claim: non-empty string required")
            if e.get("source") not in SOURCES:
                add(f"case.evidence[{i}].source: {e.get('source')!r} not in {sorted(SOURCES)}")
            if not isinstance(e.get("ref"), str):
                add(f"case.evidence[{i}].ref: string required")
            if not _is_str_list(e.get("entity_ids", None)):
                add(f"case.evidence[{i}].entity_ids: list of strings required")

    requests = data.get("evidence_requests")
    if not isinstance(requests, list):
        add("evidence_requests: must be a list")
        requests = []
    for i, r in enumerate(requests):
        if not isinstance(r, dict):
            add(f"evidence_requests[{i}]: must be an object")
            continue
        if r.get("type") not in REQUEST_TYPES:
            add(f"evidence_requests[{i}].type: {r.get('type')!r} not in {sorted(REQUEST_TYPES)}")
        if not isinstance(r.get("asked_after_step"), int) or isinstance(r.get("asked_after_step"), bool):
            add(f"evidence_requests[{i}].asked_after_step: int required")
        if not isinstance(r.get("assumed_response"), str) or not r.get("assumed_response"):
            add(f"evidence_requests[{i}].assumed_response: non-empty string required")

    sar = data.get("sar")
    if not isinstance(sar, dict):
        add("sar: must be an object")
        sar = {}
    for field in ("file", "reason", "narrative", "subjects", "total_amount_usd", "activity_dates"):
        if field not in sar:
            add(f"sar: missing '{field}'")
    files_report = sar.get("file")
    if not isinstance(files_report, bool):
        add("sar.file: must be a boolean")
        files_report = False
    if not isinstance(sar.get("reason"), str) or not sar.get("reason"):
        add("sar.reason: non-empty string required (cite the policy rule)")
    elif not RULE_CITATION.search(sar["reason"]):
        add("sar.reason: must cite a policy rule (R<digit>)")
    if not _is_str_list(sar.get("subjects", None)):
        add("sar.subjects: list of strings required")

    nba = data.get("next_best_actions")
    if not isinstance(nba, dict):
        add("next_best_actions: must be an object")
        nba = {}
    for field in ("initial", "final", "what_changed"):
        if field not in nba:
            add(f"next_best_actions: missing '{field}'")

    def check_actions(label, items):
        if not isinstance(items, list):
            add(f"next_best_actions.{label}: must be a list")
            return []
        for i, a in enumerate(items):
            if not isinstance(a, dict):
                add(f"next_best_actions.{label}[{i}]: must be an object")
                continue
            for field in ("action", "route", "reason"):
                if field not in a:
                    add(f"next_best_actions.{label}[{i}]: missing '{field}'")
            if a.get("action") not in ACTIONS:
                add(f"next_best_actions.{label}[{i}].action: {a.get('action')!r} is not a policy action")
            if a.get("route") not in ROUTES:
                add(f"next_best_actions.{label}[{i}].route: {a.get('route')!r} not in auto|L1|L2")
            if not isinstance(a.get("reason"), str) or not a.get("reason"):
                add(f"next_best_actions.{label}[{i}].reason: non-empty string required")
            elif not RULE_CITATION.search(a["reason"]):
                add(f"next_best_actions.{label}[{i}].reason: must cite a policy rule (R<digit>)")
        return [a.get("action") for a in items if isinstance(a, dict)]

    initial_names = check_actions("initial", nba.get("initial", []))
    final_names = check_actions("final", nba.get("final", []))
    if not nba.get("initial"):
        add("next_best_actions.initial: must be non-empty")
    if not isinstance(nba.get("what_changed"), str) or not nba.get("what_changed"):
        add("next_best_actions.what_changed: non-empty string required (or \"nothing\")")

    final_has_report = "FILE_REPORT" in final_names
    if files_report != final_has_report:
        add(f"sar.file={files_report} disagrees with FILE_REPORT in final actions={final_has_report}")

    if not files_report:
        if sar.get("narrative"):
            add("sar.narrative: must be \"\" when sar.file is false")
        if sar.get("subjects"):
            add("sar.subjects: must be [] when sar.file is false")
        if sar.get("total_amount_usd") not in (0, 0.0):
            add("sar.total_amount_usd: must be 0 when sar.file is false")
        if sar.get("activity_dates") not in ([], None):
            add("sar.activity_dates: must be [] when sar.file is false")
    else:
        if not sar.get("narrative"):
            add("sar.narrative: required when sar.file is true")
        if not sar.get("subjects"):
            add("sar.subjects: must name at least one subject when sar.file is true")
        if not _is_num(sar.get("total_amount_usd")) or sar.get("total_amount_usd", 0) <= 0:
            add("sar.total_amount_usd: positive number required when sar.file is true")
        dates = sar.get("activity_dates")
        if not isinstance(dates, list) or len(dates) != 2 or not all(isinstance(d, str) and DATE.match(d) for d in dates):
            add("sar.activity_dates: must be [first, last] as YYYY-MM-DD when sar.file is true")
        if verdict == "legitimate":
            add("sar.file must be false for a legitimate verdict")
        if exposure is not None and _is_num(exposure) and exposure > 0 and files_report and \
                _is_num(sar.get("total_amount_usd")) and abs(float(sar["total_amount_usd"]) - float(exposure)) > 0.01:
            add("sar.total_amount_usd should match case.exposure_usd")

    return errors


def load_known_ids(path: str) -> set:
    with open(path, "r", encoding="utf-8") as f:
        return {line.strip() for line in f if line.strip()}


def validate_dir(cases_dir: str, known_ids=None):
    files = sorted(glob.glob(os.path.join(cases_dir, "*.json")))
    total_errors = 0
    for path in files:
        name = os.path.basename(path)
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, ValueError) as e:
            print(f"{name}: INVALID JSON ({e})")
            total_errors += 1
            continue
        errors = validate_answer(data, known_ids)
        if errors:
            print(f"{name}: {len(errors)} violation(s)")
            for e in errors:
                print(f"  - {e}")
            total_errors += len(errors)
        else:
            print(f"{name}: OK")
    print(f"\n{len(files)} file(s) checked, {total_errors} violation(s)")
    return total_errors


def main():
    parser = argparse.ArgumentParser(description="Validate cases/*.json against the answer schema")
    parser.add_argument("--cases-dir", default=None)
    parser.add_argument("--known-ids", default=None, help="file with one allowed txn id per line")
    args = parser.parse_args()

    root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    cases_dir = args.cases_dir or os.path.join(root, "cases")
    known = load_known_ids(args.known_ids) if args.known_ids else None
    errors = validate_dir(cases_dir, known)
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()