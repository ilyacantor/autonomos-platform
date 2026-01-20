"""
TDAD (Test-Driven Agent Development) Evaluation Framework

Golden dataset evaluation for agent quality assurance.
Per ARB requirements, this is a Phase 1 deliverable.
"""

from app.agentic.eval.runner import EvalRunner, EvalConfig
from app.agentic.eval.golden_dataset import GOLDEN_DATASET, load_golden_dataset

__all__ = ['EvalRunner', 'EvalConfig', 'GOLDEN_DATASET', 'load_golden_dataset']
