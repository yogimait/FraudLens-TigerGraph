import json

def apply_policy(state: dict) -> dict:
    """
    Deterministic rule engine that implements R1-R10 from the fraud policy.
    It takes the classification verdict and pattern and updates final_actions,
    exposure, and sar_required.
    """
    verdict = state.get("verdict", "uncertain").lower()
    pattern = state.get("pattern", "Unknown")
    probability = state.get("fraud_probability", 0.0)
    exposure = state.get("exposure_usd", 0.0)
    
    actions = []
    sar_required = False
    
    # R1 & R2: Legitimate cases
    if verdict == "legitimate" or probability < 0.30:
        if state.get("trigger_type") == "customer_report":
            actions.append({"action": "NOTIFY_CUSTOMER", "reason": "No fraud found on reported transaction."})
        return {
            "final_actions": actions,
            "sar_required": False
        }
        
    # R3: High probability auto-block
    if probability >= 0.95:
        actions.append({"action": "BLOCK_CARD", "reason": "Probability >= 95%"})
        actions.append({"action": "REJECT_TRANSACTION", "reason": "Probability >= 95%"})
        actions.append({"action": "REQUIRE_L2_APPROVAL", "reason": "Mandatory for >=95% probability cases"})
        
    # R4: Medium probability L1 review
    elif 0.70 <= probability < 0.95:
        actions.append({"action": "REQUIRE_L1_APPROVAL", "reason": "Probability between 70% and 95%"})
        
    # R5: Device/IP Blocking (Card Testing / Account Takeover)
    if verdict == "fraud" and pattern in ["Card Testing", "Account Takeover"]:
        actions.append({"action": "BLOCK_DEVICE", "reason": f"Pattern is {pattern}"})
        actions.append({"action": "FORCE_PASSWORD_RESET", "reason": "Account Takeover protocol"})
        
    # R6 & R7: SAR Filing thresholds
    if verdict == "fraud":
        is_coordinated = pattern in ["Coordinated Ring", "Undocumented Pattern"]
        shared_attributes = False # Simplification: Would check graph connected cards
        
        if exposure > 1000 or is_coordinated or shared_attributes:
            sar_required = True
            actions.append({"action": "FILE_REPORT", "reason": "SAR threshold met (>$1k or coordinated ring)."})
            actions.append({"action": "REQUIRE_L2_APPROVAL", "reason": "Mandatory for SAR filing."})
            
    # R8: Uncertain cases
    if verdict == "uncertain":
        actions.append({"action": "REQUIRE_L1_APPROVAL", "reason": "Uncertain verdict requires human review."})
        
    # R10: Dispute resolution (If trigger was customer_report and fraud confirmed)
    if state.get("trigger_type") == "customer_report" and verdict == "fraud":
        actions.append({"action": "REFUND_CUSTOMER", "reason": "Fraud confirmed on disputed transaction."})
        
    # Deduplicate actions
    seen = set()
    deduped_actions = []
    for act in actions:
        if act["action"] not in seen:
            seen.add(act["action"])
            deduped_actions.append(act)
            
    return {
        "final_actions": deduped_actions,
        "sar_required": sar_required
    }
