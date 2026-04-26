@app.post("/alert")
async def alert_receiver(req: Request) -> Dict[str, Any]:
    ALERTS_RECEIVED.inc()
    payload = await req.json()
    target = extract_target(payload)

    features, restart_context = fetch_signal_bundle(target)
    p_autoscale = autoscale_probability(features)
    p_restart = None
    if p_autoscale is not None and p_autoscale < SETTINGS.autoscale_threshold and RESTART_MODEL_READY:
        p_restart = restart_probability(features)

    decision_result = decide_action(
        features=features,
        context=restart_context,
        p_autoscale=p_autoscale,
        p_restart=p_restart,
        autoscale_threshold=SETTINGS.autoscale_threshold,
        restart_threshold=SETTINGS.restart_threshold,
        alert_status=target["status"],
        autoscale_model_ready=MODEL_READY,
        restart_model_ready=RESTART_MODEL_READY,
    ).to_dict()

    action_result = ACTION_EXECUTOR.execute(
        decision=decision_result["final_action"],
        target=ActionTarget(namespace=target["namespace"], workload=target["workload"]),
        max_replicas=SETTINGS.max_replicas,
    )

    logger.info("AUDIT %s", json.dumps({
        "target": target,
        "features": features,
        "candidate_action": decision_result["candidate_action"],
        "final_action": decision_result["final_action"],
        "reason": decision_result["reason"],
        "action_result": action_result,
    }))
