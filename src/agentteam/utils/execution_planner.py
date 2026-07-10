"""
ExecutionPlanner: inspects FileValidationRules and produces an ordered
execution plan combining deterministic RuleExecutor operations and plugins.
For unknown operations, signals that a plugin needs to be generated.
Never calls the LLM directly.
"""

import logging
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

import pandas as pd

from agentteam.models.structured_outputs import FileValidationRules, TransformationRule
from agentteam.utils.plugin_registry import PluginRegistry
from agentteam.utils.rule_executor import RuleExecutor

logger = logging.getLogger(__name__)


class ExecutionType(str, Enum):
    BUILT_IN = "built_in"
    PLUGIN = "plugin"
    NEEDS_GENERATION = "needs_generation"


@dataclass
class ExecutionStep:
    """A single step in the execution plan."""

    rule: TransformationRule
    execution_type: ExecutionType
    plugin_path: Path | None = None


@dataclass
class ExecutionPlan:
    """
    Ordered list of steps to execute against a DataFrame.
    Steps are either built-in, plugin, or need LLM generation.
    """

    steps: list[ExecutionStep]

    @property
    def ready_steps(self) -> list[ExecutionStep]:
        """Steps that can be executed immediately."""
        return [
            s
            for s in self.steps
            if s.execution_type in (ExecutionType.BUILT_IN, ExecutionType.PLUGIN)
        ]

    @property
    def pending_steps(self) -> list[ExecutionStep]:
        """Steps that need a plugin generated before execution."""
        return [
            s for s in self.steps if s.execution_type == ExecutionType.NEEDS_GENERATION
        ]

    @property
    def is_fully_ready(self) -> bool:
        """True if all steps can be executed without LLM generation."""
        return len(self.pending_steps) == 0

    def summary(self) -> dict:
        """Return a summary dict for logging and reporting."""
        return {
            "total_steps": len(self.steps),
            "built_in": sum(
                1 for s in self.steps if s.execution_type == ExecutionType.BUILT_IN
            ),
            "plugin": sum(
                1 for s in self.steps if s.execution_type == ExecutionType.PLUGIN
            ),
            "needs_generation": len(self.pending_steps),
            "operations": [s.rule.operation for s in self.steps],
            "pending_operations": [s.rule.operation for s in self.pending_steps],
        }


class ExecutionPlanner:
    """
    Inspects FileValidationRules and produces an ExecutionPlan.
    Classifies each TransformationRule as built-in, plugin, or needs generation.
    Does not execute anything — only plans.
    """

    def __init__(self, plugin_registry: PluginRegistry):
        self.registry = plugin_registry

    def plan(self, rules: FileValidationRules) -> ExecutionPlan:
        """
        Produce an ordered ExecutionPlan from FileValidationRules.transformations.
        """
        steps = []

        for rule in rules.transformations:
            step = self._classify(rule)
            steps.append(step)
            logger.debug(f"Planned: {rule.operation} → {step.execution_type.value}")

        plan = ExecutionPlan(steps=steps)
        logger.info(f"Execution plan: {plan.summary()}")
        return plan

    def execute(self, df: pd.DataFrame, plan: ExecutionPlan) -> pd.DataFrame:
        """
        Execute all ready steps in order against a DataFrame.
        Skips pending steps — those must be generated and registered first.
        Returns transformed DataFrame.
        """
        for step in plan.steps:
            if step.execution_type == ExecutionType.NEEDS_GENERATION:
                logger.warning(f"Skipping ungenerated operation: {step.rule.operation}")
                continue
            logger.info(
                f"Executing: {step.rule.operation} "
                f"({step.execution_type.value}) "
                f"on columns: {step.rule.columns}"
            )
            df = RuleExecutor.apply_single(df, step.rule)

        return df

    def register_plugin(self, operation: str, code: str) -> bool:
        """
        Save and register a generated plugin, then update the plan.
        Returns True if registration succeeded.
        """
        path = self.registry.save(operation, code)
        return path.exists()

    # -----------------------------
    # Internals
    # -----------------------------

    def _classify(self, rule: TransformationRule) -> ExecutionStep:
        """Classify a single TransformationRule into an ExecutionStep."""
        if RuleExecutor.is_supported(rule.operation):
            return ExecutionStep(
                rule=rule,
                execution_type=ExecutionType.BUILT_IN,
            )

        if self.registry.exists(rule.operation):
            plugin_path = self.registry._plugin_path(rule.operation)
            self.registry.load(rule.operation)
            return ExecutionStep(
                rule=rule,
                execution_type=ExecutionType.PLUGIN,
                plugin_path=plugin_path,
            )

        return ExecutionStep(
            rule=rule,
            execution_type=ExecutionType.NEEDS_GENERATION,
        )
