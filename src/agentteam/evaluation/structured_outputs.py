"""
Structured outputs used by the evaluation framework.
"""

from typing import Literal

from pydantic import BaseModel, Field


class InjectedError(BaseModel):
    """Represents one deliberately injected error in a dataset."""

    row: int = Field(description="Zero-based row index.")
    column: str = Field(description="Column containing the injected error.")
    error_type: Literal[
        "type_mismatch",
        "missing_value",
        "range_violation",
        "duplicate",
        "script_failure",
    ] = Field(description="Category of injected error.")


class GroundTruth(BaseModel):
    """Ground truth for a generated evaluation dataset."""

    dataset_name: str
    filename: str

    total_rows: int

    injected_errors: list[InjectedError]

    expected_quarantine_rows: int = Field(
        description="Rows expected to end up in quarantine."
    )


class ExperimentConfig(BaseModel):
    """Configuration for one experiment run."""

    experiment_name: str

    repair_enabled: bool = True

    plugin_cache_enabled: bool = True

    llm_rule_inference_enabled: bool = True


class ExperimentResult(BaseModel):
    """Results collected from one pipeline execution."""

    run_id: str

    config: ExperimentConfig

    ground_truth: GroundTruth

    detection_accuracy: float

    repair_success: bool

    repair_attempts: int

    pipeline_success: bool

    execution_time_seconds: float

    llm_calls_made: int

    silver_row_count: int

    quarantine_row_count: int

    notes: str = ""
