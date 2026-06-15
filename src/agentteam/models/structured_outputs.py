# src/agentteam/models/structured_outputs.py

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
