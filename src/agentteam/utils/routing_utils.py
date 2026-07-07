"""Routing utilities for orchestrator edge conditions."""

import logging
from typing import cast

from langchain_core.messages import HumanMessage

from agentteam.models.structured_outputs import (
    RetrievalResult,
    RoutingDecision,
    ValidatorResult,
)

logger = logging.getLogger(__name__)


def decide_routing(
    result: RetrievalResult | ValidatorResult,
    structured_llm,
    routing_prompt_template: str,
) -> RoutingDecision:
    """Uses structured LLM output to decide the next node."""
    try:
        decision = cast(
            RoutingDecision,
            structured_llm.invoke(
                [
                    HumanMessage(
                        content=routing_prompt_template.format(
                            status=result.status,
                            summary=result.summary,
                            errors=result.errors,
                        )
                    )
                ]
            ),
        )
        logger.info(f"Routing decision: {decision.next_node} — {decision.reason}")
        return decision
    except Exception as e:
        logger.warning(f"Structured routing failed, using fallback: {e}")
        return _fallback_routing(result)


def _fallback_routing(result: RetrievalResult | ValidatorResult) -> RoutingDecision:
    if result.status == "complete":
        return RoutingDecision(
            next_node="end",
            reason="Agent completed successfully.",
        )
    return RoutingDecision(
        next_node="end",
        reason=f"Agent failed: {result.errors}",
    )
