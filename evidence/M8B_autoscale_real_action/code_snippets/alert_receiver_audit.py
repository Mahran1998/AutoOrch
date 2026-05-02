```python
audit = {
    "ts": now,
    "target": target,
    "features": features,
    "restart_context": restart_context.to_dict(),
    "candidate_action": decision_result["candidate_action"],
    "final_action": decision_result["final_action"],
    "decision": decision_result["decision"],
    "reason": decision_result["reason"],
    "p_autoscale": decision_result["p_autoscale"],
    "p_restart": decision_result["p_restart"],
    "signals": decision_result["signals"],
    "action_result": action_result,
    "alerts_count": len(payload.get("alerts", [])) if isinstance(payload.get("alerts"), list) else None,
}
logger.info("AUDIT %s", json.dumps(audit, ensure_ascii=False))
```
