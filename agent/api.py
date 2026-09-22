from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Any, Optional, List
import time
import asyncio
from graph import graph

app = FastAPI(title="Fraud Agent API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class InvestigateRequest(BaseModel):
    case_id: str
    transaction_id: str
    trigger_type: str = "risk_score"

class InvestigateResponse(BaseModel):
    status: str
    case: dict
    sar: dict
    next_best_actions: dict
    graph_data: dict
    metadata: dict

@app.post("/investigate", response_model=InvestigateResponse)
async def investigate(req: InvestigateRequest):
    """Run the LangGraph investigation agent for a given transaction."""
    start_time = time.time()
    
    initial_state = {
        "case_id": req.case_id,
        "case_data": {"TransactionID": req.transaction_id},
        "trigger_type": req.trigger_type
    }
    
    try:
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
                "exposure_usd": final_state.get('exposure_usd', 0),
                "summary": final_state.get('summary', "")
            },
            "sar": {
                "file": final_state.get('sar_required', False),
                "narrative": final_state.get('sar_narrative', ""),
                "subjects": final_state.get('sar_subjects', [])
            },
            "next_best_actions": {
                "initial": final_state.get('initial_actions', []),
                "final": final_state.get('final_actions', [])
            },
            "graph_data": {
                "nodes": final_state.get('graph_nodes', []),
                "edges": final_state.get('graph_edges', [])
            },
            "metadata": {
                "duration_seconds": round(time.time() - start_time, 2),
                "stop_reason": final_state.get("stop_reason", "completed"),
                "jev_classification": final_state.get("jev_classification", {}),
                "evidence_count": len(final_state.get("graph_evidence", []))
            }
        }
        
        # Write JSON file
        import json, os
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
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health():
    return {"status": "ok", "service": "fraud-agent"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)
