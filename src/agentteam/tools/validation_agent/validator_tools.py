# src/agentteam/tools/validator_agent/validator_tools.py

"""
Tools for the Validator Agent.
Responsible for reading output data, generating validation scripts,
executing them, and writing structured reports.
"""

import json
import logging
import subprocess
from pathlib import Path

import pandas as pd
from langchain.tools import tool

from agentteam.models.structured_outputs import GeneratedScript, ValidationReport

logger = logging.getLogger(__name__)


class ValidatorTools:
    """
    Tool suite for the Validator Agent.
    All tools operate within the provided workspace directories.
    """

    def __init__(
        self, bronze_dir: Path, silver_dir: Path, generated_dir: Path, logs_dir: Path
    ):
        self.bronze_dir = bronze_dir
        self.silver_dir = silver_dir
        self.generated_dir = generated_dir
        self.logs_dir = logs_dir
        self._validate_dirs()

    # -----------------------------
    # Validation
    # -----------------------------

    def _validate_dirs(self) -> None:
        for path in [
            self.bronze_dir,
            self.silver_dir,
            self.generated_dir,
            self.logs_dir,
        ]:
            if not path.exists():
                raise FileNotFoundError(f"Required directory not found at {path}")

    # -----------------------------
    # Tools
    # -----------------------------
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
            existing_data = json.loads(report_path.read_text(encoding="utf-8"))
            if not isinstance(existing_data, list):
                existing_data = [existing_data]
        else:
            existing_data = []

        entry = report.model_dump()
        entry["source_file"] = source_file

        existing_data.append(entry)

        report_path.write_text(json.dumps(existing_data, indent=2), encoding="utf-8")
        logger.info(
            f"Validation report appended: {report_path} — {report.status} for {source_file}"
        )
        return str(report_path)

    # -----------------------------
    # LangChain tool bindings
    # -----------------------------

    def as_tools(self) -> list:
        _self = self

        @tool
        def read_sample(file_path: str) -> str:
            """
            Read the first 20 rows of a CSV file for schema inference.
            Args:
                file_path: absolute path as returned by list_output_files
            """
            return _self.read_sample(file_path)

        @tool
        def write_script(filename: str, code: str, description: str) -> str:
            """
            Save a generated validation script to the generated directory.
            Args:
                filename: e.g. 'validation_001.py'
                code: complete Python script as plain string, no markdown, no backticks
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
            Args:
                script_path: absolute path returned by write_script
            """
            return _self.execute_script(script_path)

        @tool
        def write_validated_data(source_path: str) -> str:
            """
            Copy the validated CSV to workspace/output/validated_data.csv.
            Only call this when validation status is PASS.
            Args:
                source_path: absolute path to the validated CSV file
            """
            return _self.write_validated_data(source_path)

        @tool
        def write_validation_report(
            status: str,
            row_count: int,
            column_count: int,
            errors: list[str],
            summary: str,
            source_file: str,
        ) -> str:
            """
            Append the validation report for this file to workspace/logs/validation_report.json.
            Args:
                status: 'PASS' or 'FAIL'
                row_count: total number of rows in the dataset
                column_count: total number of columns in the dataset
                errors: list of validation errors found, empty if PASS
                summary: one sentence summary of the result
                source_file: the absolute path of the file that was validated
            """
            return _self.write_validation_report(
                ValidationReport(
                    status=status,
                    row_count=row_count,
                    column_count=column_count,
                    errors=errors,
                    summary=summary,
                ),
                source_file=source_file,
            )

        return [
            read_sample,
            write_script,
            execute_script,
            write_validation_report,
            write_validated_data,
        ]
