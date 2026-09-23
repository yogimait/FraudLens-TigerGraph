"""LLM reasoning layer (OpenRouter): evidence synthesis, reassessment, output generation.

The LLM reasons over evidence and produces text/assessments only. It never picks
policy actions (policy.py is deterministic). Calibration rules: the transaction
risk_score is a prior, not an answer; fraud_probability moves with evidence.
"""
import json
import os
import re
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv

load_dotenv()

PATTERN_ENUM = [
    "card_testing", "card_not_present_fraud", "card_not_present_new_device",
    "out_of_region_use", "account_takeover", "undocumented", "none",
]
VERDICT_ENUM = ["fraud", "legitimate", "uncertain"]

MODEL_NAME = os.environ.get("OPENROUTER_MODEL", "nvidia/nemotron-3-super-120b:free")
_BASE_URL = "https://openrouter.ai/api/v1"
_DEFAULT_HEADERS = {
    "HTTP-Referer": "https://github.com/yogimait/TigerGraphGoa",
    "X-Title": "FraudLens Agent",
}

_clients: Dict[str, Any] = {}
_exhausted_keys: set = set()


def _client_keys() -> List[str]:
    return [k for k in [os.environ.get("OPENROUTER_API_KEY", "")] if k]


def _get_client(key: str) -> Any:
    if key not in _clients:
        from openai import OpenAI
        _clients[key] = OpenAI(api_key=key, base_url=_BASE_URL, default_headers=_DEFAULT_HEADERS)
    return _clients[key]


TXN_FIELDS = ["txn_id", "ts", "amount", "risk_score", "channel", "product_cd", "region_id", "device_type"]


def _compact_evidence(ev: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "claim": str(ev.get("claim", ""))[:180],
        "source": ev.get("source", ""),
        "ref": ev.get("ref", ""),
        "entity_ids": [str(x) for x in (ev.get("entity_ids") or [])[:4]],
    }


def _compact_txn(txn: Dict[str, Any]) -> Dict[str, Any]:
    """Only the fields the assessment needs — full attrs are token bombs."""
    return {k: txn[k] for k in TXN_FIELDS if txn.get(k) not in (None, "")}


def _txn_id(txn: Dict[str, Any]) -> str:
    return str(txn.get("txn_id", txn.get("TransactionID", "")) or "")


def known_txn_ids(state: Dict[str, Any]) -> List[str]:
    ids = {_txn_id(state.get("flagged_txn") or {})}
    for t in state.get("related_txns") or []:
        tid = _txn_id(t)
        if tid:
            ids.add(tid)
    ids.discard("")
    return sorted(ids)


def _validate_assessment(result: Dict[str, Any], state: Dict[str, Any]) -> Dict[str, Any]:
    flagged = _txn_id(state.get("flagged_txn") or {})
    known = set(known_txn_ids(state))

    try:
        fp = max(0.0, min(1.0, float(result.get("fraud_probability", 0.5))))
    except (TypeError, ValueError):
        fp = 0.5
    result["fraud_probability"] = round(fp, 2)

    if result.get("pattern") not in PATTERN_ENUM:
        result["pattern"] = "none"
    if result.get("verdict") not in VERDICT_ENUM:
        result["verdict"] = "uncertain"
    if fp >= 0.70:
        result["verdict"] = "fraud"
    elif fp <= 0.30:
        result["verdict"] = "legitimate"
    else:
        result["verdict"] = "uncertain"

    affected = []
    for tid in result.get("affected_txn_ids") or []:
        tid = str(tid)
        if tid in known:
            affected.append(tid)
    if not affected and flagged and result["verdict"] != "legitimate":
        affected = [flagged]
    if result["verdict"] == "legitimate":
        affected = []
    result["affected_txn_ids"] = affected

    first = str(result.get("first_suspicious_txn_id") or "")
    if first not in affected:
        first = affected[0] if affected else ""
    result["first_suspicious_txn_id"] = first

    drivers = result.get("confidence_drivers")
    if not isinstance(drivers, list):
        drivers = []
    result["confidence_drivers"] = [str(d) for d in drivers][:8]
    return result


