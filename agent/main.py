import sys
import json
import asyncio
from dotenv import load_dotenv

from graph import graph
from state import InvestigationState

load_dotenv()

def run_cli():
    if len(sys.argv) < 2:
        print("Usage: python main.py <TransactionID>")
        sys.exit(1)
        
    txn_id = sys.argv[1]
    print(f"Starting investigation for TransactionID: {txn_id}")
    
    initial_state = {
        "case_id": f"CASE_{txn_id}",
        "case_data": {"TransactionID": txn_id},
        "trigger_type": "risk_score" # Default for benchmark
    }
    
    # Run the LangGraph state machine
    # Note: `graph.invoke` is synchronous in LangGraph v0.1
    final_state = graph.invoke(initial_state)
    
    print("\n--- INVESTIGATION RESULTS ---")
    print(f"Verdict: {final_state.get('verdict')}")
    print(f"Pattern: {final_state.get('pattern')} ({final_state.get('fraud_probability')})")
    print(f"Actions: {json.dumps(final_state.get('final_actions', []), indent=2)}")
    print(f"SAR Required: {final_state.get('sar_required')}")
    print(f"Summary: {final_state.get('summary')}")
    
    # Save output to cases/
    output_path = f"../cases/CASE_{txn_id}.json"
    
    output = {
        "case": {
            "case_id": final_state.get('case_id'),
            "verdict": final_state.get('verdict'),
            "fraud_probability": final_state.get('fraud_probability'),
            "pattern": final_state.get('pattern'),
            "pattern_description": final_state.get('pattern_description'),
            "affected_txn_ids": final_state.get('affected_txn_ids'),
            "first_suspicious_txn_id": final_state.get('first_suspicious_txn_id'),
            "exposure_usd": final_state.get('exposure_usd', 0)
        },
        "sar": {
            "file": final_state.get('sar_required', False),
            "narrative": final_state.get('sar_narrative', ""),
            "subjects": final_state.get('sar_subjects', [])
        },
        "next_best_actions": {
            "initial": [],
            "final": final_state.get('final_actions', [])
        }
    }
    
    with open(output_path, "w") as f:
        json.dump(output, f, indent=2)
        
    print(f"\nSaved JSON result to {output_path}")

if __name__ == "__main__":
    run_cli()
