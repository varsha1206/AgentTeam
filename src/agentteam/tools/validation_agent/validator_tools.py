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
import yaml
from langchain.tools import tool

from agentteam.models.structured_outputs import (
    ColumnRule,
    FileValidationRules,
    GeneratedScript,
    TransformationEntry,
    TransformationReport,
    TransformationRule,
    ValidationReport,
)

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
    ):
        self.bronze_dir = bronze_dir
        self.silver_dir = silver_dir
        self.quarantine_dir = quarantine_dir
        self.generated_dir = generated_dir
        self.logs_dir = logs_dir
        self.temp_dir = temp_dir
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
            self.temp_dir,
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
        """Promote a validated transformed file from temp to silver."""
        src = Path(source_path)
        if not src.exists():
            return f"ERROR: Source file not found at {src}"
        df = pd.read_csv(src)
        out_path = self.silver_dir / src.name.replace("transformed_", "")
        df.to_csv(out_path, index=False, encoding="utf-8")
        logger.info(f"Validated data written: {out_path}")
        return str(out_path)

    def execute_script(self, script_path: str) -> str:
        path = Path(script_path)
        if not path.exists():
            return "SCRIPT_FAILED: Script not found"
        try:
            result = subprocess.run(
                ["python", str(path)],
                capture_output=True,
                text=True,
                timeout=30,
                encoding="utf-8",
            )
            if result.returncode != 0:
                logger.error(f"Script failed: {result.stderr}")
                return f"SCRIPT_FAILED (exit {result.returncode}):\n{result.stderr}"

            output = result.stdout.strip()
            logger.info(f"Script executed: {path}")

            # Validate JSON output so agent never sees malformed responses
            try:
                json.loads(output)
                return f"SCRIPT_SUCCESS:\n{output}"
            except json.JSONDecodeError:
                return (
                    f"SCRIPT_FAILED: Script ran but did not print valid JSON.\n"
                    f"Raw output was:\n{output[:500]}"
                )

        except subprocess.TimeoutExpired:
            return "SCRIPT_FAILED: timed out after 30 seconds"
        except Exception as e:
            return f"SCRIPT_FAILED: {e}"

    def write_transformation_report(self, report: TransformationReport) -> str:
        """Append transformation report to workspace/logs/transformation_report.json."""
        report_path = self.logs_dir / "transformation_report.json"

        if report_path.exists():
            existing = json.loads(report_path.read_text(encoding="utf-8"))
            if not isinstance(existing, list):
                existing = [existing]
        else:
            existing = []

        existing.append(report.model_dump())
        report_path.write_text(json.dumps(existing, indent=2), encoding="utf-8")
        logger.info(f"Transformation report appended: {report_path} — {report.summary}")
        return str(report_path)

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
        """Load validation rules for a file. Returns a FileValidationRules JSON object."""
        if not self.rules_path.exists():
            return FileValidationRules(
                filename=filename,
                schema={},
                transformations=[],
                inferred=True,
            ).model_dump_json(indent=2)

        rules = yaml.safe_load(self.rules_path.read_text(encoding="utf-8"))
        global_rules = rules.get("global_rules", {})
        file_overrides = rules.get("rules", {}).get(filename, {}).get("overrides", {})
        file_schema = rules.get("rules", {}).get(filename, {}).get("schema", {})
        merged_transforms = {**global_rules, **file_overrides}

        transformations = [
            TransformationRule(**t)
            for t in merged_transforms.get("transformations", [])
        ]
        schema = (
            {col: ColumnRule(**col_rules) for col, col_rules in file_schema.items()}
            if file_schema
            else {}
        )

        return FileValidationRules(
            filename=filename,
            schema=schema,
            transformations=transformations,
            inferred=not bool(file_schema),
        ).model_dump_json(indent=2)

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
            Call this after execute_script succeeds for the transformation script.
            Args:
                source_file: absolute path to the bronze source file
                output_file: absolute path to the transformed temp file
                total_rows_input: total rows in the bronze file
                total_rows_output: rows written to temp after transformation
                quarantined_rows: rows sent to quarantine
                transformations_applied: list of dicts with operation, columns, rows_affected, reason
                inferred_rules: true if any rules were LLM-inferred rather than user-defined
                summary: one sentence summary of the transformation outcome
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
            Load validation rules for a file. Returns a FileValidationRules JSON object.
            Call this first before read_sample.
            Args:
                 filename: just the filename e.g. 'sample.csv'
            """
            return _self.load_validation_rules(filename)

        return [
            load_validation_rules,
            read_sample,
            write_script,
            execute_script,
            write_transformation_report,
            write_validation_report,
            write_validated_data,
        ]
