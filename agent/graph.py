import os
import json
from typing import Dict, Any, Literal
from langgraph.graph import StateGraph, START, END
from pydantic import BaseModel

from state import InvestigationState
from jev_client import classify_fraud_pattern
from llm import synthesize_evidence, generate_outputs
from policy import apply_policy

import pyTigerGraph as tg

# Setup TigerGraph connection
conn = tg.TigerGraphConnection(
    host=os.environ.get("TG_HOST", ""),
    graphname=os.environ.get("TG_GRAPH", "FraudGraph"),
    gsqlSecret=os.environ.get("TG_SECRET", ""),
    tgCloud=True
)
conn.getToken(conn.createSecret())

def load_case(state: InvestigationState) -> InvestigationState:
    """Load case data into the state."""
    # Assume case_data and trigger_type are passed in the initial state
    txn_id = state.get("case_data", {}).get("TransactionID")
    if txn_id:
        try:
            # Fetch initial transaction
            res = conn.getVerticesById("Transaction", txn_id)
            if res:
                return {"flagged_txn": res[0].get("attributes", {})}
        except Exception as e:
            print(f"Transaction not found or error: {e}")
            
    return {"flagged_txn": state.get("case_data", {})}

def jev_fast_routing(state: InvestigationState) -> InvestigationState:
    """Use Jev to quickly classify the initial pattern."""
    txn = state.get("flagged_txn", {})
    history = state.get("customer_history", [])
    
    classification = classify_fraud_pattern(txn, history)
    return {"jev_classification": classification}

def investigate_graph(state: InvestigationState) -> InvestigationState:
    """Gather evidence using installed GSQL queries."""
    txn = state.get("flagged_txn", {})
    txn_id = state.get("case_data", {}).get("TransactionID")
    
    evidence = []
    
    # 1. Get Transaction Device
    if txn_id:
        try:
            device_res = conn.runInstalledQuery("get_transaction_device", {"t_id": txn_id})
            if device_res and len(device_res) > 0:
                evidence.append({"source": "graph", "type": "device", "data": device_res[0].get("Devices", [])})
        except Exception as e:
            print(f"Error running get_transaction_device: {e}")
            
    # 2. Add Jev insights
    jev_result = state.get("jev_classification", {})
    if jev_result.get("jev_pattern") != "Unknown":
         evidence.append({"source": "jev_classifier", "type": "classification", "data": jev_result})
         
    return {"graph_evidence": evidence}

def assess_evidence(state: InvestigationState) -> InvestigationState:
    """Use LLM to determine fraud probability and verdict."""
    assessment = synthesize_evidence(state)
    
    return {
        "fraud_probability": assessment.get("fraud_probability", 0.0),
        "pattern": assessment.get("pattern", "Unknown"),
        "pattern_description": assessment.get("pattern_description", ""),
        "verdict": assessment.get("verdict", "uncertain"),
        "affected_txn_ids": assessment.get("affected_txn_ids", []),
        "first_suspicious_txn_id": assessment.get("first_suspicious_txn_id", "")
    }

def apply_policy_node(state: InvestigationState) -> InvestigationState:
    """Apply deterministic rules."""
    policy_result = apply_policy(state)
    return {
        "final_actions": policy_result.get("final_actions", []),
        "sar_required": policy_result.get("sar_required", False)
    }

def generate_outputs_node(state: InvestigationState) -> InvestigationState:
    """Generate final summary and SAR."""
    outputs = generate_outputs(state)
    return {
        "summary": outputs.get("summary", ""),
        "sar_narrative": outputs.get("sar_narrative", ""),
        "stop_reason": outputs.get("stop_reason", "Completed gracefully.")
    }

def route_next_steps(state: InvestigationState) -> Literal["apply_policy", "END"]:
    """Routing logic after assessment."""
    if state.get("verdict") in ["fraud", "legitimate"]:
        return "apply_policy"
    # For hackathon simplicity, we push uncertain cases to policy as well
    # The policy requires L1 approval for uncertain verdicts.
    return "apply_policy"

# Build Graph
builder = StateGraph(InvestigationState)

builder.add_node("load_case", load_case)
builder.add_node("jev_fast_routing", jev_fast_routing)
builder.add_node("investigate_graph", investigate_graph)
builder.add_node("assess_evidence", assess_evidence)
builder.add_node("apply_policy", apply_policy_node)
builder.add_node("generate_outputs", generate_outputs_node)

builder.add_edge(START, "load_case")
builder.add_edge("load_case", "jev_fast_routing")
builder.add_edge("jev_fast_routing", "investigate_graph")
builder.add_edge("investigate_graph", "assess_evidence")
builder.add_edge("assess_evidence", "apply_policy")
builder.add_edge("apply_policy", "generate_outputs")
builder.add_edge("generate_outputs", END)

graph = builder.compile()
