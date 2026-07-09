# Research Questions

1. RQ1: How can a multi-agent LLM system improve the robustness of data ingestion pipelines through automated self-healing?
2. RQ2: Which kinds of ingestion failures can be detected, diagnosed, and repaired reliably by LLM agents?
3. RQ3: Does a multi-agent setup outperform a single-agent or rule-based baseline in recovery speed, repair quality, and operational stability?
4. RQ4: How well do self-healing behaviors generalize across different pipeline components, failure types, and datasets?
5. RQ5: What is the cost-benefit tradeoff between better recovery and added latency / compute / token usage?

# Evaluation Plan

The evaluation should combine functional correctness, recovery performance, and efficiency so you can show the system works and is practical. A good evaluation plan also needs clear questions, data sources, and implementation steps so the results are interpretable.

## 1. Baselines

Compare against at least these systems:

- No-healing baseline: pipeline fails and requires manual intervention.
- Rule-based recovery: predefined retries, fallback parsing, schema fixes.
- Single-agent LLM repair: one model handles detection, diagnosis, and repair.
- Multi-agent LLM system: specialized agents for detection, diagnosis, repair, and verification.

## 2. Test Scenarios

Create a benchmark of realistic ingestion failures:

- Schema drift.
- Missing fields.
- Type mismatches.
- API timeouts.
- Malformed records.
- Duplicate or reordered events.
- Downstream validation failures.

## 3. Main Metrics

Use these as your core metrics:

- Detection accuracy: how often failures are identified correctly.
- Diagnosis accuracy: how often the root cause is localized correctly.
- Repair success rate: how often the pipeline is restored without human help.
- Time to recovery: how long the system takes to return to normal.
- Pipeline continuity: amount of data loss or dropped records.
- False repair rate: cases where the system claims success but the issue remains.
- Token / compute cost: operational overhead of the multi-agent setup.

## 4. Experimental Design

Run each failure case multiple times to capture variability. Compare:

- single-agent vs multi-agent
- direct repair vs explanation-then-repair
- with and without verification
- short vs long context memory for the agents

If possible, test across at least two ingestion settings: one batch pipeline and one streaming pipeline.

## 5. Analysis

Report:

- where the system heals well
- where it fails
- whether added agents actually improve repair quality
- whether verification reduces false fixes
- whether higher cost is justified by higher robustness
