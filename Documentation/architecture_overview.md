# AgentTeam Architecture Overview

## Philosophy

AgentTeam follows a **hybrid AI + deterministic architecture**.

Large Language Models are responsible for **reasoning and planning**, while deterministic Python components are responsible for **execution**.

The objective is to maximise:

- reproducibility
- testability
- auditability
- scalability

rather than allowing LLMs to execute arbitrary code for every processing task.

---

# High-Level Pipeline

```
                User
                  │
                  ▼
          Orchestrator Agent
                  │
     ┌────────────┴─────────────┐
     ▼                          ▼
 Retrieval Agent          Validation Agent
     │                          │
     ▼                          ▼
 Bronze Layer        FileValidationRules
                                │
                                ▼
                       RuleExecutor
                                │
                    ┌───────────┴───────────┐
                    ▼                       ▼
               Silver Layer          Quarantine
```

---

# Core Components

## Orchestrator

Responsibilities

- controls workflow execution
- manages GraphState
- discovers files
- routes work between agents
- issues typed AgentInstructions

The orchestrator contains no business logic.

---

## Retrieval Agent

Responsibilities

- ingest data
- generate retrieval scripts
- execute scripts
- populate Bronze layer

Produces immutable raw datasets.

---
## Repair Agent

Responsibilities

- detect script crashes in retrieval, transformation, and validation stages
- patch failing scripts for retrieval failures
- patch failing scripts for validation failures
- re-run execution after repair
- route back to the originating agent after successful repair

The repair agent operates on pipeline failures only.

It does not modify source data or business validation rules.

Repair is capped at a configurable maximum attempt count. If the maximum is reached the pipeline terminates with a structured failure report.

### Failure Detection

Every `execute_script` call across all agents returns a structured JSON failure object on error:

```json
{
  "SCRIPT_FAILED": true,
  "stage": "validation",
  "error": "...",
  "script_path": "..."
}
```

The stage field identifies which agent produced the failure. Detection logic in each node inspects tool outputs for this structure and sets `repair_target`, `repair_error`, and `repair_script_path` in GraphState. No keyword inference on error messages is used.

### Repair Routing

After repair completes the pipeline routes back to the originating agent:

- `repair_target: retrieval` → routes back to retrieval agent
- `repair_target: transformation` → routes back to validation agent
- `repair_target: validation` → routes back to validation agent
---

## Validation Agent

Responsibilities

- inspect dataset sample
- load user-defined validation rules
- infer missing validation rules and transformation columns
- produce FileValidationRules

The validator decides **what** should happen.

It does **not** execute transformations.

When a transformation rule uses infer-based selection, the validator resolves the most appropriate columns from a sample of the source file and writes explicit transformation rules before execution. This keeps planning in the LLM layer while the deterministic executor still receives concrete columns.

---

## RuleExecutor

Responsibilities

- execute supported transformations
- apply transformations deterministically
- quarantine invalid rows
- produce transformed dataframe

The RuleExecutor never calls an LLM.

Every execution is reproducible.

---

## Reporting

Every stage produces structured reports.

### ErrorReport

Records

- execution-stage failures
- quarantine-related repair signals
- whether the repair agent should act

ErrorReport is kept separate from validation violations so data-quality issues do not automatically trigger repair.

### TransformationReport

Records

- operations executed
- rows affected
- columns affected
- execution order
- reason

### ValidationReport

Records

- validation status
- validation errors
- promoted file
- row counts

Validation violations describe data-quality problems in the dataset. Validation errors describe operational failures such as script crashes or unrecoverable validation issues. Only structured errors with an explicit repair signal should route to the repair agent.

These reports provide a complete audit trail for evaluation.

---

# Design Principles

## Separation of Intelligence and Execution

LLMs decide:

- what rules apply
- what schema is expected
- which transformations are required

Python executes:

- transformations
- validation
- reporting
- promotion

---

## Typed Communication

All communication between agents uses Pydantic models.

Examples

- ErrorReport
- AgentInstruction
- DataSource
- FileValidationRules
- ValidationReport
- TransformationReport

No agent relies on free-form prompt parsing.

---

## Medallion Architecture

Bronze

- immutable raw data

Temp

- transformed working copy

Silver

- validated data

Quarantine

- rejected rows with reasons

---

## Registry-Based Execution

RuleExecutor uses a transformation registry.

Each supported operation maps to a deterministic Python function.

New operations can be registered without modifying the execution engine.

---

## Planned Hybrid Extension

Supported transformations

↓

RuleExecutor

Unsupported transformations

↓

LLM generates plugin

↓

Plugin validation

↓

Plugin registry

↓

Future executions reuse plugin without additional LLM calls

This allows the system to remain deterministic while still being extensible.

---

# Current Status

Completed

- Custom StateGraph orchestration
- Retrieval Agent
- Validation Agent
- Repair Agent
- RuleExecutor
- Typed communication models
- Medallion storage architecture
- Structured reporting
- Deterministic transformation execution
- Inferred-column resolution for transformation rules
- Structured ErrorReport routing for repair-safe validation
- Stage-tagged failure detection across all pipeline stages
- Repair routing back to originating agent

In Progress

- JSON and API ingestion
- Streamlit interface
- Comprehensive unit testing

---

# Architectural Rationale

The system intentionally limits LLM responsibilities to reasoning and planning while delegating execution to deterministic Python components.

This improves:

- reproducibility
- correctness
- security
- debugging
- testing
- scalability

while still allowing LLMs to contribute intelligent behaviour where deterministic programming alone would be insufficient.
