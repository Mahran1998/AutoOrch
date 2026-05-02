```python
if p_autoscale is not None and p_autoscale >= autoscale_threshold:
    return DecisionResult(
        candidate_action="auto_scale",
        final_action="auto_scale",
        reason="autoscale_confident",
        p_autoscale=p_autoscale,
        p_restart=p_restart,
        signals=signals,
    )

if p_restart is not None and p_restart >= restart_threshold:
    return DecisionResult(
        candidate_action="auto_restart",
        final_action="auto_restart",
        reason="restart_confident",
        p_autoscale=p_autoscale,
        p_restart=p_restart,
        signals=signals,
    )

return DecisionResult(
    candidate_action="no_action",
    final_action="no_action",
    reason="below_threshold",
    p_autoscale=p_autoscale,
    p_restart=p_restart,
    signals=signals,
)
```
