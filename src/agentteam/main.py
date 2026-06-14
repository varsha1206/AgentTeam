"""
main.py - Test entrypoint for the AgentTeam pipeline
"""

from langchain_core.runnables import RunnableConfig

from agentteam.agents.orchestrator_agent import build_app


def main():
    app = build_app()

    # GraphState extends AgentState (which extends MessagesState),
    # so it requires a "messages" key plus your custom fields
    initial_state = {
        "messages": [
            {"role": "user", "content": "Fetch the latest data from the CSV file."}
        ],
        "raww_input": "Fetch the latest data from the CSV file.",
        "final_output": None,
        "retrieved_data": {},
        "validated_data": {},
        "repaired_data": {},
        "errors": [],
        "artifacts": {},
        "metadata": {
            "run_id": "test-run-001",
            "environment": "local",
        },
    }

    config: RunnableConfig = {"configurable": {"thread_id": "test-thread-001"}}

    print("===== INVOKING AGENT PIPELINE =====")
    result = app.invoke(initial_state, config=config)  # type: ignore

    print("\n===== FINAL STATE =====")
    for key, value in result.items():
        print(f"\n[{key}]")
        print(value)


if __name__ == "__main__":
    main()
