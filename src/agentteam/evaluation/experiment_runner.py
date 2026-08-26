"""
experiment_runner.py

Runs the pipeline under controlled conditions and collects observations,
split into batches aligned with the thesis research questions and one
supplementary consistency check:

  - Detection batch    (RQ1): clean runs per dataset, no injected failures.
  - Repair batch       (RQ2, RQ4): repair-enabled runs across failure types.
  - Ablation batch     (RQ3): repair enabled vs. disabled, same failures.
  - Consistency batch  (supplementary): real-world files run twice each,
    no ground truth, no injected failure — measures run-to-run variance
    in outcome rather than correctness against a known error set.

Each batch writes to its own CSV with only the fields relevant to it.

Interactive mode: prints the full experiment plan, lets you pick a
starting index, and asks for confirmation before each individual run
so token usage can be checked between calls.
"""

import csv
import logging
import shutil
import sys
import time
import uuid
from dataclasses import dataclass
from pathlib import Path

import colorlog
import pandas as pd
from langchain_anthropic import ChatAnthropic
from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.outputs import LLMResult

from agentteam.agents.orchestrator_agent import Orchestrator
from agentteam.evaluation.dataset_generator import generate_all
from agentteam.evaluation.structured_outputs import (
    ExperimentConfig,
    ExperimentResult,
    GroundTruth,
)
from agentteam.evaluation.test_injection import clear_injection, set_injection
from agentteam.storage.sqlite_store import SQLiteStore


def get_project_root() -> Path:
    """
    Returns project root (AgentTeam/).
    src/agentteam/main.py -> goes up 3 levels
    """
    return Path(__file__).resolve().parents[3]


def setup_logging():
    workspace = get_project_root() / "workspace"
    logs_dir = workspace / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)

    log_file = logs_dir / "execution.log"

    # overwrite log on every run
    file_handler = logging.FileHandler(
        log_file,
        mode="w",
        encoding="utf-8",
    )
    file_handler.setFormatter(
        logging.Formatter(
            "%(asctime)s %(levelname)-8s %(name)s: %(message)s",
            datefmt="%H:%M:%S",
        )
    )

    console_handler = colorlog.StreamHandler()
    console_handler.setFormatter(
        colorlog.ColoredFormatter(
            "%(log_color)s%(asctime)s %(levelname)-8s %(name)s: %(message)s%(reset)s",
            datefmt="%H:%M:%S",
            log_colors={
                "DEBUG": "cyan",
                "INFO": "green",
                "WARNING": "yellow",
                "ERROR": "red",
                "CRITICAL": "bold_red",
            },
        )
    )

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.handlers.clear()
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)

    # quiet down noisy libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("anthropic").setLevel(logging.WARNING)


setup_logging()
logger = logging.getLogger(__name__)

FAILURE_TYPES = ["syntax_error", "import_error", "runtime_type_error"]

# Real-world files for the supplementary consistency batch.
# Each is run twice, unmodified, with repair enabled and no injected failure.
# total_rows is only used for reporting context in the CSV — it does not
# feed into any accuracy calculation, since these datasets have no ground truth.
REAL_WORLD_DATASETS = [
    {"filename": "italy_earthquakes.csv", "source_format": "csv", "total_rows": 8046},
    {"filename": "aw_fb_data.csv", "source_format": "csv", "total_rows": 6264},
    {
        "filename": "life_expectancy_by_country.json",
        "source_format": "json",
        "total_rows": None,
    },
    {
        "filename": "top_coffee_producing_countries.json",
        "source_format": "json",
        "total_rows": None,
    },
]


def load_real_world_ground_truths() -> list[GroundTruth]:
    """
    Builds GroundTruth entries for the real-world consistency batch.
    No injected errors, no expected_quarantine_rows — these datasets are
    used to measure run-to-run consistency, not detection accuracy.
    """
    ground_truths = []
    for entry in REAL_WORLD_DATASETS:
        ground_truths.append(
            GroundTruth(
                dataset_name=Path(entry["filename"]).stem,
                filename=entry["filename"],
                dataset_category="real_world",
                source_format=entry["source_format"],
                total_rows=entry["total_rows"] or 0,
                injected_errors=[],
                expected_quarantine_rows=None,
            )
        )
    return ground_truths


# -----------------------------
# LLM call counter
# -----------------------------


