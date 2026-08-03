"""
experiment_runner.py

Runs the pipeline under controlled conditions and collects observations.
Supports repair_enabled=True (full pipeline) and repair_enabled=False (baseline).
"""

import logging
import shutil
import time
import uuid
from pathlib import Path

import pandas as pd
from langchain_anthropic import ChatAnthropic
from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.outputs import LLMResult

from agentteam.agents.orchestrator_agent import Orchestrator
from agentteam.evaluation.dataset_generator import generate_all
from agentteam.evaluation.metrics import export_results_to_csv
from agentteam.evaluation.structured_outputs import (
    ExperimentConfig,
    ExperimentResult,
    GroundTruth,
)
from agentteam.storage.sqlite_store import SQLiteStore

logger = logging.getLogger("agentteam.evaluation.experiment_runner")


def get_project_root() -> Path:
    return Path(__file__).resolve().parents[3]


# -----------------------------
# LLM call counter
# -----------------------------


class AnthropicCallCounter(BaseCallbackHandler):
    """
    Counts Anthropic API calls and tracks token usage.
    Passed as a callback to ChatAnthropic.
    """

    def __init__(self):
        super().__init__()
        self.total_calls: int = 0
        self.total_input_tokens: int = 0
        self.total_output_tokens: int = 0

    def on_llm_start(self, serialized: dict, prompts: list, **kwargs) -> None:
        self.total_calls += 1

    def on_llm_end(self, response: LLMResult, **kwargs) -> None:
        try:
            info = response.generations[0][0].generation_info or {}
            usage = info.get("usage", {})
            self.total_input_tokens += usage.get("input_tokens", 0)
            self.total_output_tokens += usage.get("output_tokens", 0)
        except (IndexError, AttributeError, KeyError):
            pass

    def reset(self) -> None:
        self.total_calls = 0
        self.total_input_tokens = 0
        self.total_output_tokens = 0

    def summary(self) -> dict:
        return {
            "total_calls": self.total_calls,
            "total_input_tokens": self.total_input_tokens,
            "total_output_tokens": self.total_output_tokens,
        }


# -----------------------------
# Workspace preparation
# -----------------------------


def prepare_workspace(workspace_path: Path) -> None:
    """
    Clears all run artifacts from workspace.
    Preserves plugins/ — plugins are cached across runs intentionally.
    Preserves agentteam.db — SQLite accumulates results across runs.
    """
    dirs_to_clear = [
        workspace_path / "input",
        workspace_path / "output" / "bronze",
        workspace_path / "output" / "silver",
        workspace_path / "output" / "quarantine",
        workspace_path / "temp",
        workspace_path / "generated",
    ]

    for directory in dirs_to_clear:
        if directory.exists():
            for f in directory.glob("*"):
                if f.is_file():
                    f.unlink()

    logs_dir = workspace_path / "logs"
    if logs_dir.exists():
        for f in logs_dir.glob("*"):
            if f.is_file() and f.suffix != ".db":
                f.unlink()

    logger.info("Workspace prepared — artifacts cleared, plugins preserved")


# -----------------------------
# Metric helpers
# -----------------------------


def _count_silver_rows(silver_layer: list[str]) -> int:
    """Count total rows across all silver CSV files."""
    total = 0
    for path_str in silver_layer:
        path = Path(path_str)
        if path.exists():
            try:
                total += len(pd.read_csv(path, encoding="utf-8"))
            except Exception as e:
                logger.warning(f"Could not read silver file {path}: {e}")
    return total


def _count_quarantine_rows(quarantine_dir: Path) -> int:
    """Count total rows across all quarantine CSV files."""
    total = 0
    for path in quarantine_dir.glob("*.csv"):
        try:
            total += len(pd.read_csv(path, encoding="utf-8"))
        except Exception as e:
            logger.warning(f"Could not read quarantine file {path}: {e}")
    return total


def _compute_detection_accuracy(
    quarantine_row_count: int,
    expected_quarantine_rows: int,
) -> float:
    """
    Compute detection accuracy as quarantined / expected.
    Handles edge cases for clean datasets.
    """
    if expected_quarantine_rows == 0:
        return 1.0 if quarantine_row_count == 0 else 0.0
    return min(quarantine_row_count / expected_quarantine_rows, 1.0)


# -----------------------------
# Core experiment runner
# -----------------------------


