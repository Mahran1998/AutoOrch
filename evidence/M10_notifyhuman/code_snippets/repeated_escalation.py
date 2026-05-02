def apply_consecutive_escalation(
    *,
    target: Dict[str, Any],
    decision_payload: Dict[str, Any],
) -> Dict[str, Any]:
    candidate_action = decision_payload["candidate_action"]

    if candidate_action not in {"auto_scale", "auto_restart"}:
        return decision_payload

    now = time.time()
    key = f"{_target_key(target)}:{candidate_action}"
    previous = CANDIDATE_STREAK.get(key, {})
    previous_at = float(previous.get("last_seen_at", 0.0))
    within_window = now - previous_at <= SETTINGS.consecutive_memory_seconds
    count = int(previous.get("count", 0)) + 1 if within_window else 1
    CANDIDATE_STREAK[key] = {
        "candidate_action": candidate_action,
        "count": count,
        "last_seen_at": now,
    }

    if count >= SETTINGS.consecutive_escalation_count:
        decision_payload["final_action"] = "notify_human"
        decision_payload["decision"] = "notify_human"
        decision_payload["reason"] = "repeated_action"
        decision_payload["escalation"] = {
            "candidate_action": candidate_action,
            "consecutive_count": count,
            "threshold": SETTINGS.consecutive_escalation_count,
            "memory_seconds": SETTINGS.consecutive_memory_seconds,
            "key": key,
        }

