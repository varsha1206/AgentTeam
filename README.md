# AgentTeam

AgentTeam is a multi-agent system designed to autonomously execute, validate, and repair data ingestion pipelines. The system focuses on structured data sources (CSV, JSON, APIs) and introduces self-healing capabilities through LLM-assisted debugging, reducing the need for manual intervention during pipeline execution.

---

## Overview

Modern data workflows often require reliable ingestion pipelines that can handle inconsistent, malformed, or incomplete data. AgentTeam addresses this by combining multiple specialized agents that collaboratively:

* Retrieve data from structured sources
* Validate data against predefined quality checks
* Detect and diagnose failures
* Repair pipeline errors using LLM-assisted reasoning
* Re-execute tasks until successful or retry limits are reached

The output is a validated dataset stored in a structured format, ready for downstream processing.

---

## Architecture

AgentTeam follows a modular multi-agent design:

* **Orchestrator**

  * Coordinates pipeline execution
  * Manages retry logic and execution state

* **Data Retrieval Agent**

  * Extracts data from CSV, JSON, or APIs

* **Validator/Tester Agent**

  * Performs schema and data quality checks
  * Detects failures and inconsistencies

* **Repair Agent**

  * Uses LLMs to diagnose and fix errors
  * Iteratively refines pipeline execution

---

## Execution Flow

```text
Orchestrator
    ↓
Data Retrieval Agent
    ↓
Validator Agent
    ↓ (if failure)
Repair Agent → back to Validator
    ↓ (if success)
Store Data
```

---

## Key Features

* Multi-agent coordination for pipeline execution
* Automated failure detection using validation rules
* LLM-assisted debugging and repair
* Controlled retry mechanism to prevent infinite loops
* Modular and extensible architecture

---

## Evaluation Strategy

The system is evaluated using a controlled experimental setup:

* Multiple ingestion pipelines (CSV/JSON/API)
* Injected failure scenarios:

  * Schema mismatches
  * Missing values
  * Data type inconsistencies
  * Malformed inputs
* Metrics:

  * Pipeline success rate
  * Failure detection rate
  * Repair success rate
  * Number of repair iterations
  * Human intervention frequency

---

## Installation

```bash
git clone https://github.com/your-username/AgentTeam.git
cd AgentTeam
pip install -r requirements.txt
```

---

## Scope

This project focuses on:

* Structured data ingestion pipelines
* Small-scale datasets (CSV/JSON)
* Controlled failure scenarios
* Semi-autonomous execution with retry limits

Out of scope:

* Large-scale distributed systems
* Real-time streaming pipelines
* Unstructured data (images, text corpora)
* Production deployment

---

## Goal

The goal of AgentTeam is to demonstrate how multi-agent systems combined with LLM-assisted debugging can enable self-healing data pipelines, improving reliability while reducing human intervention.

---

## License

MIT License