class AnthropicCallCounter(BaseCallbackHandler):
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
    dirs_to_clear = [
        workspace_path / "input",
        workspace_path / "output" / "bronze",
        workspace_path / "output" / "silver",
        workspace_path / "output" / "quarantine",
        workspace_path / "temp",
        workspace_path / "staged_input",
        workspace_path / "generated",
    ]
    for directory in dirs_to_clear:
        directory.mkdir(parents=True, exist_ok=True)
        for f in directory.glob("*"):
            if f.is_file():
                f.unlink()

    logs_dir = workspace_path / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    for f in logs_dir.glob("*"):
        if f.is_file() and f.suffix != ".db" and f.name != "execution.log":
            f.unlink()

    clear_injection(workspace_path)
    logger.info("Workspace prepared — artifacts cleared, plugins preserved")


# -----------------------------
# Metric helpers
# -----------------------------


def _count_silver_rows(silver_layer: list[str]) -> int:
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
    total = 0
    for path in quarantine_dir.glob("*.csv"):
        try:
            total += len(pd.read_csv(path, encoding="utf-8"))
        except Exception as e:
            logger.warning(f"Could not read quarantine file {path}: {e}")
    return total


def _compute_detection_accuracy(
    quarantine_row_count: int, expected_quarantine_rows: int | None
) -> float | None:
    if expected_quarantine_rows is None:
        return None
    if expected_quarantine_rows == 0:
        return 1.0 if quarantine_row_count == 0 else 0.0
    return min(quarantine_row_count / expected_quarantine_rows, 1.0)


# -----------------------------
# CSV writers — one schema per research question
# -----------------------------


def _append_row(csv_path: Path, row: dict) -> None:
    write_header = not csv_path.exists()
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with open(csv_path, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(row.keys()))
        if write_header:
            writer.writeheader()
        writer.writerow(row)


def append_detection_result(result: ExperimentResult, csv_path: Path) -> None:
    _append_row(
        csv_path,
        {
            "run_id": result.run_id,
            "dataset_name": result.ground_truth.dataset_name,
            "dataset_category": result.ground_truth.dataset_category,
            "total_rows": result.ground_truth.total_rows,
            "expected_quarantine_rows": result.ground_truth.expected_quarantine_rows,
            "quarantine_row_count": result.quarantine_row_count,
            "silver_row_count": result.silver_row_count,
            "detection_accuracy": result.detection_accuracy,
            "execution_time_seconds": result.execution_time_seconds,
            "llm_calls_made": result.llm_calls_made,
            "notes": result.notes,
        },
    )


def append_repair_result(result: ExperimentResult, csv_path: Path) -> None:
    _append_row(
        csv_path,
        {
            "run_id": result.run_id,
            "dataset_name": result.ground_truth.dataset_name,
            "failure_type": result.config.failure_type,
            "repair_success": result.repair_success,
            "repair_attempts": result.repair_attempts,
            "execution_time_seconds": result.execution_time_seconds,
            "llm_calls_made": result.llm_calls_made,
            "notes": result.notes,
        },
    )


def append_ablation_result(result: ExperimentResult, csv_path: Path) -> None:
    _append_row(
        csv_path,
        {
            "run_id": result.run_id,
            "dataset_name": result.ground_truth.dataset_name,
            "failure_type": result.config.failure_type,
            "repair_enabled": result.config.repair_enabled,
            "pipeline_success": result.pipeline_success,
            "silver_row_count": result.silver_row_count,
            "quarantine_row_count": result.quarantine_row_count,
            "execution_time_seconds": result.execution_time_seconds,
            "llm_calls_made": result.llm_calls_made,
            "notes": result.notes,
        },
    )


def append_consistency_result(
    result: ExperimentResult, csv_path: Path, repeat_index: int
) -> None:
    """
    Real-world consistency batch — same file run twice, no ground truth,
    no injected failure. Reports outcome counts per repeat so run-to-run
    variance can be computed afterward (repeat 1 vs. repeat 2 per dataset).
    """
    _append_row(
        csv_path,
        {
            "run_id": result.run_id,
            "dataset_name": result.ground_truth.dataset_name,
            "source_format": result.ground_truth.source_format,
            "repeat_index": repeat_index,
            "silver_row_count": result.silver_row_count,
            "quarantine_row_count": result.quarantine_row_count,
            "pipeline_success": result.pipeline_success,
            "execution_time_seconds": result.execution_time_seconds,
            "llm_calls_made": result.llm_calls_made,
            "notes": result.notes,
        },
    )


