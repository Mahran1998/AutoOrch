from __future__ import annotations
from typing import Dict, List

FEATURES: List[str] = ["rps", "p95", "http_5xx_rate", "cpu_sat"]

def vector_from_row(row: Dict[str, float]) -> List[float]:
    return [float(row[name]) for name in FEATURES]
