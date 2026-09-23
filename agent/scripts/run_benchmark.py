"""Benchmark runner for the 20 HHG cases.

Default mode: trigger each case via the NestJS backend, then validate cases/.
--dry-run: run the LangGraph in-process against a CSV-backed mocked TigerGraph
client with a mocked LLM, write cases/*.json and validate — fully offline.
"""
import argparse
import csv
import json
import os
import sys
import time
from datetime import datetime, timedelta

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
AGENT_DIR = os.path.dirname(SCRIPT_DIR)
ROOT_DIR = os.path.dirname(os.path.dirname(SCRIPT_DIR))
sys.path.insert(0, AGENT_DIR)
sys.path.insert(0, SCRIPT_DIR)

CASE_PACK_PATH = os.path.join(ROOT_DIR, "Initial-docs", "dataset", "case_pack.csv")
TRANSACTIONS_PATH = os.path.join(ROOT_DIR, "Initial-docs", "dataset", "transactions.csv")
IDENTITY_PATH = os.path.join(ROOT_DIR, "Initial-docs", "dataset", "identity.csv")
DRYRUN_CACHE = os.path.join(AGENT_DIR, "tests", "fixtures", "dryrun_cases.json")

BACKEND_URL = os.environ.get("BACKEND_URL", "http://localhost:3001")
CASE_DELAY_S = 5