def snapshot_result_json(result: ExperimentResult, runs_dir: Path) -> None:
    runs_dir.mkdir(parents=True, exist_ok=True)
    (runs_dir / f"{result.run_id}.json").write_text(
        result.model_dump_json(indent=2), encoding="utf-8"
    )


# -----------------------------
# Experiment plan — flat, numbered list built upfront
# -----------------------------


@dataclass
class PlannedExperiment:
    index: int
    label: str
    batch: str  # "detection" | "repair_ablation" | "consistency"
    ground_truth: GroundTruth
    config: ExperimentConfig
    repeat_index: int | None = None


def build_experiment_plan() -> list[PlannedExperiment]:
    """
    Builds the full, flat list of experiments to run, in order.
    Detection batch first (RQ1), then repair/ablation batch (RQ2, RQ3, RQ4),
    then the supplementary real-world consistency batch.
    """
    ground_truths = generate_all()
    plan: list[PlannedExperiment] = []
    idx = 1

    # Batch A — detection (RQ1)
    for name, gt in ground_truths.items():
        config = ExperimentConfig(
            experiment_name=f"{gt.dataset_name}_detection",
            repair_enabled=True,
            failure_type="none",
        )
        plan.append(
            PlannedExperiment(
                index=idx,
                label=f"[detection] {gt.dataset_name} — no injected failure",
                batch="detection",
                ground_truth=gt,
                config=config,
            )
        )
        idx += 1

    # Batch B — repair + ablation (RQ2, RQ3, RQ4)
    target_gt = ground_truths["dataset_1"]
    for failure_type in FAILURE_TYPES:
        for repair_enabled in [True, False]:
            label_suffix = "with_repair" if repair_enabled else "without_repair"
            config = ExperimentConfig(
                experiment_name=f"repair_{failure_type}_{label_suffix}",
                repair_enabled=repair_enabled,
                failure_type=failure_type,
            )
            plan.append(
                PlannedExperiment(
                    index=idx,
                    label=f"[repair/ablation] {target_gt.dataset_name} — "
                    f"{failure_type}, repair_enabled={repair_enabled}",
                    batch="repair_ablation",
                    ground_truth=target_gt,
                    config=config,
                )
            )
            idx += 1

    # Batch C — supplementary real-world consistency check
    real_world_gts = load_real_world_ground_truths()
    for gt in real_world_gts:
        for repeat_index in [1, 2]:
            config = ExperimentConfig(
                experiment_name=f"{gt.dataset_name}_consistency_run{repeat_index}",
                repair_enabled=True,
                failure_type="none",
            )
            plan.append(
                PlannedExperiment(
                    index=idx,
                    label=f"[consistency] {gt.dataset_name} ({gt.source_format}) "
                    f"— repeat {repeat_index}/2",
                    batch="consistency",
                    ground_truth=gt,
                    config=config,
                    repeat_index=repeat_index,
                )
            )
            idx += 1

    return plan


def print_plan(plan: list[PlannedExperiment]) -> None:
    print("\nExperiment plan:")
    print("-" * 70)
    for exp in plan:
        print(f"  {exp.index:>2}. {exp.label}")
    print("-" * 70)
    print(f"Total experiments: {len(plan)}\n")


def prompt_start_index(plan: list[PlannedExperiment]) -> int:
    """
    Asks which experiment number to start from. Returns a 1-based index.
    Entering nothing starts from the beginning.
    """
    while True:
        raw = input(
            f"Start from which experiment number? [1-{len(plan)}, default 1]: "
        ).strip()
        if raw == "":
            return 1
        if raw.isdigit() and 1 <= int(raw) <= len(plan):
            return int(raw)
        print(f"Enter a number between 1 and {len(plan)}.")


def confirm(prompt: str) -> bool:
    """Blocking Y/n confirmation. Only 'y'/'yes' (case-insensitive) proceeds."""
    raw = input(f"{prompt} [y/N]: ").strip().lower()
    return raw in ("y", "yes")


# -----------------------------
# Core experiment runner
# -----------------------------


