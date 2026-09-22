import os
from dotenv import load_dotenv
load_dotenv()
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
    """Load case data and fetch the flagged transaction from TigerGraph."""
    txn_id = state.get("case_data", {}).get("TransactionID")
    if txn_id:
        try:
            res = conn.getVerticesById("Transaction", txn_id)
            if res:
                return {"flagged_txn": res[0].get("attributes", {})}
        except Exception as e:
            print(f"Transaction not found or error: {e}")
            
    return {"flagged_txn": state.get("case_data", {})}

def investigate_graph(state: InvestigationState) -> InvestigationState:
    """Gather evidence from TigerGraph using ALL available GSQL queries."""
    txn = state.get("flagged_txn", {})
    txn_id = state.get("case_data", {}).get("TransactionID")
    
    evidence = []
    graph_nodes = []
    graph_edges = []
    customer_history = []
    related_txns = []
    connected_card_ids = []
    total_exposure = 0.0
    
    # Add the flagged transaction as a node
    graph_nodes.append({
        "id": f"txn-{txn_id}",
        "type": "transaction",
        "label": f"Txn {txn_id}",
        "data": {"amount": txn.get("amount", txn.get("amt", txn.get("TransactionAmt", 0))), "risk_score": txn.get("risk_score", 0)}
    })
    
    txn_amount = float(txn.get("amount", txn.get("amt", txn.get("TransactionAmt", 0))) or 0)
    total_exposure += txn_amount

    # 1. Get Transaction Device
    if txn_id:
        try:
            device_res = conn.runInstalledQuery("get_transaction_device", {"t_id": txn_id})
            if device_res and len(device_res) > 0:
                devices = device_res[0].get("Devices", [])
                evidence.append({"source": "graph", "type": "device", "ref": "get_transaction_device", "entity_ids": [txn_id], "data": devices})
                for d in devices:
                    attrs = d.get("attributes", d)
                    dev_id = d.get("v_id", attrs.get("device_id", "unknown"))
                    graph_nodes.append({"id": f"dev-{dev_id}", "type": "device", "label": f"Device {dev_id}", "data": attrs})
                    graph_edges.append({"source": f"txn-{txn_id}", "target": f"dev-{dev_id}", "label": "FROM_DEVICE"})
        except Exception as e:
            print(f"Error running get_transaction_device: {e}")

    # 2. Find customer cards (derive customer from transaction if possible)
    card_id = ""
    if txn_id:
        try:
            query = f'''INTERPRET QUERY (STRING t_id) FOR GRAPH {conn.graphname} {{
                Start = {{Transaction.*}};
                Cards = SELECT s FROM Start:t -(<MADE:e)- Card:s WHERE t.txn_id == t_id;
                PRINT Cards;
            }}'''
            res = conn.runInterpretedQuery(query, {'t_id': str(txn_id)})
            if res and len(res) > 0 and 'Cards' in res[0] and len(res[0]['Cards']) > 0:
                card_id = res[0]['Cards'][0]['v_id']
        except Exception as e:
            print(f"Error finding card for txn: {e}")
            
    if not card_id:
        card_id = txn.get("card1", txn.get("card_id", ""))
        
    if card_id:
        graph_nodes.append({"id": f"card-{card_id}", "type": "card", "label": f"Card ...{str(card_id)[-4:]}", "data": {}})
        graph_edges.append({"source": f"card-{card_id}", "target": f"txn-{txn_id}", "label": "MADE"})
        connected_card_ids.append(str(card_id))

    # 3. Get card transactions for velocity analysis
    if card_id:
        try:
            query = f'''INTERPRET QUERY (STRING c_id) FOR GRAPH {conn.graphname} {{
                Start = {{Card.*}};
                Txns = SELECT t FROM Start:s -(MADE:e)-> Transaction:t WHERE s.card_id == c_id;
                PRINT Txns;
            }}'''
            card_txn_res = conn.runInterpretedQuery(query, {"c_id": str(card_id)})
            if card_txn_res and len(card_txn_res) > 0 and 'Txns' in card_txn_res[0]:
                card_txns = card_txn_res[0].get("Txns", [])
                # Limit to most recent 10 for context to prevent graph clutter
                recent_txns = card_txns[:10] if len(card_txns) > 10 else card_txns
                for ct in recent_txns:
                    ct_attrs = ct.get("attributes", ct)
                    ct_id = ct.get("v_id", ct_attrs.get("txn_id", ""))
                    ct_amount = float(ct_attrs.get("amount", ct_attrs.get("amt", ct_attrs.get("TransactionAmt", 0))) or 0)
                    related_txns.append(ct_attrs)
                    if str(ct_id) != str(txn_id):
                        graph_nodes.append({"id": f"txn-{ct_id}", "type": "transaction", "label": f"Txn {ct_id}", "data": {"amount": ct_amount}})
                        graph_edges.append({"source": f"card-{card_id}", "target": f"txn-{ct_id}", "label": "MADE"})
                        total_exposure += ct_amount
                
                evidence.append({
                    "source": "graph", "type": "card_transactions", "ref": "get_card_transactions (interpreted)",
                    "entity_ids": [str(card_id)],
                    "data": {"total_txns": len(card_txns), "recent_txns_count": len(recent_txns), "sample": recent_txns[:5]}
                })
        except Exception as e:
            print(f"Error running get_card_transactions interpreted query: {e}")

    return {
        "graph_evidence": evidence,
        "customer_history": customer_history,
        "related_txns": related_txns,
        "connected_card_ids": connected_card_ids,
        "exposure_usd": round(total_exposure, 2),
        "graph_nodes": graph_nodes,
        "graph_edges": graph_edges
    }

