"""Structured result parsers for orchestrator nodes."""

import logging
from typing import cast

from langchain_core.messages import HumanMessage

from agentteam.models.structured_outputs import (
    RepairResult,
    RetrievalResult,
    ValidatorResult,
)
from agentteam.utils.message_utils import (
    extract_last_ai_message,
    extract_path_from_outputs,
    extract_tool_outputs,
)

logger = logging.getLogger(__name__)


def parse_retrieval_result(messages: list, structured_llm) -> RetrievalResult:
    """Uses structured LLM output to extract RetrievalResult from agent messages."""
    tool_outputs = extract_tool_outputs(messages)
    summary = extract_last_ai_message(messages)
    try:
        result = cast(
            RetrievalResult,
            structured_llm.invoke(
                [
                    HumanMessage(
                        content=(
                            f"Extract the retrieval result from the following agent output.\n\n"
                            f"Agent summary:\n{summary}\n\n"
                            f"Tool outputs:\n{chr(10).join(tool_outputs)}\n\n"
                            f"Extract: status, summary, script_path, output_path, errors."
                            f'errors must be a JSON array of strings, e.g. [] or ["error1"].\n'
                            f"Never return errors as a plain string."
                        )
                    )
                ]
            ),
        )
        return result
    except Exception as e:
        logger.warning(f"Structured extraction failed, using fallback: {e}")
        return _fallback_parse_retrieval(summary, tool_outputs)


def _fallback_parse_retrieval(summary: str, tool_outputs: list[str]) -> RetrievalResult:
    script_path = extract_path_from_outputs(
        tool_outputs, "generated", "retrieval", ".py"
    )
    output_path = extract_path_from_outputs(tool_outputs, "output", ".csv")
    status = "complete" if output_path else "failed"
    return RetrievalResult(
        status=status,
        summary=summary,
        script_path=script_path,
        output_path=output_path,
        errors=[] if status == "complete" else ["No output CSV produced."],
    )


def parse_validator_result(messages: list, structured_llm) -> ValidatorResult:
    """Uses structured LLM output to extract ValidatorResult from agent messages."""
    tool_outputs = extract_tool_outputs(messages)
    summary = extract_last_ai_message(messages)
    try:
        result = cast(
            ValidatorResult,
            structured_llm.invoke(
                [
                    HumanMessage(
                        content=(
                            f"Extract the validation result from the following agent output.\n\n"
                            f"Agent summary:\n{summary}\n\n"
                            f"Tool outputs:\n{chr(10).join(tool_outputs)}\n\n"
                            f"Extract: status, validation_outcome, script_path, report_path, errors, summary."
                        )
                    )
                ]
            ),
        )
        return result
    except Exception as e:
        logger.warning(f"Structured validator extraction failed, using fallback: {e}")
        return _fallback_parse_validator(summary, tool_outputs)


def _fallback_parse_validator(summary: str, tool_outputs: list[str]) -> ValidatorResult:
    script_path = extract_path_from_outputs(
        tool_outputs, "generated", "validation", ".py"
    )
    report_path = extract_path_from_outputs(
        tool_outputs, "logs", "validation_report.json"
    )
    validation_outcome = (
        "FAIL" if any("ERROR" in o or "FAIL" in o for o in tool_outputs) else "PASS"
    )
    return ValidatorResult(
        status="complete",
        validation_outcome=validation_outcome,
        script_path=script_path,
        report_path=report_path,
        errors=[],
        summary=summary,
    )


def parse_repair_result(messages: list, structured_llm) -> RepairResult:
    """Uses structured LLM output to extract RepairResult from agent messages."""
    tool_outputs = extract_tool_outputs(messages)
    summary = extract_last_ai_message(messages)
    try:
        result = cast(
            RepairResult,
            structured_llm.invoke(
                [
                    HumanMessage(
                        content=(
                            f"Extract the repair result from the following agent output.\n\n"
                            f"Agent summary:\n{summary}\n\n"
                            f"Tool outputs:\n{chr(10).join(tool_outputs)}\n\n"
                            f"Extract: status, script_path, output_path, errors, summary.\n"
                            f"errors must be a JSON array of strings."
                        )
                    )
                ]
            ),
        )
        return result
    except Exception as e:
        logger.warning(f"Structured repair extraction failed, using fallback: {e}")
        return _fallback_parse_repair(summary, tool_outputs)


def _fallback_parse_repair(summary: str, tool_outputs: list[str]) -> RepairResult:
    script_path = extract_path_from_outputs(tool_outputs, "generated", "repair", ".py")
    output_path = extract_path_from_outputs(tool_outputs, "temp", ".csv")
    status = "complete" if output_path else "failed"
    return RepairResult(
        status=status,
        script_path=script_path,
        output_path=output_path,
        errors=[] if status == "complete" else ["No repaired output produced."],
        summary=summary,
    )
