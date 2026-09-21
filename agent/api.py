from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Dict, Any, Optional
import time
import asyncio
from graph import graph

app = FastAPI(title="Fraud Agent API")

class InvestigateRequest(BaseModel):
    case_id: str
    transaction_id: str
    trigger_type: str = "risk_score"

class InvestigateResponse(BaseModel):
    status: str
    case: dict
    sar: dict
    next_best_actions: dict
    metadata: dict

@app.post("/investigate", response_model=InvestigateResponse)
async def investigate(req: InvestigateRequest):
    """
    Run the LangGraph investigation agent for a given transaction.
    MVP: Synchronous response (blocks until graph completes).
    """
    start_time = time.time()
    
    initial_state = {
        "case_id": req.case_id,
        "case_data": {"TransactionID": req.transaction_id},
        "trigger_type": req.trigger_type
    }
    
    try:
        # Run graph (in threadpool since graph.invoke is sync)
        final_state = await asyncio.to_thread(graph.invoke, initial_state)
        
        output = {
            "status": "completed",
            "case": {
                "case_id": final_state.get('case_id'),
                "verdict": final_state.get('verdict'),
                "fraud_probability": final_state.get('fraud_probability'),
                "pattern": final_state.get('pattern'),
                "pattern_description": final_state.get('pattern_description'),
                "affected_txn_ids": final_state.get('affected_txn_ids', []),
                "first_suspicious_txn_id": final_state.get('first_suspicious_txn_id', ""),
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
            },
            "metadata": {
                "duration_seconds": round(time.time() - start_time, 2),
                "stop_reason": final_state.get("stop_reason", "completed")
            }
        }
        
        # Write to JSON file in cases directory
        import json
        import os
        cases_dir = os.path.join(os.path.dirname(__file__), "../cases")
        os.makedirs(cases_dir, exist_ok=True)
        with open(os.path.join(cases_dir, f"{req.case_id}.json"), "w") as f:
            json.dump({
                "case": output["case"],
                "sar": output["sar"],
                "next_best_actions": output["next_best_actions"]
            }, f, indent=2)
            
        return output
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"Agent Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)
