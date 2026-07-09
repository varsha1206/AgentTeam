# src/agentteam/models/structured_outputs.py

from typing import Literal

from pydantic import BaseModel, Field


class GeneratedScript(BaseModel):
    """Structured output for a generated Python script."""

    filename: str = Field(
        description="The filename for the script, e.g. 'retrieval_001.py'"
    )
    code: str = Field(
        description="The complete, executable Python script as a plain string. No markdown, no backticks."
    )
    description: str = Field(
        description="One sentence describing what this script does."
    )


class ValidationReport(BaseModel):
    status: Literal["PASS", "FAIL"] = Field(
        description="Whether data passed or failed validation."
    )
    row_count: int = Field(description="Total number of rows in the dataset")
    column_count: int = Field(description="Total number of columns in the dataset")
    errors: list[str] = Field(
        default_factory=list, description="List of validation errors found."
    )
    summary: str = Field(description="One sentence summary of the validation result.")


class RetrievalResult(BaseModel):
    """Structured result extracted from retrieval agent messages."""

    status: Literal["complete", "failed"] = Field(
        description="Whether retrieval completed successfully."
    )
    summary: str = Field(description="Summary of what was retrieved.")
    script_path: str | None = Field(
        default=None, description="Absolute path to the generated retrieval script."
    )
    output_path: str | None = Field(
        default=None, description="Absolute path to the output CSV file."
    )
    errors: list[str] = Field(
        default_factory=list, description="Any errors encountered during retrieval."
    )


class DataSource(BaseModel):
    """Describes where and how to read source data."""

    source_type: Literal["csv", "json", "api"] = Field(
        description="The type of data source."
    )
    path: str | None = Field(
        default=None, description="Absolute file path for csv or json sources."
    )
    url: str | None = Field(default=None, description="Endpoint URL for api sources.")
    method: Literal["GET", "POST"] | None = Field(
        default=None, description="HTTP method for api sources."
    )
    headers: dict[str, str] = Field(
        default_factory=dict, description="HTTP headers for api sources."
    )
    params: dict[str, str] = Field(
        default_factory=dict, description="Query params or POST body for api sources."
    )
    output_filename: str = Field(
        description="What to name the output bronze file e.g. 'employee_data.csv'."
    )


class AgentInstruction(BaseModel):
    """Structured instruction sent by the orchestrator to an agent at invocation time."""

    task: Literal[
        "full_pipeline",
        "transform_and_validate",
        "validate_only",
        "repair_transformation",
        "repair_retrieval",
    ] = Field(description="What the agent should do this invocation.")
    source: DataSource | None = Field(
        default=None, description="Data source description. Retrieval agent only."
    )
    target_file: str | None = Field(
        default=None, description="Absolute path to the file to process."
    )
    script_to_repair: str | None = Field(
        default=None,
        description="Absolute path to the script that needs patching. Repair agent only.",
    )
    errors: list[str] = Field(
        default_factory=list,
        description="Errors from the previous run that need to be addressed.",
    )
    context: str | None = Field(
        default=None, description="Any additional context the agent needs."
    )


class ValidatorResult(BaseModel):
    """Structured result extracted from validator agent messages."""

    status: Literal["complete", "failed"] = Field(
        description="Whether the validation process completed successfully."
    )
    validation_outcome: Literal["PASS", "FAIL"] = Field(
        description="Whether the data passed or failed validation."
    )
    script_path: str | None = Field(
        default=None, description="Absolute path to the generated validation script."
    )
    report_path: str | None = Field(
        default=None, description="Absolute path to the validation report JSON file."
    )
    errors: list[str] = Field(
        default_factory=list, description="Validation errors found in the data."
    )
    summary: str = Field(description="One sentence summary of the validation result.")

    quarantine_percentage: float | None = Field(
        default=None, description="Percentage of rows quarantined during validation."
    )


class RoutingDecision(BaseModel):
    """Structured routing decision after each agent completes."""

    next_node: Literal["validation_agent", "repair_agent", "end"] = Field(
        description="The next node to route to."
    )
    reason: str = Field(description="One sentence explaining the routing decision.")


class ColumnRule(BaseModel):
    """Rules for a single column."""

    type: Literal["int", "float", "str", "bool", "date"] | None = Field(
        default=None, description="Expected data type for this column."
    )
    nullable: bool = Field(
        default=True, description="Whether this column can contain null values."
    )
    min: float | None = Field(
        default=None, description="Minimum value for numeric columns."
    )
    max: float | None = Field(
        default=None, description="Maximum value for numeric columns."
    )
    date_format: str | None = Field(
        default=None, description="Expected date format e.g. '%Y-%m-%d'."
    )


