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
- Added quarantine_layer, repair_target, repair_error, repair_attempts to GraphState
- Added output/quarantine/ to workspace structure
- Created configs/validation_rules.yaml with global rules and per-file overrides
- Validator now produces two scripts per file: transformation_<filename>.py and validation_<filename>.py
- Transformation script splits rows into temp/transformed_<filename>.csv (valid) and output/quarantine/ (bad rows with quarantine_reason column)
- Validation script reads temp file and asserts schema rules, promotes to silver on PASS
- Added TransformationReport and write_transformation_report — logs every transformation applied, rows affected, and reason
- Added AgentInstruction structured model — orchestrator sends typed instructions to every agent at invocation time instead of raw f-strings
- Added DataSource structured model — retrieval agent receives source type, path, and output filename via AgentInstruction
- execute_script now validates JSON output before returning — returns SCRIPT_FAILED if script runs but prints non-JSON, preventing agent from spawning diagnostic scripts
- Orchestrator discovers input files itself and sends one AgentInstruction per file to retrieval agent
- Validator node clears stale validation and transformation reports at start of each run

### Rule Executor Refactor

- Introduced deterministic RuleExecutor to execute known transformation rules without LLM involvement
- Refactored transformation execution from generated Python scripts to deterministic Python functions
- Every supported TransformationRule now maps directly to a registered operation
- Added registry pattern so transformation operations can be registered dynamically
- RuleExecutor applies transformations sequentially according to FileValidationRules
- LLM now produces FileValidationRules only; execution is handled entirely by deterministic code
- Transformation logic is now independently unit-testable without requiring an LLM
- Separation established between intelligent planning (LLM) and deterministic execution (RuleExecutor)
- Began redesign of Repair Agent to modify FileValidationRules instead of patching generated Python scripts
- Designed hybrid execution architecture where unsupported transformations can later be generated as reusable plugins by the LLM while supported operations remain deterministic

## Architecture


- **Orchestrator** — custom StateGraph, owns routing logic, wraps each agent in a node that writes to GraphState
- **RetrievalAgent** — create_react_agent, tools: list_input_files, write_script, execute_script
- **RetrievalTools** — plain Python class, all file IO, independently testable without LLM
- **ValidatorAgent** — create_react_agent responsible for rule inference and validation workflow
- **RuleExecutor** — deterministic transformation engine applying registered TransformationRules without LLM execution
- **Structured outputs** — GeneratedScript, RetrievalResult, RoutingDecision, ValidationReport, TransformationReport, FileValidationRules, AgentInstruction
- **GraphState** — shared Pydantic state: raw_input, retrieved_data, validated_data, repaired_data, bronze_layer, silver_layer, errors, artifacts, metadata
- **Workspace** — input/, output/bronze/, output/silver/, output/quarantine/, generated/, logs/, temp/
- **Config** — Hydra YAML per agent (system_prompt, temperature, max_iterations)
- **TransformationReport** — structured log per file: transformations applied, rows affected, reason, inferred vs user-defined rules
- **AgentInstruction** — typed instruction sent by orchestrator to every agent: task, source, target_file, script_to_repair, errors, context
- **DataSource** — describes how to read a source: source_type (csv/json/api), path/url, headers, params, output_filename
- **Medallion layers** — bronze (raw, immutable), temp (transformed), silver (validated), quarantine (failed rows + reason)

## Architectural Decisions


- Dropped langgraph_supervisor — tools and agents had no way to write to shared GraphState fields, only messages. Switched to custom StateGraph for full state control and thesis transparency.
- Hybrid code generation (Option A + B) — tool-based as baseline, code-generating as research contribution. Direct comparison between the two becomes the thesis experiment.
- LLM-based routing with rule-based fallback — robust against LLM failures, and the two strategies can be compared in thesis evaluation.
- Structured outputs via Pydantic — enforces contract between agents, makes parsing reliable, every agent result is typed and testable.
- Prompt caching via Anthropic beta header — system prompts sent on every API call, caching reduces token cost.
- Bronze/silver layered output structure — bronze holds raw retrieval output, silver holds validated data. Mirrors standard data engineering medallion architecture.
- Per-file validation loop instead of batch validation — prevents cross-contamination of validation results.
- AgentInstruction pattern — orchestrator communicates intent via typed Pydantic models instead of prompt-generated strings.
- DataSource abstraction — source reading logic is model-driven rather than prompt-driven, enabling future JSON/API support.
- execute_script enforces JSON contract at tool level rather than relying on prompt instructions.
- Transformation before validation — Bronze remains immutable while transformed data is validated before promotion.
- TransformationReport alongside ValidationReport — provides complete audit trail for thesis evaluation.
- RuleExecutor separates intelligent planning from deterministic execution, making transformation behaviour reproducible, testable, and independent of LLM variability.
- Registry-based transformation execution enables future extension through plugins without modifying the execution engine.
- Planned hybrid execution model — deterministic operations executed by RuleExecutor, unsupported transformations generated as reusable plugins by the LLM.

## Challenges


- create_agent returns a chain not a Pregel — switched to create_react_agent
- remaining_steps required in GraphState by LangGraph when using create_react_agent
- llm_model in GraphState broke MemorySaver serialization
- Windows cp1252 encoding caused Unicode failures in generated scripts
- Agent hallucinated missing directories instead of checking filesystem
- LLM exceeded iteration limits and repeatedly regenerated scripts
- Validator conflated multiple files into a single validation call
- validation_report.json overwritten instead of appended
- Diagnostic script generation increased latency and consumed unnecessary tokens
- Employee dataset quarantined entirely because nullable assumptions were too strict
- Context overflow caused by passing quarantine CSV through LLM context
- Retrieval script naming included file extensions
- Generated transformation scripts became increasingly difficult to validate, maintain and repair, motivating the migration toward deterministic RuleExecutor execution
