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
        def execute_script(script_path: str, stage: str) -> str:
            """
            Execute a validation script and return its output.
            Returns SCRIPT_SUCCESS or SCRIPT_FAILED.
            Args:
                script_path: absolute path returned by write_script
                stage: 'validation', 'transformation', or 'retrieval' — which stage this script belongs to
            """
            return _self.execute_script(script_path, stage)

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