def jev_fast_routing(state: InvestigationState) -> InvestigationState:
    """Use Jev to quickly classify the initial pattern using real transaction data."""
    txn = state.get("flagged_txn", {})
    history = state.get("related_txns", [])
    
    classification = classify_fraud_pattern(txn, history)
    return {"jev_classification": classification}

def compute_initial_actions(state: InvestigationState) -> InvestigationState:
    """Record what the policy engine would recommend BEFORE evidence requests."""
    initial_policy = apply_policy(state)
    return {"initial_actions": initial_policy.get("final_actions", [])}

def assess_evidence(state: InvestigationState) -> InvestigationState:
    """Use LLM to determine fraud probability and verdict."""
    assessment = synthesize_evidence(state)
    
    return {
        "fraud_probability": assessment.get("fraud_probability", 0.0),
        "pattern": assessment.get("pattern", "Insufficient Evidence"),
        "pattern_description": assessment.get("pattern_description", ""),
        "verdict": assessment.get("verdict", "uncertain"),
        "affected_txn_ids": assessment.get("affected_txn_ids", []),
        "first_suspicious_txn_id": assessment.get("first_suspicious_txn_id", "")
    }

def apply_policy_node(state: InvestigationState) -> InvestigationState:
    """Apply deterministic policy rules to determine final actions."""
    policy_result = apply_policy(state)
    return {
        "final_actions": policy_result.get("final_actions", []),
        "sar_required": policy_result.get("sar_required", False)
    }

def generate_outputs_node(state: InvestigationState) -> InvestigationState:
    """Generate final summary and SAR narrative."""
    outputs = generate_outputs(state)
    return {
        "summary": outputs.get("summary", ""),
        "sar_narrative": outputs.get("sar_narrative", ""),
        "stop_reason": outputs.get("stop_reason", "Completed gracefully.")
    }

# Build Graph — the investigation state machine
builder = StateGraph(InvestigationState)

builder.add_node("load_case", load_case)
builder.add_node("investigate_graph", investigate_graph)
builder.add_node("jev_fast_routing", jev_fast_routing)
builder.add_node("compute_initial_actions", compute_initial_actions)
builder.add_node("assess_evidence", assess_evidence)
builder.add_node("apply_policy", apply_policy_node)
builder.add_node("generate_outputs", generate_outputs_node)

# Flow: load → graph investigation → jev classification → initial actions → LLM assessment → policy → outputs
builder.add_edge(START, "load_case")
builder.add_edge("load_case", "investigate_graph")
builder.add_edge("investigate_graph", "jev_fast_routing")
builder.add_edge("jev_fast_routing", "compute_initial_actions")
builder.add_edge("compute_initial_actions", "assess_evidence")
builder.add_edge("assess_evidence", "apply_policy")
builder.add_edge("apply_policy", "generate_outputs")
builder.add_edge("generate_outputs", END)

graph = builder.compile()