def _call(prompt: str, system: str) -> tuple:
    keys = _client_keys()
    if not keys:
        raise RuntimeError("OPENROUTER_API_KEY not configured")
    last_err: Optional[Exception] = None
    content = None
    tokens = 0
    for key in keys:
        if key in _exhausted_keys:
            continue
        client = _get_client(key)
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ]
        for use_json in (True, False, False):
            try:
                kwargs = {"response_format": {"type": "json_object"}} if use_json else {}
                completion = client.chat.completions.create(
                    messages=messages,
                    model=MODEL_NAME,
                    temperature=0.0,
                    **kwargs,
                )
                choices = getattr(completion, "choices", None)
                content = choices[0].message.content if choices else None
                if content is None:
                    raise RuntimeError("empty completion content")
                try:
                    tokens = int(completion.usage.total_tokens)
                except (AttributeError, TypeError, ValueError):
                    tokens = 0
                break
            except Exception as e:
                msg = str(e).lower()
                if "empty completion" in msg:
                    last_err = e
                    continue
                if use_json and ("response_format" in msg or "json_schema" in msg or "unsupported" in msg):
                    continue
                if "rate limit" in msg or "429" in msg or "credits" in msg or "402" in msg:
                    _exhausted_keys.add(key)
                    last_err = e
                    break
                raise
        if content is not None:
            break
    if content is None:
        raise last_err or RuntimeError("no LLM API key available")
    return content, tokens


def _call_json(prompt: str, system: str) -> tuple:
    try:
        raw, tokens = _call(prompt, system)
        return json.loads(_strip_fences(raw)), tokens
    except json.JSONDecodeError:
        raw, tokens = _call(prompt + "\nReturn ONLY one valid JSON object. No markdown, no trailing text, escape all quotes properly.", system)
        return json.loads(_strip_fences(raw)), tokens


def _prompt_evidence(state: Dict[str, Any], reassess: bool) -> str:
    flagged = state.get("flagged_txn") or {}
    flagged_id = _txn_id(flagged)
    known = known_txn_ids(state)
    rag_context = state.get("rag_context") or []
    similar = state.get("similar_prior_cases") or []
    customer = state.get("customer_response") or ""

    parts = [
        f"Case: {state.get('case_id')} | trigger: {state.get('trigger_type')} | flagged transaction: {flagged_id}",
        f"Trigger context: {json.dumps((state.get('case_data') or {}).get('trigger_text', ''), default=str)[:300]}",
        f"Flagged transaction: {json.dumps(_compact_txn(flagged), default=str)}",
        f"Graph evidence: {json.dumps([_compact_evidence(e) for e in state.get('evidence') or []], default=str)}",
        f"Related transactions on the same card (most recent {len(state.get('related_txns') or [])}): {json.dumps([_compact_txn(t) for t in (state.get('related_txns') or [])[:20]], default=str)}",
        f"Jev fast classification: {json.dumps(state.get('jev_classification') or {})}",
        f"Known transaction IDs in this investigation: {json.dumps(known)}",
    ]
    if rag_context:
        parts.append(f"Retrieved policy/pattern documents: {json.dumps([{'ref': r.get('ref'), 'excerpt': r.get('text', '')[:180]} for r in rag_context], default=str)}")
    if similar:
        parts.append(f"Similar closed cases used as memory: {json.dumps(similar, default=str)}")
    if customer:
        parts.append(f"Simulated customer response to our evidence request: {customer!r}. Treat this as new evidence.")
    parts.append(f"""Calibration rules:
- The transaction risk_score ({flagged.get('risk_score', 0)}) is a PRIOR from the bank's model, never the answer. Many high scores are legitimate; some fraud scores low. Move away from it only as your evidence justifies.
- fraud_probability must reflect what the evidence shows, not the prior alone. Half of flagged cases are legitimate.
- LEGITIMATE discriminators — check these FIRST, they are common: (1) the flagged transaction repeats a recurring pattern in the card's history: same product_cd/merchant category, similar amount, regular cadence (disputed-but-legitimate, policy R7); (2) in-person purchase consistent with the cardholder's usual channel; (3) amount, hour and region consistent with the card's past behavior. If any of these match and there is no device/identity evidence of compromise, conclude legitimate with fraud_probability 0.05-0.25.
- FRAUD discriminators: new device identity, out-of-region use inconsistent with history, burst of small amounts then a larger one (card testing), takeover signals, or a denied customer validation with no recurring-pattern match.
- Do NOT park probabilities at round thresholds (0.70, 0.50). Give your honest estimate anywhere in 0.0-1.0.
- Consistency: verdict "fraud" requires fraud_probability >= 0.70; verdict "legitimate" requires fraud_probability <= 0.30; verdict "uncertain" only for probabilities in between.
- Use at least two independent signals before concluding fraud; a risk score alone is one signal.
- affected_txn_ids may contain ONLY ids from the known-ids list. Include every transaction that is part of the same fraud episode (the flagged one first among them). For legitimate verdicts use an empty list.
- verdict is "fraud" only for confirmed/strongly-suspected activity, "legitimate" when the evidence fits the cardholder's normal behavior, "uncertain" otherwise.
- pattern MUST be one of {json.dumps(PATTERN_ENUM)}; use "undocumented" for coordinated abuse fitting none of the known patterns and describe it in pattern_description.
Output strictly valid JSON with fields: fraud_probability (float), pattern (string), pattern_description (string), verdict (string), affected_txn_ids (list of strings), first_suspicious_txn_id (string), confidence_drivers (list of short strings naming each evidence item that moved your probability).
{"Re-assess the case with the customer response included; explain how it changed your view." if reassess else ""}""")
    return "\n\n".join(parts)


