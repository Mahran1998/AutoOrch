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
```
