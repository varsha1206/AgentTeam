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

    def load_validation_rules(self, filename: str) -> str:
        """Load validation rules and return as FileValidationRules JSON."""

        if not self.rules_path.exists():
            logger.warning(f"Rules file not found at {self.rules_path}")
            return FileValidationRules(
                filename=filename,
                schema={},
                transformations=[],
                inferred=True,
            ).model_dump_json(indent=2)

        raw = yaml.safe_load(self.rules_path.read_text(encoding="utf-8"))

        global_rules = raw.get("global_rules", {})
        file_rules = raw.get("rules", {}).get(filename, {})

        file_schema = file_rules.get("schema", {})
        file_overrides = file_rules.get("overrides", {})

        merged_transformations = global_rules.get(
            "transformations", []
        ) + file_overrides.get("transformations", [])

        result = FileValidationRules(
            filename=filename,
            schema={column: ColumnRule(**rule) for column, rule in file_schema.items()},
            transformations=[
                TransformationRule(**rule) for rule in merged_transformations
            ],
            inferred=not bool(file_schema),
        )

        logger.info(
            "Loaded validation rules for %s: %d schema rules, %d transformations",
            filename,
            len(result.schema),
            len(result.transformations),
        )

        return result.model_dump_json(indent=2)

    def _resolve_inferred_columns(
        self,
        rules: FileValidationRules,
        source_path: str,
    ) -> FileValidationRules:
        """
        Resolve any transformation rules that have selection='infer' by using the sample DataFrame to infer the most appropriate columns.
        Returns a new FileValidationRules object with the inferred columns filled in.
        """
        sample_df = pd.read_csv(source_path, nrows=5)

        infer_rules = [r for r in rules.transformations if r.selection == "infer"]
        transformation_operations = [r.operation for r in infer_rules]
        if not infer_rules:
            return rules

        prompt = f"""
    Dataset columns:
    {list(sample_df.columns)}

    Transformations to apply:
    {transformation_operations}

    Infer the most appropriate columns for each transformation.
    """

        result = self.llm.with_structured_output(InferredColumn).invoke(prompt)
        transformations_columns = {}

        for transformation, columns in result.transformations_column_mapping.items():
            transformations_columns[transformation] = columns

        logger.info("Inferred columns for transformations: %s", transformations_columns)

        for transformation_rule in rules.transformations:
            if transformation_rule.selection != "infer":
                continue

            transformation_rule.columns = transformations_columns[
                transformation_rule.operation
            ]
            transformation_rule.selection = "explicit"
            logger.info(transformation_rule)

        return rules

    def get_execution_plan(self, rules_json: str, source_path: str) -> str:
        """
        Produce an execution plan from FileValidationRules.
        Returns plan summary JSON including which operations need plugin generation.
        """
        rules = FileValidationRules.model_validate_json(rules_json)
        rules = self._resolve_inferred_columns(rules, source_path)
        plan = self.planner.plan(rules)
        summary = plan.summary()
        logger.info(f"Execution plan: {summary}")
        return json.dumps(summary, indent=2)

    def generate_plugin(self, operation: str, code: str) -> str:
        """
        Save a LLM-generated plugin to workspace/plugins/ and register it.
        Args:
            operation: the operation name e.g. 'normalize_phone_numbers'
            code: complete plugin function as plain Python string
        """
        path = self.plugin_registry.save(operation, code)
        logger.info(f"Plugin generated and registered: {operation} at {path}")
        return str(path)

    def run_transformation(
        self, rules_json: str, source_path: str, filename: str
    ) -> str:
        """
        Run the full transformation pipeline against a bronze file.
        Uses ExecutionPlanner: built-ins via RuleExecutor, plugins via PluginRegistry.
        Writes transformed data to temp/transformed_<filename>.csv.
        Returns JSON: {transformed_path, total_rows, operations_applied, skipped_operations}
        """
        rules = FileValidationRules.model_validate_json(rules_json)
        plan = self.planner.plan(rules)

        if not plan.is_fully_ready:
            pending = [s.rule.operation for s in plan.pending_steps]
            return json.dumps(
                {
                    "error": "NEEDS_PLUGINS",
                    "pending_operations": pending,
                    "message": f"Generate plugins for these operations first: {pending}",
                }
            )

        try:
            df = pd.read_csv(source_path)
            total_rows = len(df)
            df = self.planner.execute(df, plan)

            out_path = self.temp_dir / f"transformed_{filename}"
            df.to_csv(out_path, index=False, encoding="utf-8")

            applied = [s.rule.operation for s in plan.ready_steps]
            logger.info(f"Transformation complete: {len(df)} rows → {out_path}")

            return json.dumps(
                {
                    "transformed_path": str(out_path),
                    "total_rows": total_rows,
                    "output_rows": len(df),
                    "operations_applied": applied,
                    "skipped_operations": [],
                }
            )
        except Exception as e:
            logger.error(f"Transformation failed: {e}")
            return json.dumps(
                {
                    "SCRIPT_FAILED": True,
                    "stage": "transformation",
                    "error": str(e),
                    "script_path": None,
                }
            )

    def write_script(self, script: GeneratedScript) -> str:
        """Save a generated validation script to workspace/generated/."""
        script_path = self.generated_dir / script.filename
        script_path.parent.mkdir(parents=True, exist_ok=True)
        script_path.write_text(script.code, encoding="utf-8")
        logger.info(f"Validation script written: {script_path} — {script.description}")

        # silently corrupt for testing — agent does not see this
        if self._should_inject_error(script.filename):
            corrupted = "this is not valid python!!!\n" + script.code
            script_path.write_text(corrupted, encoding="utf-8")
            logger.debug(
                f"Test error injected into {script.filename}"
            )  # DEBUG not WARNING

        return str(script_path)

    def _should_inject_error(self, filename: str) -> bool:
        if not self.rules_path.exists():
            return False
        try:
            raw = yaml.safe_load(self.rules_path.read_text(encoding="utf-8"))
            stem = filename.replace("validation_", "").replace(".py", ".csv")
            return (
                raw.get("rules", {})
                .get(stem, {})
                .get("test", {})
                .get("inject_script_error", False)
            )
        except Exception:
            return False

    def execute_script(self, script_path: str, stage: str = "unknown") -> str:
        """Execute a script and return its output."""
        path = Path(script_path)

        if not path.exists():
            return json.dumps(
                {
                    "SCRIPT_FAILED": True,
                    "stage": stage,
                    "error": f"Script not found at {script_path}",
                    "script_path": script_path,
                }
            )

        try:
            result = subprocess.run(
                ["python", str(path)],
                capture_output=True,
                text=True,
                timeout=30,
                encoding="utf-8",
            )

            if result.returncode != 0:
                logger.error(f"Script failed: {path} — {result.stderr[:200]}")
                return json.dumps(
                    {
                        "SCRIPT_FAILED": True,
                        "stage": stage,
                        "error": result.stderr,
                        "script_path": str(path),
                    }
                )

            output = result.stdout.strip()
            logger.info(f"Script executed: {path}")

            try:
                json.loads(output)
                return f"SCRIPT_SUCCESS:\n{output}"
            except json.JSONDecodeError:
                return json.dumps(
                    {
                        "SCRIPT_FAILED": True,
                        "stage": stage,
                        "error": f"Script ran but did not print valid JSON. Raw output: {output[:300]}",
                        "script_path": str(path),
                    }
                )

        except subprocess.TimeoutExpired:
            return json.dumps(
                {
                    "SCRIPT_FAILED": True,
                    "stage": stage,
                    "error": "Script timed out after 30 seconds",
                    "script_path": str(path),
                }
            )
        except Exception as e:
            return json.dumps(
                {
                    "SCRIPT_FAILED": True,
                    "stage": stage,
                    "error": str(e),
                    "script_path": str(path),
                }
            )

    def write_validated_data(self, source_path: str) -> str:
        """Promote a validated transformed file from temp to silver."""
        src = Path(source_path)
        if not src.exists():
            return f"ERROR: Source file not found at {src}"
        df = pd.read_csv(src, encoding="utf-8")
        out_path = self.silver_dir / src.name.replace("transformed_", "")
        df.to_csv(out_path, index=False, encoding="utf-8")
        logger.info(f"Promoted to silver: {out_path}")
        return str(out_path)

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
        def execute_script(script_path: str, stage: str) -> str:
            """
            Execute a validation script and return its output.
            Args:
                script_path: absolute path returned by write_script
                stage: 'validation', 'transformation', or 'retrieval' — which stage this script belongs to
            """
            return _self.execute_script(script_path, stage)

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
