def decide_action(
    *,
    p_autoscale,
    p_restart,
    autoscale_threshold,
    restart_threshold,
    restart_model_ready=True,
):
    if p_autoscale is not None and p_autoscale >= autoscale_threshold:
        return {
            "candidate_action": "auto_scale",
            "final_action": "auto_scale",
            "reason": "autoscale_confident",
        }

    if not restart_model_ready:
        return {
            "candidate_action": "no_action",
            "final_action": "no_action",
            "reason": "below_threshold_or_restart_model_unavailable",
        }

    if p_restart is not None and p_restart >= restart_threshold:
        return {
            "candidate_action": "auto_restart",
            "final_action": "auto_restart",
            "reason": "restart_confident",
        }

    return {
        "candidate_action": "no_action",
        "final_action": "no_action",
        "reason": "below_threshold",
    }
