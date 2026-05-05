# Correlation Analysis Summary

## Scope

This package analyzes only the existing AutoOrch datasets:

- `experiments/dataset_autoscale.csv`
- `experiments/dataset_restart.csv`

No new experiments were run, no models were retrained, and no runtime code was changed.

## Dataset Sizes And Labels

| Dataset | Rows | Label column | Label counts | Feature columns used |
| --- | ---: | --- | --- | --- |
| Autoscale | 624 | `action_label` | no_action=337, auto_scale=287 | `rps`, `p95`, `http_5xx_rate`, `cpu_sat` |
| Restart | 49 | `label` | no_action=33, auto_restart=16 | `rps`, `p95`, `http_5xx_rate`, `cpu_sat` |

## Generated Outputs

- `autoscale_pearson_correlation.csv`
- `autoscale_spearman_correlation.csv`
- `autoscale_spearman_pvalues.csv`
- `restart_pearson_correlation.csv`
- `restart_spearman_correlation.csv`
- `restart_spearman_pvalues.csv`
- `autoscale_correlation_heatmap.png`
- `restart_correlation_heatmap.png`

Spearman p-values were generated with SciPy. Some p-values are `NaN` where a feature is constant, such as `http_5xx_rate` in the autoscale dataset.

## Pearson Interpretation

In the autoscale dataset, the Pearson correlation between `rps` and `cpu_sat` is 0.987. This supports the AutoScale evidence story: under controlled load, request pressure and CPU saturation rise together.

In the restart dataset, the Pearson correlation between `p95` and `http_5xx_rate` is 1.000. This supports the AutoRestart evidence story: the injected restart-like condition produced high latency and high 5xx requests per second together.

## Spearman Interpretation

In the autoscale dataset, the Spearman correlation between `rps` and `cpu_sat` is 0.946. This indicates a strong monotonic relationship between request pressure and CPU saturation in the controlled autoscale data.

In the restart dataset, the Spearman correlation between `p95` and `http_5xx_rate` is 0.848. This indicates that higher latency windows also tend to be higher 5xx-request windows in the controlled restart dataset.

## Thesis Use

Use the heatmaps and correlation tables as descriptive support in the evaluation/results chapter. The autoscale analysis has stronger descriptive support because it uses 624 rows. The restart analysis is useful but more limited because it uses 49 rows.

## Limitation

Correlation analysis is descriptive and does not prove causal relationships or production generalization. The restart dataset is small, so restart correlations should be described as supportive evidence from a controlled prototype experiment, not as statistically broad incident behavior.
