import asyncio
import time

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import answer_writer
from graph import run_investigation

app = FastAPI(title="Fraud Agent API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class InvestigateRequest(BaseModel):
    case_id: str
    transaction_id: str
    trigger_type: str = "risk_score"


@app.post("/investigate")
async def investigate(req: InvestigateRequest):
    start = time.time()
    try:
        final_state = await asyncio.to_thread(
            run_investigation, req.case_id, req.transaction_id, req.trigger_type)
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
    state = dict(final_state)
    state["latency_s"] = time.time() - start
    answer = answer_writer.build_answer(state)
    answer_writer.write_answer(answer)
    return {"status": "completed", **answer}


@app.get("/health")
async def health():
    return {"status": "ok", "service": "fraud-agent"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api:app", host="0.0.0.0", port=8000)