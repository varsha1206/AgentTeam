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
    """Structured output for a validation report."""

    status: str = Field(description="Either 'PASS' or 'FAIL'")
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


class RoutingDecision(BaseModel):
    """Structured routing decision after each agent completes."""

    next_node: Literal["validator_agent", "repair_agent", "end"] = Field(
        description="The next node to route to."
    )
    reason: str = Field(description="One sentence explaining the routing decision.")
