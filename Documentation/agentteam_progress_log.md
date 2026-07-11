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
- Added InferredColumn structured model and validator-side inference of transformation columns from sample data
- Added ErrorReport structured model so operational failures are tracked separately from validation violations
- Split validation violations from validation errors so repair routing only triggers on explicit repair-worthy failures
- Added AgentInstruction structured model — orchestrator sends typed instructions to every agent at invocation time instead of raw f-strings
- Added DataSource structured model — retrieval agent receives source type, path, and output filename via AgentInstruction
- execute_script now validates JSON output before returning — returns SCRIPT_FAILED if script runs but prints non-JSON, preventing agent from spawning diagnostic scripts
- Orchestrator discovers input files itself and sends one AgentInstruction per file to retrieval agent
- Validator node clears stale validation and transformation reports at start of each run
- Built RepairAgent using create_react_agent with repair-scoped tools
- Repair agent detects script crashes via structured SCRIPT_FAILED JSON responses tagged with stage field
- All execute_script calls across retrieval, transformation, and validation now return consistent structured JSON on failure: {SCRIPT_FAILED, stage, error, script_path}
- RetrievalNode and ValidationNode both detect SCRIPT_FAILED in tool outputs and populate repair_target, repair_error, repair_script_path in GraphState
- Repair routing returns to originating agent after successful repair — retrieval failures route back to retrieval, validation/transformation failures route back to validation
- Repair capped at configurable max attempts, pipeline terminates cleanly with structured failure report on exhaustion
- Added PluginRegistry — loads, saves, and registers LLM-generated transformation plugins from workspace/plugins/
- Added ExecutionPlanner — classifies each TransformationRule as built_in, plugin, or needs_generation before execution
- Plugins follow same function signature as built-in operations: def <operation>(df, rule) -> pd.DataFrame
- LLM generates plugins only when operation is not in RuleExecutor registry and not already cached in workspace/plugins/
- Plugins are saved to disk and reloaded on startup — LLM only generates once per operation, reused on all future runs
- Quarantine moved from transformation stage to validation script — transformation now produces clean temp file, validation script splits rows into silver and quarantine
- Validation script writes silver and quarantine directly — LLM generates row-level assertions, valid rows promoted, bad rows quarantined with quarantine_reason column
- Added YamlTransformationRule and YamlValidationRules structured models — YAML parsed into typed Pydantic models before conversion to FileValidationRules, with ColumnInference marker for infer: true columns
- Added ExecutionLogger — writes structured execution events to workspace/logs/execution_log.json, repair agent reads this for full pipeline context before deciding how to repair
- Refactored orchestrator into BaseAgentNode and BaseRouter in utils/base_node.py — all agent nodes inherit standard invocation, instruction building, and repair detection
- _detect_repair_needed moved to BaseAgentNode — shared across retrieval and validation nodes, stage identified from structured SCRIPT_FAILED tag not keyword inference
- Moved all nodes to src/agentteam/nodes/ — retrieval_node.py, validation_node.py, repair_node.py each contain node class and router class

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
- Added repair-safe validation flow so dataset violations do not automatically trigger repair
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
- **RepairAgent** — create_react_agent, reads execution log and failing scripts, patches scripts or generates plugins to fix failures
- **RepairTools** — read_execution_log, read_script, write_script, execute_script, read_rules_cache, update_rules_cache, run_executor
- **PluginRegistry** — loads/saves/registers LLM-generated plugins from workspace/plugins/, reloads on startup
- **ExecutionPlanner** — classifies TransformationRules as built_in/plugin/needs_generation, orchestrates hybrid execution
- **ExecutionLogger** — append-only structured event log per run written to workspace/logs/execution_log.json
- **BaseAgentNode** — base class for all orchestrator nodes: standard invocation, AgentInstruction building, repair detection
- **BaseRouter** — base class for all routers: structured LLM routing with rule-based fallback
- **Workspace** — input/, output/bronze/, output/silver/, output/quarantine/, generated/, plugins/, logs/, temp/

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
- Inferred-column resolution keeps transform planning flexible without giving up deterministic execution.
- ErrorReport provides a typed boundary between operational failures and data-quality violations.
- Planned hybrid execution model — deterministic operations executed by RuleExecutor, unsupported transformations generated as reusable plugins by the LLM.
- Stage-tagged SCRIPT_FAILED responses — every execute_script returns structured JSON with stage field on failure, eliminating keyword inference on error strings for repair routing
- Repair detection in BaseAgentNode — shared across all nodes, extensible by adding one entry to stage_detectors, no duplication
- Plugin caching in workspace/plugins/ — LLM generates a plugin once, PluginRegistry reloads it on all future runs without LLM calls
- Quarantine in validation not transformation — transformation produces a clean DataFrame, validation script decides which rows pass based on ColumnRules, keeping concerns cleanly separated
- ExecutionLogger as repair context — repair agent reads structured execution history rather than inferring context from script contents or error messages alone
- InferColumn helps TransformationRule to understand which columns to work on, if not all columns were used

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
- Repair agent could not distinguish which stage failed — fixed by tagging all SCRIPT_FAILED responses with stage field in structured JSON
- Plugin cached from previous run contained wrong logic — fixed by deleting stale plugins and regenerating; plugins now versioned by operation name
- coerce_numeric wiped string columns by defaulting to all columns when columns list was None — fixed by enforcing explicit column lists using InferColumn
- 100% quarantine detection removed from repair triggers — quarantine rate is a data quality outcome not a pipeline failure, repair should only fire on script crashes

