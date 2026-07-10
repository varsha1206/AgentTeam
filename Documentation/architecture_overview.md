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
- RuleExecutor
- Typed communication models
- Medallion storage architecture
- Structured reporting
- Deterministic transformation execution
- Inferred-column resolution for transformation rules
- Structured ErrorReport routing for repair-safe validation

In Progress

- Repair Agent redesign
- Hybrid plugin generation
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
