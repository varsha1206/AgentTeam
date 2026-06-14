# retrieval_agent.py

import logging
import warnings

from langchain.tools import tool
from langchain_core.language_models.chat_models import BaseChatModel

with warnings.catch_warnings():
    warnings.simplefilter("ignore", DeprecationWarning)
    from langgraph.prebuilt import (
        create_react_agent,  # still required by create_supervisor
    )


logging.basicConfig()
logger = logging.getLogger(__name__)


def retrieval_agent_app(llm_model: BaseChatModel):
    """
    Builds and returns a compiled LangGraph Pregel app for the retrieval agent.
    Required by create_supervisor which expects list[Pregel].
    """

    @tool
    def read_csv() -> dict:
        """Read data from a CSV file."""
        logger.info("Reading CSV file...")
        return {"data": "CSV data"}

    agent = create_react_agent(
        model=llm_model,
        tools=[read_csv],
        prompt="You are a data retrieval agent.",
        name="retrieval_agent",  # required for supervisor routing/handoff
    )

    return agent
