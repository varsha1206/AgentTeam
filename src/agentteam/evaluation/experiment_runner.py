import shutil
import time
import uuid
from pathlib import Path
from typing import Literal

from agentteam.agents.orchestrator_agent import Orchestrator
from agentteam.evaluation.structured_outputs import (
    ExperimentResult,
    GroundTruth,
)
from agentteam.storage.sqlite_store import SQLiteStore

PROJECT_ROOT = Path(__file__).resolve().parents[3]

WORKSPACE_DIR = PROJECT_ROOT / "workspace"
INPUT_DIR = WORKSPACE_DIR / "input"

OUTPUT_DIRS = [
    WORKSPACE_DIR / "output" / "bronze",
    WORKSPACE_DIR / "output" / "silver",
    WORKSPACE_DIR / "output" / "quarantine",
    WORKSPACE_DIR / "temp",
]


Condition = Literal["with_repair", "without_repair"]


def clean_workspace():
    """
    Remove previous experiment artifacts.
    Ensures every run starts from identical state.
    """

    for directory in OUTPUT_DIRS:
        if directory.exists():
            shutil.rmtree(directory)

        directory.mkdir(
            parents=True,
            exist_ok=True,
        )


def copy_dataset(dataset_path: Path):
    """
    Copies test dataset into normal pipeline input location.
    """

    INPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    destination = INPUT_DIR / dataset_path.name

    shutil.copy(
        dataset_path,
        destination,
    )

    return destination


def count_llm_calls() -> int:
    """
    Placeholder.

    Replace with your LangChain callback counter
    or SQLite trace table later.
    """

    return 0


def collect_sqlite_metrics(run_id: str):
    """
    Reads persisted pipeline information.
    """

    store = SQLiteStore()

    silver_rows = store.count_silver_rows(run_id)

    quarantine_rows = store.count_quarantine_rows(run_id)

    repair_attempts = store.count_repairs(run_id)

    return {
        "silver_rows": silver_rows,
        "quarantine_rows": quarantine_rows,
        "repair_attempts": repair_attempts,
    }


def run_pipeline(
    condition: Condition,
):
    """
    Executes the LangGraph pipeline.

    The only difference between experiments:
    repair enabled or disabled.
    """

    enable_repair = condition == "with_repair"

    orchestrator = Orchestrator(enable_repair=enable_repair)

    final_state = orchestrator.run()

    return final_state


def run_experiment(
    dataset_path: Path,
    ground_truth: GroundTruth,
    condition: Condition,
    run_id: str | None = None,
) -> ExperimentResult:
    """
    Executes one experiment.

    Example:

    Dataset 1
        WITH repair

    Dataset 1
        WITHOUT repair

    """

    if run_id is None:
        run_id = str(uuid.uuid4())

    print(f"\nRunning {condition}: {dataset_path.name}")

    clean_workspace()

    copy_dataset(dataset_path)

    start_time = time.perf_counter()

    final_state = run_pipeline(condition)

    execution_time = time.perf_counter() - start_time

    sqlite_metrics = collect_sqlite_metrics(run_id)

    pipeline_success = sqlite_metrics["silver_rows"] > 0

    repair_success = False

    if condition == "with_repair":
        repair_success = pipeline_success and sqlite_metrics["repair_attempts"] > 0

    result = ExperimentResult(
        run_id=run_id,
        condition=condition,
        dataset_name=dataset_path.name,
        ground_truth=ground_truth,
        detection_accuracy=0.0,
        # calculated later in metrics.py
        silver_row_count=sqlite_metrics["silver_rows"],
        quarantine_row_count=sqlite_metrics["quarantine_rows"],
        valid_rows_recovered=0,
        # calculated after comparing conditions
        repair_success=repair_success,
        repair_attempts=sqlite_metrics["repair_attempts"],
        pipeline_success=pipeline_success,
        execution_time_seconds=execution_time,
        llm_calls_made=count_llm_calls(),
        notes=str(final_state.errors) if hasattr(final_state, "errors") else "",
    )

    return result


def run_all_experiments(datasets: list[tuple[Path, GroundTruth]]):
    """
    Runs the complete ablation experiment matrix.

    Current:

    Dataset 1
       - with repair
       - without repair

    Dataset 2
       - with repair
       - without repair

    Dataset 3
       - with repair
       - without repair
    """

    results = []

    conditions = [
        "with_repair",
        "without_repair",
    ]

    for dataset, truth in datasets:
        for condition in conditions:
            result = run_experiment(
                dataset_path=dataset,
                ground_truth=truth,
                condition=condition,
            )

            results.append(result)

    return results
