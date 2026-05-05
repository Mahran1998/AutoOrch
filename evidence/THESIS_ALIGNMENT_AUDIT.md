# AutoOrch Thesis Alignment Audit

This audit identifies sections in the current thesis draft that must be aligned with the final implemented AutoOrch architecture. Thesis-facing wording should frame these changes as **Design evolution and final implementation choices**, not as mistakes.

Current inspected draft:

```text
Marhran_0302REV_CORR_UPDATED_v2_FINAL CORR (AutoRecovered).docx
```

## High-Priority Alignment Issues

| Topic | Exact locations found | Current issue | Required final wording | Evidence source | Priority |
| --- | --- | --- | --- | --- | --- |
| 4-class classifier | paragraphs 153, 375, 490, 503, 555, 614, 616 | Thesis states or implies a single 4-class/multi-class classifier as current runtime | AutoOrch uses two binary classifiers: autoscale first, restart second, plus policy layer | `webhook/models/*_meta.json`, `evidence/THESIS_RESULTS_SUMMARY.md` | High |
| NotifyHuman as ML class | paragraphs 153, 375, 490, 579; also wording around 149, 202, 645, 664 | `notify_human` appears as a learned class/action class in runtime model | `notify_human` is a policy escalation outcome for repeated/unsafe/uncertain cases | `evidence/M10_notifyhuman/summary.md` | High |
| `http_5xx_rate` definition | paragraph 611; clarify 452, 819, 891 | Wording says or suggests rate/ratio/percentage | `http_5xx_rate` means 5xx requests per second | `experiments/dataset_restart.csv`, PromQL outputs | High |
| Final target workload | paragraphs 105, 462, 551, 572, 598, 599, 683, 747, 797, 802, 803, 812 | Final evaluation target is described as `demo-backend` | Final evaluation target is `controllable-backend`; `demo-backend` may appear only as historical or unrelated local resource | M7B/M8B/M9/M10 evidence folders | High |
| Decision logic | paragraph 620 | Thesis says all decision logic resides in the trained model and no runtime rule branches exist | Runtime uses model cascade plus safety policy: scope checks, confidence threshold, repeated-candidate escalation, safe fallback | `webhook/main.py`, M10 evidence | High |
| Old artifact name | paragraph 616 | Mentions `autoorch_4class_classifier.joblib` | Use `autoscale_classifier.joblib` and `restart_classifier.joblib` | `webhook/models/` | High |
| 14-feature runtime | no direct hit found | No direct contradiction found in current text extraction | Keep checking after rewrites; runtime vector is four features | `evidence/CONTRADICTION_BLACKLIST.md` | Low |

## Chapter-Level Rewrite Guidance

| Chapter/Section | Required update | Evidence / source |
| --- | --- | --- |
| Abstract | Mention controlled local Kubernetes prototype; two binary models plus policy; real restart and scale actions; no universal production claim | `evidence/THESIS_RESULTS_SUMMARY.md` |
| 1.2 Objectives and scope | Replace single multi-class objective with cascaded binary models and safety policy; describe `notify_human` as escalation | Model metadata, M10 |
| 3.2 High-level architecture | Rewrite decision engine as model cascade plus policy layer | M6, M7B, M8B, M9, M10 |
| 4.1 Functional requirements | Replace 4-class classifier requirements; update AutoRestart and NotifyHuman requirements | M7B, M10 |
| 4.4 Specification list | Replace single classifier spec with autoscale/restart binary model loading and confidence threshold | `webhook/models/*_meta.json` |
| 5.1 Assumptions | Replace `demo-backend` and 4-class assumptions; use `controllable-backend` and four features | M7B/M8B evidence |
| 5.2 Decision engine | Describe autoscale classifier, restart classifier, and policy escalation | code snippets and model metadata |
| 5.5 Use cases | Merge as UC-01 with four alternative flows | `evidence/README.md` |
| 5.6 Sequence flows | Update flows to show Alertmanager -> AutoOrch -> Prometheus -> model cascade -> action/policy | M6 evidence |
| 5.7 Decision logic summary | Replace all-in-one model wording with final cascade and policy | M9/M10 evidence |
| 8.1 Target workload | Replace `demo-backend` with `controllable-backend` | screenshots and evidence folders |
| 8.2 Feature extraction | Add equations for `rps`, `p95`, `http_5xx_rate`, `cpu_sat`; clarify req/s | PromQL snippets |
| 8.3 ML pipeline | Describe autoscale and restart datasets/models separately | `experiments/dataset_*.csv`, model metadata |
| 8.4 Ansible playbooks | State real restart and scale runbooks were executed in M7B/M8B | M7B/M8B logs |
| 8.5 Audit/metrics | Include `p_autoscale`, `p_restart`, final action, action result, notify metric | M9/M10 logs |
| 10 Results | Add final scenario table, screenshots, and correlation heatmaps | M11 and correlation package |
| 11 Limitations/future work | Add Model-v2, larger datasets, production validation, real notification integration | controlled-scope notes |

## Thesis-Facing Design Evolution Wording

Use wording like this:

> During implementation, the initial broad multi-class decision concept was refined into two specialized binary classifiers and a policy layer. This final design made the prototype easier to validate, safer to operate, and more transparent in the evidence phase. The autoscale classifier handles CPU/load-driven scale decisions, the restart classifier handles application-failure restart decisions, and policy rules handle no-action and notify-human outcomes.