def synthesize_evidence(state: Dict[str, Any]) -> Dict[str, Any]:
    """LLM synthesis of the current evidence into a fraud assessment."""
    flagged_id = _txn_id(state.get("flagged_txn") or {})
    fallback = {
        "fraud_probability": 0.5, "pattern": "none", "pattern_description": "",
        "verdict": "uncertain",
        "affected_txn_ids": [flagged_id] if flagged_id else [],
        "first_suspicious_txn_id": "", "confidence_drivers": [], "tokens": 0,
        "llm_ok": False,
    }
    try:
        result, tokens = _call_json(_prompt_evidence(state, reassess=bool(state.get("customer_response"))),
                                    "You are a fraud investigation AI. Output JSON only, no markdown. Be precise, evidence-based, and honestly calibrated.")
    except Exception as e:
        print(f"LLM evidence synthesis failed: {type(e).__name__}: {e}")
        return fallback
    result = _validate_assessment(result, state)
    result["tokens"] = tokens
    result["llm_ok"] = True
    return result


def generate_outputs(state: Dict[str, Any]) -> Dict[str, Any]:
    """Produce the analyst summary, SAR narrative (when filing) and stop_reason."""
    filing = bool(state.get("sar_required"))
    filing_block = ""
    if filing:
        filing_block = f"""
Write `sar_narrative` as a formal suspicious activity report, 6-12 sentences, standing on its own: who (customer, cards, devices), what happened, when (dates), where (channels/regions), how it was carried out, why it is suspicious. Total amount: ${state.get('exposure_usd', 0)}. Subjects: {json.dumps(state.get('sar_subjects') or [])}."""
    prompt = f"""Finalize this fraud investigation case.

Case: {state.get('case_id')} | verdict: {state.get('verdict')} | pattern: {state.get('pattern')} | probability: {state.get('fraud_probability')} | exposure: ${state.get('exposure_usd', 0)}
Evidence highlights: {json.dumps([_compact_evidence(e) for e in (state.get('evidence') or [])[:6]], default=str)}
Initial actions: {json.dumps(state.get('initial_actions') or [])}
Final actions: {json.dumps(state.get('final_actions') or [])}
Customer response: {state.get('customer_response') or 'none'} | Evidence requests: {json.dumps(state.get('evidence_requests') or [])}
Stop reason (deterministic): {state.get('stop_reason', '')}
SAR filing required: {filing}

Write `summary`: 2-6 sentences an analyst could read: what triggered the case, what the evidence showed, the verdict and actions.
Write `stop_reason`: one sentence on why the investigation stopped, following the deterministic reason but in plain words.
{filing_block}
If SAR filing is false, output "" for sar_narrative.
Output strictly valid JSON: {{"summary": str, "sar_narrative": str, "stop_reason": str}}"""
    try:
        result, tokens = _call_json(prompt, "You are a compliance officer. Output JSON only, no markdown.")
    except Exception as e:
        print(f"LLM output generation failed: {type(e).__name__}: {e}")
        return {
            "summary": "Investigation completed; summary generation failed.",
            "sar_narrative": "",
            "stop_reason": state.get("stop_reason", "Investigation completed."),
            "tokens": 0,
            "llm_ok": False,
        }
    return {
        "summary": str(result.get("summary", "")),
        "sar_narrative": str(result.get("sar_narrative", "")),
        "stop_reason": str(result.get("stop_reason", "")) or state.get("stop_reason", ""),
        "tokens": tokens,
    }


def _strip_fences(text: str) -> str:
    text = text.strip()
    match = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
    return match.group(1).strip() if match else text