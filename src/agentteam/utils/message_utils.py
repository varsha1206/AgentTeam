"""Message extraction utilities for orchestrator nodes."""

from langchain_core.messages import AIMessage


def extract_tool_outputs(messages: list) -> list[str]:
    """Extract all tool output contents from a message list."""
    return [m.content for m in messages if hasattr(m, "type") and m.type == "tool"]


def extract_last_ai_message(messages: list) -> str:
    """Extract the content of the last AI message."""
    last_ai = next(
        (m for m in reversed(messages) if isinstance(m, AIMessage)),
        None,
    )
    if last_ai is None:
        return ""
    content = last_ai.content
    if isinstance(content, str):
        return content
    return "\n".join(item if isinstance(item, str) else str(item) for item in content)


def extract_path_from_outputs(tool_outputs: list[str], *keywords: str) -> str | None:
    """Find the first tool output containing all keywords that looks like a file path."""
    for output in tool_outputs:
        output_str = str(output).strip()
        if (
            all(kw in output_str for kw in keywords)
            and "\n" not in output_str
            and len(output_str) < 300
        ):
            return output_str
    return None