def run_experiment(
    ground_truth: GroundTruth,
    config: ExperimentConfig,
    workspace_path: Path,
    run_id: str,
) -> ExperimentResult:
    """
    Runs one pipeline experiment under the given configuration.
    Returns structured ExperimentResult with all metrics populated.
    """
    logger.info(f"Running experiment: {config.experiment_name}")

    try:
        prepare_workspace(workspace_path)

        # copy dataset to workspace/input/
        source = (
            Path(__file__).parent
            / "datasets"
            / ("clean" if ground_truth.dataset_name == "clean" else "broken")
            / ground_truth.filename
        )
        dest = workspace_path / "input" / ground_truth.filename

        if not source.exists():
            raise FileNotFoundError(f"Dataset not found: {source}")
        shutil.copy2(source, dest)
        logger.info(f"Dataset copied to input: {ground_truth.filename}")

        # build LLM with call counter
        counter = AnthropicCallCounter()
        llm = ChatAnthropic(
            model_name="claude-haiku-4-5-20251001",
            timeout=60,
            stop=["end of response"],
            callbacks=[counter],
            model_kwargs={
                "extra_headers": {"anthropic-beta": "prompt-caching-2024-07-31"}
            },
        )

        orchestrator = Orchestrator(
            workspace=workspace_path,
            llm_model=llm,
            repair_enabled=config.repair_enabled,
        )

        initial_state = {
            "messages": [
                {
                    "role": "user",
                    "content": (
                        "Retrieve the dataset from the input folder. "
                        "Read all available files, summarise their contents, "
                        "and write the raw data to the output folder."
                    ),
                }
            ],
            "raw_input": str(workspace_path / "input" / ground_truth.filename),
            "workspace_path": workspace_path,
            "execution_plan": [],
            "final_output": None,
            "retrieved_data": {},
            "validated_data": {},
            "repaired_data": {},
            "bronze_layer": [],
            "silver_layer": [],
            "quarantine_layer": [],
            "repair_target": None,
            "repair_error": None,
            "repair_script_path": None,
            "repair_attempts": 0,
            "errors": [],
            "artifacts": {},
            "metadata": {"run_id": run_id, "environment": "evaluation"},
        }

        start_time = time.perf_counter()
        final_state = {}
        for chunk in orchestrator.stream(initial_state, thread_id=run_id):
            final_state = chunk
        end_time = time.perf_counter()

        execution_time = round(end_time - start_time, 2)

        silver_layer = final_state.get("silver_layer", [])
        quarantine_dir = workspace_path / "output" / "quarantine"
        repaired_data = final_state.get("repaired_data", {})

        silver_row_count = _count_silver_rows(silver_layer)
        quarantine_row_count = _count_quarantine_rows(quarantine_dir)
        repair_attempts = final_state.get("repair_attempts", 0)
        repair_success = (
            repaired_data.get("status") == "complete" if repaired_data else False
        )
        pipeline_success = silver_row_count > 0
        detection_accuracy = _compute_detection_accuracy(
            quarantine_row_count, ground_truth.expected_quarantine_rows
        )

        # persist to SQLite
        store = SQLiteStore(
            db_path=workspace_path / "agentteam.db",
            llm=llm,
        )
        store.persist_run(
            run_id=run_id,
            started_at=initial_state["metadata"].get("run_id", run_id),
            status="complete" if pipeline_success else "failed",
            files_processed=len(final_state.get("bronze_layer", [])),
            repair_attempts=repair_attempts,
        )
        for silver_path in silver_layer:
            p = Path(silver_path)
            store.persist_silver(run_id, p.name, p)
        for quarantine_file in quarantine_dir.glob("*.csv"):
            store.persist_quarantine(run_id, quarantine_file.name, quarantine_file)
        if repaired_data and repaired_data.get("repair_target"):
            store.persist_repair(
                run_id=run_id,
                repair_target=repaired_data.get("repair_target", "unknown"),
                attempt_number=repair_attempts,
                success=repair_success,
                error_description=str(repaired_data.get("errors", [])),
            )

        result = ExperimentResult(
            run_id=run_id,
            config=config,
            ground_truth=ground_truth,
            detection_accuracy=detection_accuracy,
            repair_success=repair_success,
            repair_attempts=repair_attempts,
            pipeline_success=pipeline_success,
            execution_time_seconds=execution_time,
            llm_calls_made=counter.total_calls,
            silver_row_count=silver_row_count,
            quarantine_row_count=quarantine_row_count,
            notes="",
        )

        logger.info(
            f"Experiment complete: {config.experiment_name} — "
            f"silver: {silver_row_count}, quarantine: {quarantine_row_count}, "
            f"repair attempts: {repair_attempts}, "
            f"detection accuracy: {detection_accuracy:.2f}, "
            f"time: {execution_time}s, llm calls: {counter.total_calls}"
        )

        return result

    except Exception as e:
        logger.error(f"Experiment failed: {config.experiment_name} — {e}")
        return ExperimentResult(
            run_id=run_id,
            config=config,
            ground_truth=ground_truth,
            detection_accuracy=0.0,
            repair_success=False,
            repair_attempts=0,
            pipeline_success=False,
            execution_time_seconds=0.0,
            llm_calls_made=0,
            silver_row_count=0,
            quarantine_row_count=0,
            notes=str(e),
        )


# -----------------------------
# Run all experiments
# -----------------------------


def run_all_experiments(workspace_path: Path) -> list[ExperimentResult]:
    """
    Runs all evaluation datasets under both conditions.
    Returns list of ExperimentResult — one per run.
    """

    ground_truths = generate_all()
    results = []

    for name, gt in ground_truths.items():
        for repair_enabled in [True, False]:
            condition_label = "with_repair" if repair_enabled else "without_repair"
            run_id = str(uuid.uuid4())
            config = ExperimentConfig(
                experiment_name=f"{gt.dataset_name}_{condition_label}",
                repair_enabled=repair_enabled,
            )
            try:
                result = run_experiment(
                    ground_truth=gt,
                    config=config,
                    workspace_path=workspace_path,
                    run_id=run_id,
                )
                logger.info(
                    f"Experiment result: {result.config.experiment_name} — "
                    f"silver: {result.silver_row_count}, "
                    f"quarantine: {result.quarantine_row_count}, "
                    f"detection accuracy: {result.detection_accuracy:.2f}, "
                    f"repair attempts: {result.repair_attempts}, "
                    f"repair success: {result.repair_success}, "
                    f"time: {result.execution_time_seconds}s, "
                    f"llm calls: {result.llm_calls_made}"
                )
                results.append(result)
            except Exception as e:
                logger.error("Experiment failed: %s — %s", config.experiment_name, e)

    results_dir = get_project_root() / "results"
    results_dir.mkdir(exist_ok=True)
    export_results_to_csv(results, results_dir / "experiment_results.csv")

    return results


if __name__ == "__main__":
    workspace = get_project_root() / "workspace"
    all_results = run_all_experiments(workspace)
    logger.info(f"All experiments complete — {len(all_results)} runs")
