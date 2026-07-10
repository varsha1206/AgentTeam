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
- Built ValidatorAgent using create_react_agent with workspace-scoped tools
- Restructured output/ into output/bronze/ and output/silver/ (medallion architecture)
- Retrieval agent writes raw files to bronze layer, populates bronze_layer list in GraphState by scanning filesystem after run
- Validator agent validates bronze layer files one at a time, looping per file rather than batch validating
- Validator generates a separate validation script per file (validation_<filename>.py)
- Validation results appended to a single validation_report.json (list of entries, one per file) instead of overwriting
- Files that pass validation are written to silver layer, tracked in silver_layer list in GraphState
- Added colorlog for colored console output, suppressed noisy httpx/anthropic INFO logs


## Architecture


- **Orchestrator** — custom StateGraph, owns routing logic, wraps each agent in a node that writes to GraphState
- **RetrievalAgent** — create_react_agent, tools: list_input_files, write_script, execute_script
- **RetrievalTools** — plain Python class, all file IO, independently testable without LLM
- **Structured outputs** — GeneratedScript, RetrievalResult, RoutingDecision, ValidationReport
- **GraphState** — shared Pydantic state: raw_input, retrieved_data, validated_data, repaired_data, bronze_layer, silver_layer, errors, artifacts, metadata
- **Workspace** — input/, output/bronze/, output/silver/, generated/, logs/, temp/
- **Config** — Hydra YAML per agent (system_prompt, temperature, max_iterations)



## Architectural Decisions


- Dropped langgraph_supervisor — tools and agents had no way to write to shared GraphState fields, only messages. Switched to custom StateGraph for full state control and thesis transparency.
- Hybrid code generation (Option A + B) — tool-based as baseline, code-generating as research contribution. Direct comparison between the two becomes the thesis experiment.
- LLM-based routing with rule-based fallback — robust against LLM failures, and the two strategies can be compared in thesis evaluation.
- Structured outputs via Pydantic — enforces contract between agents, makes parsing reliable, every agent result is typed and testable.
- Prompt caching via Anthropic beta header — system prompts sent on every API call, caching reduces token cost by 90%.
- Bronze/silver layered output structure — bronze holds raw retrieval output, silver holds validated data. Mirrors standard data engineering medallion architecture, gives a clean conceptual model for the thesis methodology chapter.
- Per-file validation loop instead of batch validation — each bronze file gets its own isolated agent call, preventing cross-contamination of validation results between files and producing per-file validation scripts and reports.


## Challenges


- create_agent returns a chain not a Pregel — had to switch to create_react_agent
- remaining_steps required in GraphState by LangGraph 1.2.5 when using create_react_agent
- llm_model in GraphState broke MemorySaver serialization — removed from state
- Windows cp1252 encoding — LLM generated ✓ in scripts, broke file writes and subprocess.
- Agent not calling tools — hallucinated directory missing without checking.Fixed with explicit MANDATORY instruction in system prompt
- Script running twice — LLM hit max_iterations and looped. Fixed with explicit stop instructions in prompt
- Validator was validating multiple files in one call and conflating results — fixed by passing one explicit file path per agent invocation instead of letting it discover files via list_output_files
- validation_report.json was being overwritten on each file — fixed by reading existing report, appending new entry, writing back as a list
