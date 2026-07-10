"""
RuleExecutor: deterministic transformation engine.
Each operation is a standalone function with a consistent signature.
Plugins follow the same signature and are registered the same way.
Never calls the LLM. Fully unit-testable.
"""

import logging
import re
from typing import Callable

import pandas as pd

from agentteam.models.structured_outputs import FileValidationRules, TransformationRule

logger = logging.getLogger(__name__)

# -----------------------------
# Operation type
# Every operation — built-in or plugin — must match this signature
# -----------------------------
TransformationFn = Callable[[pd.DataFrame, TransformationRule], pd.DataFrame]


# -----------------------------
# Built-in operations
# Each function: (df, rule) -> df
# -----------------------------


def rename_to_snake_case(df: pd.DataFrame, rule: TransformationRule) -> pd.DataFrame:
    def to_snake(name: str) -> str:
        s = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1_\2", name)
        s = re.sub(r"([a-z\d])([A-Z])", r"\1_\2", s)
        return s.replace(" ", "_").lower()

    for col in rule.columns:
        if col in df.columns:
            new_col = to_snake(col)
            df.rename(columns={col: new_col}, inplace=True)
    return df


def rename_to_camel_case(df: pd.DataFrame, rule: TransformationRule) -> pd.DataFrame:
    def to_camel(name: str) -> str:
        parts = re.split(r"[_\s]+", name)
        return parts[0].lower() + "".join(p.capitalize() for p in parts[1:])

    for col in rule.columns:
        if col in df.columns:
            new_col = to_camel(col)
            df.rename(columns={col: new_col}, inplace=True)
    return df


def coerce_numeric(df: pd.DataFrame, rule: TransformationRule) -> pd.DataFrame:
    for col in rule.columns:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


def coerce_date(df: pd.DataFrame, rule: TransformationRule) -> pd.DataFrame:
    for col in rule.columns:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")
    return df


def fill_missing_mean(df: pd.DataFrame, rule: TransformationRule) -> pd.DataFrame:
    for col in rule.columns:
        if col in df.columns:
            df[col] = df[col].fillna(df[col].mean())
    return df


def fill_missing_mode(df: pd.DataFrame, rule: TransformationRule) -> pd.DataFrame:
    for col in rule.columns:
        if col in df.columns and not df[col].mode().empty:
            df[col] = df[col].fillna(df[col].mode()[0])
    return df


def fill_missing_value(df: pd.DataFrame, rule: TransformationRule) -> pd.DataFrame:
    for col in rule.columns:
        if col in df.columns:
            df[col] = df[col].fillna(rule.fill_value)
    return df


def drop_missing(df: pd.DataFrame, rule: TransformationRule) -> pd.DataFrame:
    target = [c for c in rule.columns if c in df.columns]
    return df.dropna(subset=target)


def drop_duplicates(df: pd.DataFrame, rule: TransformationRule) -> pd.DataFrame:
    return df.drop_duplicates()


# -----------------------------
# RuleExecutor
# -----------------------------


class RuleExecutor:
    """
    Deterministic transformation engine with a function registry.
    Built-in operations and plugins share the same signature:
        fn(df: pd.DataFrame, rule: TransformationRule) -> pd.DataFrame
    Plugins register themselves via RuleExecutor.register().
    """

    _registry: dict[str, TransformationFn] = {
        "rename_to_snake_case": rename_to_snake_case,
        "rename_to_camel_case": rename_to_camel_case,
        "coerce_numeric": coerce_numeric,
        "coerce_date": coerce_date,
        "fill_missing_mean": fill_missing_mean,
        "fill_missing_mode": fill_missing_mode,
        "fill_missing_value": fill_missing_value,
        "drop_missing": drop_missing,
        "drop_duplicates": drop_duplicates,
    }

    @classmethod
    def register(cls, operation: str, fn: TransformationFn) -> None:
        """Register a new operation — built-in or plugin."""
        cls._registry[operation] = fn
        logger.info(f"Registered operation: {operation}")

    @classmethod
    def is_supported(cls, operation: str) -> bool:
        """Check if an operation is registered."""
        return operation in cls._registry

    @classmethod
    def supported_operations(cls) -> list[str]:
        """Return list of all registered operation names."""
        return list(cls._registry.keys())

    @classmethod
    def apply_single(cls, df: pd.DataFrame, rule: TransformationRule) -> pd.DataFrame:
        """Apply a single TransformationRule. Used by ExecutionPlanner."""
        fn = cls._registry.get(rule.operation)
        if fn is None:
            logger.warning(f"No registered function for: {rule.operation}")
            return df
        return fn(df, rule)

    @classmethod
    def apply(cls, df: pd.DataFrame, rules: FileValidationRules) -> pd.DataFrame:
        """
        Apply all registered TransformationRules in order.
        Skips unregistered operations — ExecutionPlanner handles those via plugins.
        """
        for rule in rules.transformations:
            fn = cls._registry.get(rule.operation)
            if fn is None:
                logger.debug(f"Skipping unregistered operation: {rule.operation}")
                continue
            logger.info(
                f"Applying: {rule.operation} on columns: {rule.columns or 'all'}"
            )
            df = fn(df, rule)
        return df
