# AgentTeam — Development Log

## Project: LLM-powered multi-agent data ingestion pipeline
## Stack: Python, LangGraph, LangChain, Anthropic Claude, Hydra, Pydantic


## Progress


- Set up project structure, uv environment, Anthropic API
- Built GraphState using Pydantic with merge/replace reducers
- Built Orchestrator with custom StateGraph (replaced langgraph_supervisor)
- Built RetrievalAgent using create_react_agent with workspace-scoped tools
- Retrieval agent generates a Python script, executes it via subprocess, writes output CSV
- Structured outputs (Pydantic) enforced for all agent results and routing decisions
- Prompt caching enabled on all system prompts
- Full pipeline runs end-to-end: input CSV → generated script → output CSV → GraphState updated
- Routing decision after retrieval is LLM-based with rule-based fallback



## Architecture


- **Orchestrator** — custom StateGraph, owns routing logic, wraps each agent in a node that writes to GraphState
- **RetrievalAgent** — create_react_agent, tools: list_input_files, write_script, execute_script
- **RetrievalTools** — plain Python class, all file IO, independently testable without LLM
- **Structured outputs** — GeneratedScript, RetrievalResult, RoutingDecision, ValidationReport
- **GraphState** — shared Pydantic state: raw_input, retrieved_data, validated_data, repaired_data, errors, artifacts, metadata
- **Workspace** — input/, output/, generated/, logs/, temp/
- **Config** — Hydra YAML per agent (system_prompt, temperature, max_iterations)



## Architectural Decisions


- Dropped langgraph_supervisor — tools and agents had no way to write to shared GraphState fields, only messages. Switched to custom StateGraph for full state control and thesis transparency.
- Hybrid code generation (Option A + B) — tool-based as baseline, code-generating as research contribution. Direct comparison between the two becomes the thesis experiment.
- LLM-based routing with rule-based fallback — robust against LLM failures, and the two strategies can be compared in thesis evaluation.
- Structured outputs via Pydantic — enforces contract between agents, makes parsing reliable, every agent result is typed and testable.
- Prompt caching via Anthropic beta header — system prompts sent on every API call, caching reduces token cost by 90%.



## Challenges


- create_agent returns a chain not a Pregel — had to switch to create_react_agent
- remaining_steps required in GraphState by LangGraph 1.2.5 when using create_react_agent
- llm_model in GraphState broke MemorySaver serialization — removed from state
- Windows cp1252 encoding — LLM generated ✓ in scripts, broke file writes and subprocess.
- Agent not calling tools — hallucinated directory missing without checking.Fixed with explicit MANDATORY instruction in system prompt
- Script running twice — LLM hit max_iterations and looped. Fixed with explicit stop instructions in prompt