class TransformationRule(BaseModel):
    """A single transformation to apply before validation."""

    operation: Literal[
        "rename_to_snake_case",
        "rename_to_camel_case",
        "fill_missing_mean",
        "fill_missing_mode",
        "fill_missing_value",
        "drop_missing",
        "coerce_numeric",
        "coerce_date",
        "drop_duplicates",
        "quarantine_missing",
        "quarantine_duplicates",
        "quarantine_type_mismatch",
    ] = Field(description="The transformation or quarantine operation to apply.")
    columns: list[str] | None = Field(
        default=None,
        description="Columns to apply this operation to. None means all columns.",
    )
    fill_value: str | None = Field(
        default=None, description="Value to use when operation is fill_missing_value."
    )


class TransformationEntry(BaseModel):
    """A single transformation applied to the dataset."""

    operation: str = Field(description="The transformation operation applied.")
    columns: list[str] | None = Field(
        default=None,
        description="Columns the operation was applied to. None means all columns.",
    )
    rows_affected: int = Field(
        default=0, description="Number of rows affected by this transformation."
    )
    reason: str = Field(description="Why this transformation was applied.")


class TransformationReport(BaseModel):
    """Structured report of all transformations applied to a single file."""

    source_file: str = Field(description="Absolute path to the bronze source file.")
    output_file: str = Field(description="Absolute path to the transformed temp file.")
    total_rows_input: int = Field(description="Total rows in the bronze file.")
    total_rows_output: int = Field(
        description="Rows written to temp after transformation."
    )
    quarantined_rows: int = Field(description="Rows sent to quarantine.")
    transformations_applied: list[TransformationEntry] = Field(
        default_factory=list, description="Ordered list of transformations applied."
    )
    inferred_rules: bool = Field(
        default=False,
        description="True if any rules were inferred by LLM rather than user-defined.",
    )
    summary: str = Field(
        description="One sentence summary of the transformation outcome."
    )


class FileValidationRules(BaseModel):
    """Complete validation and transformation rules for a single file."""

    filename: str = Field(
        description="The filename these rules apply to e.g. 'sample.csv'."
    )
    schema: dict[str, ColumnRule] = Field(
        default_factory=dict,
        description="Per-column rules. LLM infers any columns not specified.",
    )
    transformations: list[TransformationRule] = Field(
        default_factory=list,
        description="Ordered list of transformations to apply before validation.",
    )
    inferred: bool = Field(
        default=False,
        description="True if these rules were inferred by the LLM rather than user-defined.",
    )


class QuarantineEntry(BaseModel):
    """A single quarantined row with its reason."""

    row_index: int = Field(description="Original row index in the source file.")
    column: str | None = Field(
        default=None, description="Column that caused quarantine, if applicable."
    )
    value: str | None = Field(
        default=None, description="The offending value, if applicable."
    )
    reason: str = Field(
        description="Human-readable reason why this row was quarantined."
    )
    rule_violated: str = Field(
        description="The rule or operation that this row violated."
    )


class QuarantineReport(BaseModel):
    """Structured quarantine report for a single file."""

    source_file: str = Field(description="Absolute path to the source bronze file.")
    total_rows: int = Field(description="Total rows in the source file.")
    quarantined_rows: int = Field(description="Number of rows quarantined.")
    passed_rows: int = Field(description="Number of rows that passed to silver.")
    entries: list[QuarantineEntry] = Field(
        default_factory=list, description="One entry per quarantined row."
    )


class RepairResult(BaseModel):
    """Structured result extracted from repair agent messages."""

    status: Literal["complete", "failed"] = Field(
        description="Whether the repair process completed successfully."
    )
    script_path: str | None = Field(
        default=None, description="Absolute path to the repaired script."
    )
    output_path: str | None = Field(
        default=None, description="Absolute path to the repaired output CSV."
    )
    errors: list[str] = Field(
        default_factory=list, description="Any errors encountered during repair."
    )
    summary: str = Field(description="One sentence summary of what was repaired.")


class RulesCache(BaseModel):
    """Resolved FileValidationRules written to temp/ for use by the executor."""

    filename: str = Field(description="The filename these rules apply to.")
    rules: FileValidationRules = Field(description="The complete resolved rules.")
    source: Literal["user_defined", "llm_inferred", "hybrid"] = Field(
        description="Whether rules came from YAML, LLM inference, or both."
    )
