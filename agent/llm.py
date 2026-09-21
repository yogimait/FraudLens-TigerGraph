import os
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from dotenv import load_dotenv

load_dotenv()

# We need langchain-groq for ChatGroq! Oh wait, I installed "groq", but to use ChatGroq I need langchain-groq.
# I will use the raw groq client instead, which is often more reliable for strict JSON mode.
from groq import Groq
import json

client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
MODEL_NAME = os.environ.get("GROQ_MODEL", "llama3-70b-8192")

def synthesize_evidence(state: dict) -> dict:
    """
    LLM reasoning node to synthesize evidence and output a fraud probability.
    """
    prompt = f"""
    You are an expert fraud investigator. Analyze the following evidence and determine the probability of fraud.
    
    Trigger: {state.get('trigger_type')}
    Flagged Transaction: {json.dumps(state.get('flagged_txn', {}), default=str)}
    
    Graph Evidence:
    {json.dumps(state.get('graph_evidence', []), indent=2)}
    
    Jev Classification:
    {json.dumps(state.get('jev_classification', {}), indent=2)}
    
    Historical Similar Cases:
    {json.dumps(state.get('similar_prior_cases', []), indent=2)}
    
    Output a strictly valid JSON object with the following fields:
    - fraud_probability: float between 0.0 and 1.0
    - pattern: string name of the fraud pattern (e.g. 'Card Testing', 'Account Takeover', 'None')
    - pattern_description: string explaining why this pattern matches
    - verdict: string ('fraud', 'legitimate', or 'uncertain')
    - affected_txn_ids: list of strings (transaction IDs that are part of the fraud episode)
    - first_suspicious_txn_id: string (the first transaction ID in the pattern)
    """

    chat_completion = client.chat.completions.create(
        messages=[
            {"role": "system", "content": "You output JSON only. No markdown formatting."},
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
        print("Error parsing LLM JSON:", e)
        return {
            "fraud_probability": 0.5,
            "pattern": "Unknown",
            "pattern_description": "Failed to parse LLM response.",
            "verdict": "uncertain",
            "affected_txn_ids": [],
            "first_suspicious_txn_id": ""
        }

def generate_outputs(state: dict) -> dict:
    """
    Generate final summary and SAR narrative (if required).
    """
    prompt = f"""
    You are finalizing a fraud investigation case. 
    
    Verdict: {state.get('verdict')}
    Pattern: {state.get('pattern')}
    Probability: {state.get('fraud_probability')}
    SAR Required: {state.get('sar_required')}
    
    Final Actions:
    {json.dumps(state.get('final_actions', []), indent=2)}
    
    Write a summary (2-4 sentences). 
    If SAR Required is True, write a detailed SAR narrative (6-12 sentences covering who, what, when, where, how, why).
    If SAR Required is False, output an empty string for sar_narrative.
    
    Output a strictly valid JSON object with the following fields:
    - summary: string
    - sar_narrative: string
    - stop_reason: string (why the investigation stopped)
    """

    chat_completion = client.chat.completions.create(
        messages=[
            {"role": "system", "content": "You output JSON only. No markdown formatting."},
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
            "summary": "Investigation completed.",
            "sar_narrative": "",
            "stop_reason": "Completed with errors."
        }
