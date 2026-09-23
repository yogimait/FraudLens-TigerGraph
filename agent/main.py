import argparse
import sys
import time

from dotenv import load_dotenv

load_dotenv()

from answer_writer import build_answer, write_answer
from graph import run_investigation


def main():
    parser = argparse.ArgumentParser(description="Run one fraud investigation and write the answer file.")
    parser.add_argument("case_id")
    parser.add_argument("transaction_id")
    parser.add_argument("trigger_type", nargs="?", default="risk_score")
    args = parser.parse_args()

    print(f"Investigating {args.case_id} (txn {args.transaction_id}, trigger {args.trigger_type})")
    start = time.time()
    state = run_investigation(args.case_id, args.transaction_id, args.trigger_type)
    state = dict(state)
    state["latency_s"] = time.time() - start

    answer = build_answer(state)
    path = write_answer(answer)

    print(f"Verdict: {answer['case']['verdict']} ({answer['case']['fraud_probability']}) pattern={answer['case']['pattern']}")
    print(f"Actions: {[a['action'] + '/' + a['route'] for a in answer['next_best_actions']['final']]}")
    print(f"SAR: {answer['sar']['file']} | stop: {answer['stop_reason']}")
    print(f"Saved {path}")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"Investigation failed: {e}")
        sys.exit(1)