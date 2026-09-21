import csv
import time
import requests
import json
import os

API_URL = "http://localhost:3001/cases/{}/trigger"
CASE_PACK_PATH = os.path.join(os.path.dirname(__file__), "../../Initial-docs/dataset/case_pack.csv")

def run_benchmark():
    if not os.path.exists(CASE_PACK_PATH):
        print(f"Error: {CASE_PACK_PATH} not found.")
        return

    cases = []
    with open(CASE_PACK_PATH, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            cases.append(row)

    print(f"Loaded {len(cases)} cases to process.")
    
    success_count = 0
    failure_count = 0

    for idx, case in enumerate(cases):
        case_id = case['case_id']
        txn_id = case['flagged_txn_id']
        trigger_type = case['trigger_type']
        
        print(f"[{idx+1}/{len(cases)}] Triggering case {case_id} (Txn: {txn_id}, Trigger: {trigger_type})...")
        
        payload = {
            "transaction_id": txn_id,
            "trigger_type": trigger_type
        }
        
        try:
            # We are sending to NestJS, which will trigger LangGraph.
            # NestJS awaits the response and then saves it to MongoDB.
            response = requests.post(API_URL.format(case_id), json=payload, timeout=120)
            
            if response.status_code in [200, 201]:
                print(f"  -> SUCCESS: {case_id} completed.")
                success_count += 1
            else:
                print(f"  -> FAILED: {case_id} returned {response.status_code}")
                print(f"     {response.text}")
                failure_count += 1
        except Exception as e:
            print(f"  -> ERROR: {case_id} encountered exception: {e}")
            failure_count += 1
            
        print(f"  -> Waiting 5 seconds before next case to respect rate limits...")
        time.sleep(5)
        
    print("\n--- BENCHMARK COMPLETE ---")
    print(f"Successful: {success_count}")
    print(f"Failed: {failure_count}")

if __name__ == "__main__":
    run_benchmark()
