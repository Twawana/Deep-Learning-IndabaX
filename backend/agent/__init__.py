"""
In Vision agent package — Planner → Executor → Advisor pipeline.

Tools return facts only. Recommendations come only from the Advisor stage.
"""

from agent.pipeline import run_pipeline

__all__ = ["run_pipeline"]