def load_case_pack(only=None):
    rows = []
    with open(os.path.join(ROOT_DIR, "Initial-docs", "dataset", "case_pack.csv"), "r", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    if only:
        wanted = {x.strip() for x in only.split(",") if x.strip()}
        rows = [r for r in rows if r["case_id"] in wanted]
    return rows


def run_http_mode(case_rows):
    import requests
    url = BACKEND_URL.rstrip("/") + "/cases/{}/trigger"
    ok = failed = degraded = 0
    for i, case in enumerate(case_rows):
        case_id = case["case_id"]
        payload = {"transaction_id": case["flagged_txn_id"], "trigger_type": case["trigger_type"]}
        print(f"[{i + 1}/{len(case_rows)}] POST {case_id} (txn {payload['transaction_id']})")
        try:
            resp = requests.post(url.format(case_id), json=payload, timeout=600)
            if resp.status_code in (200, 201):
                ok += 1
                answer_path = os.path.join(ROOT_DIR, "cases", f"{case_id}.json")
                llm_ok = None
                if os.path.exists(answer_path):
                    try:
                        with open(answer_path, encoding="utf-8") as fh:
                            llm_ok = json.load(fh).get("metadata", {}).get("llm_ok")
                    except (json.JSONDecodeError, OSError):
                        pass
                if llm_ok is False:
                    degraded += 1
                    print("  -> OK but LLM DEGRADED (rate limit?) — aborting to avoid overwriting good answers")
                    break
                print(f"  -> OK")
            else:
                failed += 1
                print(f"  -> HTTP {resp.status_code}: {resp.text[:300]}")
        except Exception as e:
            failed += 1
            print(f"  -> ERROR: {e}")
        if i < len(case_rows) - 1:
            time.sleep(CASE_DELAY_S)
    print(f"\nHTTP mode done: {ok} ok, {failed} failed, degraded stop: {degraded}")
    return failed == 0 and degraded == 0


def _norm_ts(transaction_dt: int) -> str:
    return (datetime(2026, 1, 1) + timedelta(seconds=int(transaction_dt or 0))).strftime("%Y-%m-%d %H:%M:%S")


def build_dryrun_data(case_rows) -> dict:
    """Scan the dataset CSVs once and cache per-case graph facts for offline runs."""
    if os.path.exists(DRYRUN_CACHE):
        with open(DRYRUN_CACHE, "r", encoding="utf-8") as f:
            cached = json.load(f)
        if cached.get("built_at"):
            return cached

    flagged_ids = {str(c["flagged_txn_id"]) for c in case_rows}
    flagged_rows = {}
    print(f"Scanning {os.path.basename(TRANSACTIONS_PATH)} for {len(flagged_ids)} flagged transactions...")
    with open(TRANSACTIONS_PATH, "r", encoding="utf-8", newline="") as f:
        reader = csv.reader(f)
        tx_header = next(reader)
        tx_col = {name: i for i, name in enumerate(tx_header)}
        for row in reader:
            if row[0] in flagged_ids:
                flagged_rows[row[0]] = {"card1": row[tx_col["card1"]],
                                        "customer_id": row[tx_col["customer_id"]], "row": row}
                if len(flagged_rows) == len(flagged_ids):
                    break

    wanted_cards = {info["card1"] for info in flagged_rows.values() if info["card1"]}
    card_txns = {c: [] for c in wanted_cards}
    print(f"Scanning again for card activity of {len(wanted_cards)} card(s)...")
    with open(TRANSACTIONS_PATH, "r", encoding="utf-8", newline="") as f:
        reader = csv.reader(f)
        next(reader)
        for row in reader:
            card = row[tx_col["card1"]]
            bucket = card_txns.get(card)
            if bucket is not None and len(bucket) < 40:
                bucket.append(row)

    device_rows = {}
    if os.path.exists(IDENTITY_PATH):
        print("Scanning identity.csv for flagged devices...")
        with open(IDENTITY_PATH, "r", encoding="utf-8", newline="") as f:
            reader = csv.reader(f)
            id_col = {name: i for i, name in enumerate(next(reader))}
            for row in reader:
                if row[id_col["TransactionID"]] in flagged_ids:
                    device_rows[row[id_col["TransactionID"]]] = {
                        "device_type": row[id_col["DeviceType"]] or "unknown",
                        "device_info": row[id_col["DeviceInfo"]] or "unknown",
                        "id_15": row[id_col["id_15"]] or "unknown",
                        "id_23": row[id_col["id_23"]] or "unknown",
                    }

    def row_attrs(row):
        try:
            dt = int(float(row[tx_col["TransactionDT"]] or 0))
        except ValueError:
            dt = 0
        try:
            amount = float(row[tx_col["TransactionAmt"]] or 0)
        except ValueError:
            amount = 0.0
        try:
            risk = float(row[tx_col["risk_score"]] or 0)
        except ValueError:
            risk = 0.0
        return {
            "txn_id": row[tx_col["TransactionID"]],
            "ts": _norm_ts(dt),
            "amount": amount,
            "product_cd": row[tx_col["ProductCD"]] or "unknown",
            "channel": row[tx_col["channel"]] or "unknown",
            "risk_score": risk,
            "dist1": float(row[tx_col["dist1"]] or 0),
            "addr1": float(row[tx_col["addr1"]] or 0),
            "addr2": float(row[tx_col["addr2"]] or 0),
        }

    data = {"cases": {}, "built_at": datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")}
    for case in case_rows:
        txn_id = str(case["flagged_txn_id"])
        info = flagged_rows.get(txn_id)
        if not info:
            data["cases"][case["case_id"]] = {}
            continue
        data["cases"][case["case_id"]] = {
            "flagged_txn": row_attrs(info["row"]),
            "card1": info["card1"],
            "card_id": case["card_id"],
            "customer_id": case["customer_id"],
            "device": device_rows.get(txn_id),
            "card_txns": [row_attrs(r) for r in card_txns.get(info["card1"], [])],
        }

    os.makedirs(os.path.dirname(DRYRUN_CACHE), exist_ok=True)
    with open(DRYRUN_CACHE, "w", encoding="utf-8") as f:
        json.dump(data, f)
    print(f"Cached dry-run data to {DRYRUN_CACHE}")
    return data


class DryRunTigerGraph:
    """Offline stand-in for TigerGraphMCP serving real CSV-derived rows."""

    def __init__(self, data: dict, case_id: str):
        entry = data["cases"].get(case_id, {})
        self.txn = entry.get("flagged_txn", {})
        self.card1 = str(entry.get("card1", ""))
        self.card_id = entry.get("card_id", "")
        self.customer_id = entry.get("customer_id", "")
        self.device = entry.get("device", {})
        self.card_txns = entry.get("card_txns", [])
        self.use_mcp = False
        self.calls = 0

    @property
    def conn(self):
        raise RuntimeError("dry-run mode never opens a real connection")

    def run_installed_query(self, name: str, params: dict):
        self.calls += 1
        if name == "get_transaction_device" and self.device_row():
            return [{"Devices": [self.device_row()]}]
        if name == "get_card_transactions":
            return [{"Txns": [self._vertex(t) for t in self.card_txns]}]
        if name == "get_card_recent_window":
            anchor = str(params.get("anchor_ts", ""))
            hours = int(params.get("hours", 2))
            start = datetime.strptime(anchor, "%Y-%m-%d %H:%M:%S") - timedelta(hours=hours)
            window = [t for t in self.card_txns if start.strftime("%Y-%m-%d %H:%M:%S") <= t["ts"] <= anchor]
            return [{"Txns": [self._vertex(t) for t in window]}]
        if name == "get_shared_device_cards":
            return [{"Cards": []}]
        if name == "get_customer_cards" and self.card_id:
            return [{"Cards": [{"v_id": self.card_id, "attributes": {}}]}]
        return []

    def run_interpreted_query(self, gsql: str, params: dict = None):
        self.calls += 1
        params = params or {}
        t_id = str(params.get("t_id", ""))
        if t_id:
            if t_id == str(self.txn.get("txn_id", "")):
                return [{"T": [self._vertex(self.txn)]}]
            match = [t for t in self.card_txns if str(t["txn_id"]) == t_id]
            return [{"T": [self._vertex(match[0])]}] if match else []
        c_id = str(params.get("c_id", ""))
        if c_id and "Card:c -(MADE" in gsql:
            return [{"C": [{"v_id": self.card_id, "attributes": {}}]}] if self.card_id else []
        return []

    def device_row(self):
        if not self.device:
            return None
        return {
            "v_id": str(self.txn.get("txn_id", "")),
            "attributes": dict(self.device),
        }

    def _vertex(self, attrs: dict):
        return {"v_id": str(attrs.get("txn_id", "")), "attributes": dict(attrs)}

    def close(self):
        pass


def run_dry_mode(case_rows) -> bool:
    os.environ.pop("JEV_API_KEY", None)
    os.environ.pop("GROQ_API_KEY", None)

    import jev_client
    jev_client._jev_dead = True
    jev_client._client_failed = True

    import graph as graph_mod
    import llm as llm_mod
    import memory as memory_mod
    from jev_client import _heuristic_pattern
    import answer_writer
    import validate_answers

    data = build_dryrun_data(case_rows)

    def stub_synth(state):
        txn = state.get("flagged_txn") or {}
        related = state.get("related_txns") or []
        pattern, conf = _heuristic_pattern(txn, related)
        smalls = [t for t in related if abs(float(t.get("amount", 0) or 0)) < 5]
        flagged_id = str(txn.get("txn_id", ""))
        if len(smalls) >= 3:
            pattern, conf = "card_testing", 0.88
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
            affected.extend(str(t["txn_id"]) for t in smalls if str(t["txn_id"]) != flagged_id)
        drivers = [f"Jev heuristic pattern {pattern} at confidence {conf}",
                   f"Model risk score {risk} used as prior only"]
        if customer:
            drivers.append(f"Customer response: {customer}")
        return {
            "fraud_probability": fp,
            "pattern": pattern,
            "pattern_description": "Mocked dry-run synthesis; regenerate via backend for graded output." if pattern == "undocumented" else "",
            "verdict": verdict,
            "affected_txn_ids": affected,
            "first_suspicious_txn_id": affected[0] if affected else "",
            "confidence_drivers": drivers,
            "tokens": 0,
        }

    def stub_outputs(state):
        verdict = state.get("verdict", "uncertain")
        return {
            "summary": (f"Dry-run investigation for {state.get('case_id')}: verdict {verdict} at "
                        f"probability {state.get('fraud_probability')}, pattern {state.get('pattern')}. "
                        f"{len(state.get('evidence') or [])} evidence items gathered; "
                        f"{len(state.get('evidence_requests') or [])} evidence request(s) simulated."),
            "sar_narrative": (f"Dry-run placeholder SAR for {state.get('case_id')}. "
                              f"Flagged transaction {state.get('first_suspicious_txn_id', '')} with total "
                              f"${state.get('exposure_usd', 0)} across {len(state.get('affected_txn_ids') or [])} "
                              f"transactions.") if state.get("sar_required") else "",
            "stop_reason": state.get("stop_reason", "Dry run complete."),
            "tokens": 0,
        }

    llm_mod.synthesize_evidence = stub_synth
    llm_mod.generate_outputs = stub_outputs
    memory_mod.persist_investigation_case = lambda conn, state: ""

    failures = 0
    for case in case_rows:
        case_id = case["case_id"]
        graph_mod.tg_client = DryRunTigerGraph(data, case_id)
        start = time.time()
        state = graph_mod.run_investigation(case_id, case["flagged_txn_id"], case["trigger_type"])
        state = dict(state)
        state["latency_s"] = time.time() - start
        answer = answer_writer.build_answer(state)
        path = answer_writer.write_answer(answer)
        errors = validate_answers.validate_answer(answer)
        status = "OK" if not errors else f"{len(errors)} violation(s)"
        print(f"{case_id}: verdict={answer['case']['verdict']} "
              f"fp={answer['case']['fraud_probability']} sar={answer['sar']['file']} "
              f"tools={answer['tool_calls']} validation={status}")
        for e in errors:
            print(f"  - {e}")
        failures += len(errors)
    return failures == 0


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Run the 20-case benchmark")
    parser.add_argument("--dry-run", action="store_true", help="run in-process offline with mocked TG/LLM")
    parser.add_argument("--no-validate", action="store_true")
    parser.add_argument("--case", default="", help="comma-separated case_id subset, e.g. HHG-001,HHG-002")
    args = parser.parse_args()

    case_rows = load_case_pack(args.case)
    print(f"Loaded {len(case_rows)} cases from case_pack.csv")

    if args.dry_run:
        ok = run_dry_mode(case_rows)
    else:
        ok = run_http_mode(case_rows)

    if not args.no_validate:
        import validate_answers
        print("\n--- VALIDATING cases/ ---")
        exit_errors = validate_answers.validate_dir(os.path.join(ROOT_DIR, "cases"))
        if ok and exit_errors == 0:
            print("Benchmark complete: all answers valid.")
            sys.exit(0)
        print("Benchmark finished with validation errors.")
        sys.exit(1)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
