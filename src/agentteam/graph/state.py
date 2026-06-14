"""
Graphstate: Central state for the entire agent pipeline
"""

from __future__ import annotations

from typing import Annotated, Any, Mapping

from langchain.agents import AgentState
from langchain.chat_models import BaseChatModel
from langgraph.managed.is_last_step import RemainingSteps


def merge_dict(existing: dict[str, Any], new: dict[str, Any]) -> dict[str, Any]:
    """
    Merges the existing dictionary with a new dictionary.

    This function logs the state merge and ensures that the new values
    are appended to the existing state without overwriting other entries.
    Args:
        existing (Dict[str, Any]): The current dictionary state.
        new (Dict[str, Any]): The new dictionary state to merge.
    Returns:
        Dict[str, Any]: The merged dictionary state.
    """
    merged = dict(existing) if existing else {}
    merged.update(new or {})
    return merged


def replace_dict(existing: dict[str, Any], new: Any) -> Any:
    """
    Replaces the existing dictionary with a new dictionary.

    This function logs the state update and ensures that the old state is replaced
    with the new one.

    Args:
        existing (Dict[str, Any]): The current dictionary state.
        new (Dict[str, Any]): The new dictionary state to replace the existing one.

    Returns:
        Dict[str, Any]: The updated dictionary state.

    """
    # If new is not a mapping, just replace existing value outright
    if not isinstance(new, Mapping):
        return new
    # In-place replace: clear existing mapping and update with new entries
    existing.clear()
    existing.update(new)
    return existing


class GraphState(AgentState):
    """
    Central state container for the entire agent pipeline.

    Design goals:
    - LLM-safe (structured, validated)
    - serializable (JSON-ready)
    - extensible (artifacts + metadata)
    - debuggable (trace log)
    """

    remaining_steps: RemainingSteps
    # Input / Output
    raww_input: Annotated[Any, replace_dict]
    final_output: Any
    # Pipeline stages
    retrieved_data: Annotated[Any, merge_dict]
    validated_data: Annotated[Any, replace_dict]
    repaired_data: Annotated[Any, merge_dict]

    # Error handling
    errors: Annotated[list[str], merge_dict]

    # Flexible artifact store
    # (LLM/tool outputs, agent memory, etc.)
    artifacts: dict[str, Any]

    # Metadata (run config, model info, etc.)
    metadata: dict[str, Any]
    llm_model: BaseChatModel
