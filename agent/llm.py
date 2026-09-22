import os
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from dotenv import load_dotenv

load_dotenv()

from groq import Groq
import json

client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
MODEL_NAME = os.environ.get("GROQ_MODEL", "llama3-70b-8192")

KNOWN_PATTERNS = [
    "Card Testing",
    "Account Takeover", 
    "Transaction Laundering",
    "Coordinated Ring",
    "Synthetic Identity",
    "Anomalous Activity",
    "Insufficient Evidence"
]

def synthesize_evidence(state: dict) -> dict:
    """
    LLM reasoning node to synthesize all evidence and output a fraud assessment.
    Constrained to pick from known fraud patterns only.
    """
    txn_id = state.get("case_data", {}).get("TransactionID", "")
    
    prompt = f"""You are an expert fraud investigator at a financial institution. Analyze ALL of the following evidence carefully and determine the probability of fraud.

## Case Information
- Case ID: {state.get('case_id')}
- Trigger Type: {state.get('trigger_type')}
- Transaction ID: {txn_id}

## Flagged Transaction Data
{json.dumps(state.get('flagged_txn', {}), default=str, indent=2)}

## Graph Evidence (from TigerGraph)
{json.dumps(state.get('graph_evidence', []), indent=2, default=str)}

## Related Transactions on Same Card ({len(state.get('related_txns', []))} total)
{json.dumps(state.get('related_txns', [])[:5], indent=2, default=str)}

## Jev Fast Classification
{json.dumps(state.get('jev_classification', {}), indent=2)}

## Connected Cards
{json.dumps(state.get('connected_card_ids', []))}

## Computed Exposure
${state.get('exposure_usd', 0)}

## Initial Actions (before evidence gathering)
{json.dumps(state.get('initial_actions', []), indent=2)}

## Instructions
- `fraud_probability` must be a calibrated float between 0.0 and 1.0 reflecting your honest confidence
- `pattern` MUST be exactly one of: {json.dumps(KNOWN_PATTERNS)}
- Use "Insufficient Evidence" ONLY if you genuinely cannot determine any pattern
- `verdict` must be "fraud", "legitimate", or "uncertain"
- `affected_txn_ids` must contain ONLY transaction IDs that actually appear in the evidence above. The flagged transaction ID is: {txn_id}
- Write a clear `pattern_description` explaining what evidence supports this pattern classification

Output a strictly valid JSON object with these fields:
- fraud_probability: float
- pattern: string (from the list above)
- pattern_description: string (2-3 sentences explaining the evidence)
- verdict: string
- affected_txn_ids: list of strings
- first_suspicious_txn_id: string
"""

    chat_completion = client.chat.completions.create(
        messages=[
            {"role": "system", "content": "You are a fraud investigation AI. You output JSON only. No markdown formatting. Be precise and evidence-based."},
            {"role": "user", "content": prompt}
        ],
        model=MODEL_NAME,
        response_format={"type": "json_object"},
        temperature=0.0
    )
    
    try:
        result = json.loads(chat_completion.choices[0].message.content)
        # Validate pattern is from known list
        if result.get("pattern") not in KNOWN_PATTERNS:
            result["pattern"] = "Anomalous Activity"
        return result
    except Exception as e:
        print("Error parsing LLM JSON:", e)
        return {
            "fraud_probability": 0.5,
            "pattern": "Insufficient Evidence",
            "pattern_description": "Failed to parse LLM response.",
            "verdict": "uncertain",
            "affected_txn_ids": [txn_id] if txn_id else [],
            "first_suspicious_txn_id": txn_id or ""
        }

def generate_outputs(state: dict) -> dict:
    """
    Generate final case summary and SAR narrative (if required).
    """
    prompt = f"""You are finalizing a fraud investigation case. Write a professional case summary.

## Case Details
- Case ID: {state.get('case_id')}
- Verdict: {state.get('verdict')}
- Pattern: {state.get('pattern')}
- Pattern Description: {state.get('pattern_description')}
- Fraud Probability: {state.get('fraud_probability')}
- Exposure: ${state.get('exposure_usd', 0)}
- Affected Transactions: {json.dumps(state.get('affected_txn_ids', []))}
- SAR Required: {state.get('sar_required')}
- Trigger Type: {state.get('trigger_type')}

## Initial Actions (before evidence)
{json.dumps(state.get('initial_actions', []), indent=2)}

## Final Actions (after evidence)
{json.dumps(state.get('final_actions', []), indent=2)}

## Graph Evidence
{json.dumps(state.get('graph_evidence', [])[:3], indent=2, default=str)}

## Instructions
- Write a professional `summary` (3-5 sentences) covering: what triggered the case, what evidence was found, what pattern was identified, and what actions are recommended.
- If SAR Required is True, write a detailed `sar_narrative` (8-12 sentences) as a formal Suspicious Activity Report covering who, what, when, where, how, why.
- If SAR Required is False, output an empty string for sar_narrative.
- Write a clear `stop_reason` explaining why the investigation stopped.

Output a strictly valid JSON object with:
- summary: string
- sar_narrative: string  
- stop_reason: string
"""

    chat_completion = client.chat.completions.create(
        messages=[
            {"role": "system", "content": "You are a compliance officer. You output JSON only. No markdown formatting."},
            {"role": "user", "content": prompt}
        ],
        model=MODEL_NAME,
        response_format={"type": "json_object"},
        temperature=0.0
    )
    
    try:
        result = json.loads(chat_completion.choices[0].message.content)
        return result
    except Exception as e:
        return {
            "summary": "Investigation completed but summary generation failed.",
            "sar_narrative": "",
            "stop_reason": "Completed with output generation errors."
        }
