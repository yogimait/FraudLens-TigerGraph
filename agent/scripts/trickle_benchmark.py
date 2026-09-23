"""Trickle-run benchmark cases through Groq rate-limit windows."""
import os
import sys
import time

import requests

BACKEND = os.environ.get("BACKEND_URL", "http://localhost:3001")
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def answer_meta(case_id):
    path = os.path.join(ROOT, "cases", f"{case_id}.json")
    try:
        import json
        with open(path, encoding="utf-8") as fh:
            return json.load(fh).get("metadata", {})
    except (OSError, json.JSONDecodeError):
        return {}


def main():
    case_ids = [f"HHG-{i:03d}" for i in range(1, 21)]
    done = set()
    attempts = 0
    while len(done) < len(case_ids) and attempts < 60:
        attempts += 1
        progress = False
        for case_id in case_ids:
            if case_id in done:
                continue
            row = None
            import csv
            with open(os.path.join(ROOT, "Initial-docs", "dataset", "case_pack.csv"), encoding="utf-8") as f:
                for r in csv.DictReader(f):
                    if r["case_id"] == case_id:
                        row = r
                        break
            if row is None:
                continue
            try:
                resp = requests.post(
                    BACKEND.rstrip("/") + f"/cases/{case_id}/trigger",
                    json={"transaction_id": row["flagged_txn_id"], "trigger_type": row["trigger_type"]},
                    timeout=600)
                ok_http = resp.status_code in (200, 201)
                llm_ok = answer_meta(case_id).get("llm_ok")
                ts = time.strftime("%H:%M:%S")
                if ok_http and llm_ok is True:
                    done.add(case_id)
                    print(f"[{ts}] {case_id}: OK ({len(done)}/{len(case_ids)})", flush=True)
                elif ok_http and llm_ok is False:
                    print(f"[{ts}] {case_id}: degraded, sleeping 600s", flush=True)
                    time.sleep(600)
                    break
                else:
                    print(f"[{ts}] {case_id}: HTTP {resp.status_code}, sleeping 300s", flush=True)
                    time.sleep(300)
                    break
            except Exception as e:
                print(f"[{ts}] {case_id}: {type(e).__name__}: {e}", flush=True)
                time.sleep(300)
                break
        time.sleep(2)
    print(f"Trickle done: {len(done)}/20 complete", flush=True)


if __name__ == "__main__":
    sys.exit(main())
