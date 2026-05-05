# AutoOrch Chapter Acceptance Checklist

Use this checklist before accepting any rewritten thesis chapter. A chapter should not be considered complete until all relevant checks pass.

## Global Checks For Every Chapter

| Check | Pass? | Notes |
| --- | --- | --- |
| Describes the final architecture consistently | TBD | Two binary classifiers plus policy layer |
| Uses locked terminology | TBD | See `CONTRADICTION_BLACKLIST.md` |
| Contains no blacklist phrase as a current implementation claim | TBD | Search after each rewrite |
| Claims are supported by evidence | TBD | Link to evidence folders where possible |
| Avoids broad production generalization | TBD | Use controlled prototype wording |
| Figures and tables have captions and sources | TBD | Source can be "Made by the author" or evidence folder |
| Code snippets are formatted text, not screenshots | TBD | Screenshots should show runtime evidence |
| Limitations connect to future work | TBD | Especially Model-v2, production hardening, notification integration |

## Chapter-Specific Checks

| Chapter | Required checks before acceptance |
| --- | --- |
| Abstract | Mentions controlled local Kubernetes prototype; states two binary models plus policy; does not claim universal production generalization |
| Chapter 1 Introduction | Objectives match final implementation; no single 4-class classifier claim; defines AutoOrch as alert-to-action orchestration |
| Chapter 2 Problem Space | Still supports SME alert fatigue and remediation gap; no unnecessary implementation detail that conflicts with final system |
| Chapter 3 Suggested Solution | Presents design evolution professionally; explains why two binary classifiers and policy layer are safer and more traceable |
| Chapter 4 Requirements | Functional requirements match final runtime; `notify_human` is policy escalation; real Ansible restart/scale are included |
| Chapter 5 Logical Design | Use cases merged into UC-01 with four alternative flows; sequence flows match Alertmanager -> AutoOrch -> Prometheus -> model cascade -> action/policy |
| Chapter 7 Background | ML/autoscaling discussion supports supervised binary classification and safe gating; Spearman/correlation definitions are concise |
| Chapter 8 Implementation | Uses final paths/artifacts; target workload is `controllable-backend`; features and PromQL equations are correct |
| Chapter 10 Evaluation | Includes M6/M7B/M8B/M9/M10 evidence, selected screenshots, result table, correlation/heatmap interpretation, and controlled-scope note |
| Chapter 11 Limitations/Future Work | Includes Model-v2 as future work; limitations are honest and converted into realistic next steps |

## Final Blacklist Search

Before finalizing the thesis, export DOCX text and search for:

- `4-class`
- `multi-class classifier`
- `autoorch_4class_classifier.joblib`
- `notify_human class`
- `14-feature`
- `rate/ratio`
- `percentage`
- `demo-backend`
- `simulated-only`
- `all decision logic resides`
- `no runtime rule branches`

Any remaining hit must either be removed or explicitly framed as historical design evolution.

