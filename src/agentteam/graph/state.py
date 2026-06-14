"""
Graphstate: Central state for the entire agent pipeline
"""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field


class TraceEvent(BaseModel):
    step: str
    agent: Optional[str] = None
    action: Optional[str] = None

    input_preview: Optional[str] = None
    output_preview: Optional[str] = None

    metadata: dict[str, Any] = Field(default_factory=dict)


class GraphState(BaseModel):
    """
    Central state container for the entire agent pipeline.

    Design goals:
    - LLM-safe (structured, validated)
    - serializable (JSON-ready)
    - extensible (artifacts + metadata)
    - debuggable (trace log)
    """

    # Input / Output
    raw_input: Any = None
    final_output: Any = None

    # Pipeline stages
    retrieved_data: Any = None
    validated_data: Any = None
    repaired_data: Any = None

    # Error handling
    errors: list[str] = Field(default_factory=list)

    # Flexible artifact store
    # (LLM/tool outputs, agent memory, etc.)
    artifacts: dict[str, Any] = Field(default_factory=dict)

    # Execution trace
    trace: list[TraceEvent] = Field(default_factory=list)

    # Metadata (run config, model info, etc.)
    metadata: dict[str, Any] = Field(default_factory=dict)

    # Helper methods
    def add_trace(
        self,
        step: str,
        agent: Optional[str] = None,
        action: Optional[str] = None,
        input_preview: Optional[str] = None,
        output_preview: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> None:
        self.trace.append(
            TraceEvent(
                step=step,
                agent=agent,
                action=action,
                input_preview=input_preview,
                output_preview=output_preview,
                metadata=metadata or {},
            )
        )

    def add_error(self, error: str) -> None:
        self.errors.append(error)

    def set_artifact(self, key: str, value: Any) -> None:
        self.artifacts[key] = value

    def get_artifact(self, key: str, default: Any = None) -> Any:
        return self.artifacts.get(key, default)

    def update_metadata(self, key: str, value: Any) -> None:
        self.metadata[key] = value

    # Serialization
    def to_dict(self) -> dict[str, Any]:
        return self.model_dump()

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "GraphState":
        return cls.model_validate(data)
