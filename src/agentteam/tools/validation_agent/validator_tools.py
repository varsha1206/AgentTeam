"""
Tools for the Validator Agent.
Responsible for reading output data, planning and executing transformations,
generating validation scripts, and writing structured reports.
"""

import json
import logging
import subprocess
from pathlib import Path

import pandas as pd
import yaml
from langchain.tools import tool
from langchain_core.language_models.chat_models import BaseChatModel

from agentteam.models.structured_outputs import (
    ColumnRule,
    FileValidationRules,
    GeneratedScript,
    InferredColumn,
    TransformationEntry,
    TransformationReport,
    TransformationRule,
    ValidationReport,
)
from agentteam.utils.execution_planner import ExecutionPlanner
from agentteam.utils.plugin_registry import PluginRegistry

logger = logging.getLogger(__name__)


class ValidatorTools:
    """
    Tool suite for the Validator Agent.
    All tools operate within the provided workspace directories.
    """

    def __init__(
        self,
        bronze_dir: Path,
        silver_dir: Path,
        quarantine_dir: Path,
        generated_dir: Path,
        logs_dir: Path,
        rules_path: Path,
        temp_dir: Path,
        plugins_dir: Path,
        llm: BaseChatModel,
    ):
        self.bronze_dir = bronze_dir
        self.silver_dir = silver_dir
        self.quarantine_dir = quarantine_dir
        self.generated_dir = generated_dir
        self.logs_dir = logs_dir
        self.temp_dir = temp_dir
        self.rules_path = rules_path
        self.plugin_registry = PluginRegistry(plugins_dir)
        self.planner = ExecutionPlanner(self.plugin_registry)
        self._validate_dirs()
        self.plugin_registry.load_all()
        self.llm = llm

    def _validate_dirs(self) -> None:
        for path in [
            self.bronze_dir,
            self.silver_dir,
            self.generated_dir,
            self.logs_dir,
            self.temp_dir,
            self.quarantine_dir,
        ]:
            if not path.exists():
                raise FileNotFoundError(f"Required directory not found at {path}")

    def read_sample(self, file_path: str) -> str:
        """Read first 20 rows of a CSV for schema inference."""
        path = Path(file_path)
        if not path.exists():
            return f"ERROR: File not found at {path}"
        try:
            df = pd.read_csv(path, nrows=20)
            logger.info(f"Read sample: {path} — {len(df)} rows, {len(df.columns)} cols")
            return (
                f"Columns: {list(df.columns)}\n"
                f"Dtypes:\n{df.dtypes.to_string()}\n"
                f"Sample (first 20 rows):\n{df.to_string(index=False)}\n"
                f"Null counts:\n{df.isnull().sum().to_string()}"
            )
        except Exception as e:
            return f"ERROR reading sample from {path}: {e}"

    def write_script(self, script: GeneratedScript) -> str:
        """Save a generated validation script to workspace/generated/."""
        script_path = self.generated_dir / script.filename
        script_path.parent.mkdir(parents=True, exist_ok=True)
        script_path.write_text(script.code, encoding="utf-8")
        logger.info(f"Validation script written: {script_path} — {script.description}")
        return str(script_path)

    def write_validated_data(self, source_path: str) -> str:
        """Copy validated CSV to workspace/output/validated_data.csv on PASS."""
        src = Path(source_path)
        if not src.exists():
            return f"ERROR: Source file not found at {src}"
        df = pd.read_csv(src)
        out_path = self.silver_dir / src.name
        df.to_csv(out_path, index=False, encoding="utf-8")
        logger.info(f"Validated data written: {out_path}")
        return str(out_path)

    def execute_script(self, script_path: str) -> str:
        """Execute a validation script and return its output."""
        path = Path(script_path)
        if not path.exists():
            return f"ERROR: Script not found at {path}"
        try:
            result = subprocess.run(
                ["python", str(path)],
                capture_output=True,
                text=True,
                timeout=30,
                encoding="utf-8",
            )
            if result.returncode != 0:
                logger.error(f"Validation script failed: {result.stderr}")
                return f"ERROR (exit {result.returncode}):\n{result.stderr}"
            logger.info(f"Validation script executed: {path}")
            return result.stdout or "Script completed with no output."
        except subprocess.TimeoutExpired:
            return "ERROR: Script timed out after 30 seconds"
        except Exception as e:
            return f"ERROR: {e}"

    def write_validation_report(
        self, report: ValidationReport, source_file: str
    ) -> str:
        """Append structured validation report to workspace/logs/validation_report.json."""
        report_path = self.logs_dir / "validation_report.json"

        if report_path.exists():
            existing = json.loads(report_path.read_text(encoding="utf-8"))
            if not isinstance(existing, list):
                existing = [existing]
        else:
            existing = []

        entry = report.model_dump()
        entry["source_file"] = source_file
        existing.append(entry)

        report_path.write_text(json.dumps(existing, indent=2), encoding="utf-8")
        logger.info(
            f"Validation report appended: {report_path} — {report.status} for {source_file}"
        )
        return str(report_path)

    def as_tools(self) -> list:
        _self = self

        @tool
        def load_validation_rules(filename: str) -> str:
            """
            Load validation rules for a file. Returns a FileValidationRules JSON object.
            Call this first before read_sample.
            Args:
                filename: just the filename e.g. 'sample.csv'
            """
            return _self.load_validation_rules(filename)

        @tool
        def read_sample(file_path: str) -> str:
            """
            Read the first 20 rows of a CSV file for schema inference.
            Args:
                file_path: absolute path to the bronze file
            """
            return _self.read_sample(file_path)

        @tool
        def get_execution_plan(rules_json: str, source_path: str) -> str:
            """
            Get the execution plan for a set of FileValidationRules.
            Returns which operations are built-in, which are plugins, and which need generation.
            Call this after producing the complete FileValidationRules.
            Args:
                rules_json: complete FileValidationRules as a JSON string
                source_path: absolute path to the bronze
            """
            return _self.get_execution_plan(rules_json, source_path)

        @tool
        def generate_plugin(operation: str, code: str) -> str:
            """
            Save a generated plugin function to workspace/plugins/ and register it.
            Only call this for operations listed as needs_generation in the execution plan.
            The function must be named exactly the same as the operation.
            Args:
                operation: operation name e.g. 'normalize_phone_numbers'
                code: complete plugin function, plain Python, no markdown, no backticks
                      must define: def <operation>(df: pd.DataFrame, rule) -> pd.DataFrame
            """
            return _self.generate_plugin(operation, code)

        @tool
        def run_transformation(rules_json: str, source_path: str, filename: str) -> str:
            """
            Run the full transformation pipeline against a bronze file.
            Returns JSON: {transformed_path, total_rows, output_rows, operations_applied}
            If any operations need plugin generation first, returns {error: NEEDS_PLUGINS, pending_operations: [...]}
            Args:
                rules_json: complete FileValidationRules as a JSON string
                source_path: absolute path to the bronze file
                filename: just the filename e.g. 'employee_data.csv'
            """
            return _self.run_transformation(rules_json, source_path, filename)

        @tool
        def write_script(filename: str, code: str, description: str) -> str:
            """
            Save a generated validation script to the generated directory.
            Use this for validation scripts only — not transformation.
            Args:
                filename: e.g. 'validation_employee_data.py'
                code: complete Python script, plain string, no markdown, no backticks
                description: one sentence describing what this script validates
            """
            return _self.write_script(
                GeneratedScript(
                    filename=filename,
                    code=code,
                    description=description,
                )
            )

        @tool
        def execute_script(script_path: str) -> str:
            """
            Execute a validation script and return its output.
            Returns SCRIPT_SUCCESS or SCRIPT_FAILED.
            Args:
                script_path: absolute path returned by write_script
            """
            return _self.execute_script(script_path)

        @tool
        def write_transformation_report(
            source_file: str,
            output_file: str,
            total_rows_input: int,
            total_rows_output: int,
            quarantined_rows: int,
            transformations_applied: list[dict],
            inferred_rules: bool,
            summary: str,
        ) -> str:
            """
            Write a structured transformation report to workspace/logs/transformation_report.json.
            Args:
                source_file: absolute path to the bronze source file
                output_file: absolute path to the transformed temp file
                total_rows_input: total rows in the bronze file
                total_rows_output: rows in temp after transformation
                quarantined_rows: rows sent to quarantine (0 at this stage)
                transformations_applied: list of dicts with operation, columns, rows_affected, reason
                inferred_rules: true if any rules were LLM-inferred
                summary: one sentence summary
            """
            return _self.write_transformation_report(
                TransformationReport(
                    source_file=source_file,
                    output_file=output_file,
                    total_rows_input=total_rows_input,
                    total_rows_output=total_rows_output,
                    quarantined_rows=quarantined_rows,
                    transformations_applied=[
                        TransformationEntry(**t) for t in transformations_applied
                    ],
                    inferred_rules=inferred_rules,
                    summary=summary,
                )
            )

        @tool
        def write_validation_report(
            status: str,
            row_count: int,
            column_count: int,
            validation_violations: list[str],
            quarantined_rows: int,
            summary: str,
            source_file: str,
        ) -> str:
            """
            Append the validation report to workspace/logs/validation_report.json.
            Args:
                status: 'PASS' or 'FAIL'
                row_count: valid rows promoted to silver
                column_count: number of columns
                validation_violations: list of validation errors, empty if PASS
                summary: one sentence summary
                source_file: absolute path to the bronze file
            """
            return _self.write_validation_report(
                ValidationReport(
                    status=status,
                    row_count=row_count,
                    column_count=column_count,
                    validation_violations=validation_violations,
                    quarantined_rows=quarantined_rows,
                    summary=summary,
                ),
                source_file=source_file,
            )

        return [
            load_validation_rules,
            read_sample,
            get_execution_plan,
            generate_plugin,
            run_transformation,
            write_script,
            execute_script,
            write_transformation_report,
            write_validation_report,
        ]
