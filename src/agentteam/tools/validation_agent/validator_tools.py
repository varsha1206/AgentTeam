# src/agentteam/tools/validator_agent/validator_tools.py

"""
Tools for the Validator Agent.
Responsible for reading output data, generating validation scripts,
executing them, and writing structured reports.
"""

import io
import json
import logging
import subprocess
from pathlib import Path

import pandas as pd
import yaml
from langchain.tools import tool

from agentteam.models.structured_outputs import GeneratedScript, ValidationReport

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
    ):
        self.bronze_dir = bronze_dir
        self.silver_dir = silver_dir
        self.quarantine_dir = quarantine_dir
        self.generated_dir = generated_dir
        self.logs_dir = logs_dir
        self.rules_path = rules_path
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
            self.quarantine_dir,
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

    def load_validation_rules(self, filename: str) -> str:
        """Load and return validation rules for a specific file as a JSON string."""
        if not self.rules_path.exists():
            return json.dumps(
                {
                    "filename": filename,
                    "user_defined": False,
                    "global_rules": {},
                    "file_rules": None,
                    "message": "No validation_rules.yaml found. Infer all rules from data sample.",
                }
            )
        rules = yaml.safe_load(self.rules_path.read_text(encoding="utf-8"))
        global_rules = rules.get("global_rules", {})
        file_rules = rules.get("rules", {}).get(filename, None)
        return json.dumps(
            {
                "filename": filename,
                "user_defined": file_rules is not None,
                "global_rules": global_rules,
                "file_rules": file_rules,
                "message": (
                    "Apply file_rules overrides on top of global_rules. "
                    "Infer any schema details not specified."
                    if file_rules
                    else "No file-specific rules. Apply global_rules and infer schema from sample."
                ),
            },
            indent=2,
        )

    def write_quarantine(self, source_path: str, quarantine_data: str) -> str:
        """Write quarantined rows with quarantine_reason column to workspace/output/quarantine/."""
        src_name = Path(source_path).name
        out_path = self.quarantine_dir / src_name
        try:
            df = pd.read_csv(io.StringIO(quarantine_data))
            if "quarantine_reason" not in df.columns:
                return "ERROR: quarantine_data must contain a quarantine_reason column"
            df.to_csv(out_path, index=False, encoding="utf-8")
            logger.info(f"Quarantine data written: {out_path} — {len(df)} rows")
            return str(out_path)
        except Exception as e:
            return f"ERROR writing quarantine data: {e}"

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

        @tool
        def load_validation_rules(filename: str) -> str:
            """
            Load validation rules for a specific file from validation_rules.yaml.
            Call this before read_sample to get the rules to apply.
            Args:
                filename: just the filename e.g. 'sample.csv', not the full path
            """
            return _self.load_validation_rules(filename)

        @tool
        def write_quarantine(source_path: str, quarantine_data: str) -> str:
            """
            Write quarantined rows to workspace/output/quarantine/.
            The quarantine_data must be a CSV string with a quarantine_reason column added.
            Args:
                source_path: absolute path to the original bronze file being validated
                quarantine_data: CSV string of bad rows with quarantine_reason column
            """
            return _self.write_quarantine(source_path, quarantine_data)

        return [
            read_sample,
            write_script,
            execute_script,
            write_validation_report,
            write_validated_data,
            load_validation_rules,
            write_quarantine,
        ]
