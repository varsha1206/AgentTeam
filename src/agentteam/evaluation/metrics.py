"""
metrics.py

Exports experiment results and generates analysis tables for the thesis.
"""

from pathlib import Path

import pandas as pd

from agentteam.evaluation.structured_outputs import ExperimentResult

# ---------------------------------------------------
# Helpers
# ---------------------------------------------------


def _to_dataframe(results: list[ExperimentResult]) -> pd.DataFrame:
    """
    Converts ExperimentResult models into a flat dataframe.
    """

    rows = []

    for r in results:
        rows.append(
            {
                "run_id": r.run_id,
                "dataset": r.ground_truth.dataset_name,
                "condition": (
                    "with_repair" if r.config.repair_enabled else "without_repair"
                ),
                "detection_accuracy": r.detection_accuracy,
                "repair_success": r.repair_success,
                "repair_attempts": r.repair_attempts,
                "pipeline_success": r.pipeline_success,
                "execution_time_seconds": r.execution_time_seconds,
                "llm_calls_made": r.llm_calls_made,
                "silver_row_count": r.silver_row_count,
                "quarantine_row_count": r.quarantine_row_count,
                "notes": r.notes,
            }
        )

    return pd.DataFrame(rows)


# ---------------------------------------------------
# Main CSV
# ---------------------------------------------------


def export_results_to_csv(
    results: list[ExperimentResult],
    output_path: Path,
) -> None:

    df = _to_dataframe(results)

    output_path.parent.mkdir(parents=True, exist_ok=True)

    df.to_csv(
        output_path,
        index=False,
    )


# ---------------------------------------------------
# RQ1
# ---------------------------------------------------


def export_detection_accuracy(
    results: list[ExperimentResult],
    output_path: Path,
):

    df = _to_dataframe(results)

    df[
        [
            "dataset",
            "condition",
            "detection_accuracy",
            "quarantine_row_count",
        ]
    ].to_csv(
        output_path,
        index=False,
    )


# ---------------------------------------------------
# RQ2
# ---------------------------------------------------


def export_repair_metrics(
    results: list[ExperimentResult],
    output_path: Path,
):

    df = _to_dataframe(results)

    repair = df[df["condition"] == "with_repair"][
        [
            "dataset",
            "repair_success",
            "repair_attempts",
            "execution_time_seconds",
            "llm_calls_made",
        ]
    ]

    repair.to_csv(
        output_path,
        index=False,
    )


# ---------------------------------------------------
# RQ3
# ---------------------------------------------------


def compute_valid_rows_recovered(
    results: list[ExperimentResult],
) -> pd.DataFrame:
    """
    Compares repaired vs baseline runs.

    recovered_rows =
        silver(with repair)
        -
        silver(without repair)
    """

    df = _to_dataframe(results)

    with_repair = df[df.condition == "with_repair"].set_index("dataset")

    without_repair = df[df.condition == "without_repair"].set_index("dataset")

    comparison = pd.DataFrame()

    comparison["dataset"] = with_repair.index

    comparison["silver_with_repair"] = with_repair["silver_row_count"].values

    comparison["silver_without_repair"] = without_repair["silver_row_count"].values

    comparison["valid_rows_recovered"] = (
        comparison["silver_with_repair"] - comparison["silver_without_repair"]
    )

    comparison["pipeline_success_with"] = with_repair["pipeline_success"].values

    comparison["pipeline_success_without"] = without_repair["pipeline_success"].values

    return comparison


def export_pipeline_metrics(
    results: list[ExperimentResult],
    output_path: Path,
):

    comparison = compute_valid_rows_recovered(results)

    comparison.to_csv(
        output_path,
        index=False,
    )


# ---------------------------------------------------
# Human-readable table
# ---------------------------------------------------


def create_comparison_table(
    results: list[ExperimentResult],
    output_path: Path,
):

    df = _to_dataframe(results)

    summary = (
        df.groupby("condition")
        .agg(
            detection_accuracy=("detection_accuracy", "mean"),
            repair_success=("repair_success", "mean"),
            pipeline_success=("pipeline_success", "mean"),
            execution_time=("execution_time_seconds", "mean"),
            llm_calls=("llm_calls_made", "mean"),
        )
        .round(2)
    )

    output_path.write_text(summary.to_string())


# ---------------------------------------------------
# Overall summary
# ---------------------------------------------------


def summarize_results(
    results: list[ExperimentResult],
) -> pd.DataFrame:

    df = _to_dataframe(results)

    return (
        df.groupby("condition")
        .agg(
            runs=("run_id", "count"),
            detection_accuracy=("detection_accuracy", "mean"),
            repair_success=("repair_success", "mean"),
            pipeline_success=("pipeline_success", "mean"),
            avg_execution_time=("execution_time_seconds", "mean"),
            avg_llm_calls=("llm_calls_made", "mean"),
        )
        .round(2)
    )