def run_experiment(
    ground_truth: GroundTruth,
    config: ExperimentConfig,
    workspace_path: Path,
    run_id: str,
) -> ExperimentResult:
    logger.info(f"Running experiment: {config.experiment_name}")

    try:
        prepare_workspace(workspace_path)
        logger.info("config repair enable : %s", config.repair_enabled)
        logger.info("Configuring failure: %s", config.failure_type)
        failure_type = config.failure_type
        if failure_type != "none":
            set_injection(workspace_path, ground_truth.filename, config.failure_type)

        if ground_truth.dataset_category == "real_world":
            dataset_subdir = "real_world"
        elif ground_truth.dataset_name == "clean":
            dataset_subdir = "clean"
        else:
            dataset_subdir = "broken"

        source = (
            Path(__file__).parent / "datasets" / dataset_subdir / ground_truth.filename
        )
        dest = workspace_path / "input" / ground_truth.filename
        if not source.exists():
            raise FileNotFoundError(f"Dataset not found: {source}")
        shutil.copy2(source, dest)
        logger.info(f"Dataset copied to input: {ground_truth.filename}")

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
                        "Retrieve the dataset from the input folder, summarize it breifly and output to the output folder. "
                        "Run transformations and validations using Validation agent and complete the pipeline."
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
            "needs_repair": None,
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
        execution_time = round(time.perf_counter() - start_time, 2)

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

        store = SQLiteStore(db_path=workspace_path / "agentteam.db", llm=llm)
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

        print(
            f"    → silver: {silver_row_count}, quarantine: {quarantine_row_count}, "
            f"repair attempts: {repair_attempts}, repair success: {repair_success}, "
            f"detection accuracy: {detection_accuracy}\n"
            f"    → time: {execution_time}s, llm calls: {counter.total_calls}, "
            f"input tokens: {counter.total_input_tokens}, "
            f"output tokens: {counter.total_output_tokens}"
        )
        logger.info(f"Experiment complete: {config.experiment_name}")
        return result

    except Exception as e:
        logger.error(f"Experiment failed: {config.experiment_name} — {e}")
        print(f"    → FAILED: {e}")
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
    finally:
        clear_injection(workspace_path)


def _dispatch_result(
    exp: PlannedExperiment, result: ExperimentResult, results_dir: Path
) -> None:
    """Writes the result to the correct CSV(s) for its batch."""
    runs_dir = results_dir / "runs"
    snapshot_result_json(result, runs_dir)

    if exp.batch == "detection":
        append_detection_result(result, results_dir / "results_detection.csv")
    elif exp.batch == "repair_ablation":
        if exp.config.repair_enabled:
            append_repair_result(result, results_dir / "results_repair.csv")
        append_ablation_result(result, results_dir / "results_ablation.csv")
    elif exp.batch == "consistency":
        append_consistency_result(
            result, results_dir / "results_consistency.csv", exp.repeat_index
        )


# -----------------------------
# Interactive entry point
# -----------------------------


def run_all_experiments(workspace_path: Path) -> list[ExperimentResult]:
    results_dir = get_project_root() / "results"
    results_dir.mkdir(exist_ok=True)

    plan = build_experiment_plan()
    print_plan(plan)

    if not confirm("Run this experiment plan?"):
        print("Aborted — no experiments run.")
        return []

    start_index = prompt_start_index(plan)
    remaining = [exp for exp in plan if exp.index >= start_index]

    results = []
    for exp in remaining:
        print(f"\n{'=' * 70}")
        print(f"Experiment {exp.index}/{len(plan)}: {exp.label}")
        print(f"{'=' * 70}")

        if not confirm("Run this experiment?"):
            print("Skipped. Stopping — remaining experiments not run.")
            break

        run_id = str(uuid.uuid4())
        result = run_experiment(exp.ground_truth, exp.config, workspace_path, run_id)
        _dispatch_result(exp, result, results_dir)
        results.append(result)

        if exp.index != remaining[-1].index:
            if not confirm("Continue to the next experiment?"):
                print("Stopped by user. Remaining experiments not run.")
                break

    print(f"\nDone — {len(results)} experiment(s) run this session.")
    return results


if __name__ == "__main__":
    workspace = get_project_root() / "workspace"
    try:
        run_all_experiments(workspace)
    except KeyboardInterrupt:
        print("\nInterrupted by user.")
        sys.exit(1)
