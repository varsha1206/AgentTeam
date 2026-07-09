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
- infer missing validation rules
- produce FileValidationRules

The validator decides **what** should happen.

It does **not** execute transformations.

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
