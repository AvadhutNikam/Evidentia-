"""
backend/ach_scoring.py
================================================================================
EVIDENTIA AI - BACKWARDS-COMPATIBILITY RE-EXPORT FACADE
================================================================================
All scoring functionality has been modularized into:
- backend/scoring/evidence_scoring.py: ACH matrix, likelihood ratios, diagnosticity
- backend/scoring/background.py: suspect prior records, M.O. similarity, bias insulation
- backend/scoring/bayesian.py: Bayesian updating, LR multiplication, 3-layer synthesis
- backend/scoring/sensitivity.py: Leave-One-Out (LOO) robustness and Monte Carlo ranges
- backend/scoring/gaps.py: investigative gap detection, missing evidence simulations
- backend/scoring/history.py: historical score versioning and delta tracking
"""

from scoring import *
from scoring import __all__ as _scoring_all

__all__ = _scoring_all
