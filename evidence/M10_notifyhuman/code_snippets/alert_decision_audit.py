decision_result = apply_consecutive_escalation(
    target=target,
    decision_payload=decision_result,
)

decision_result = apply_guardrails(
    target=target,
    decision_payload=decision_result,
    restart_context=restart_context,
)

action_result = ACTION_EXECUTOR.execute(
    decision=decision_result["final_action"],
    target=action_target,
    max_replicas=SETTINGS.max_replicas,
)

DECISIONS.labels(decision=decision_result["decision"]).inc()
record_action_metrics(action_metric_name, action_result)

audit = {
    "target": target,
    "features": features,
    "candidate_action": decision_result["candidate_action"],
    "final_action": decision_result["final_action"],
    "decision": decision_result["decision"],
    "reason": decision_result["reason"],
    "p_autoscale": decision_result["p_autoscale"],
    "p_restart": decision_result["p_restart"],
    "action_result": action_result,
}

