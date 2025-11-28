# Trend Decomposition Agent

## About

This project is an AI-assisted healthcare claims trend analyzer that decomposes period-over-period PMPM changes into concrete drivers and opportunities. It reflects two prebuilt PostgreSQL cubes (descriptor and normalizer) via SQLAlchemy, then runs an iterative agent loop to hypothesize, query, interpret, refine, and record findings. Outputs include a structured markdown report and optional CSV snapshots of key drill-downs for reproducibility.

While the AI is limited to working with constrained tools to provide guardrails, all intermediate and final output should be validated.

## TODO: Increase personal confidence in agent

Objective: achieve results that are reliable, traceable, auditable, and easy to review.

1. Signal injection: Add a synthetic PMPM spike (e.g., Georgia + ICD [A98.4](https://www.google.com/search?q=A98.4) (Ebola)) to confirm the agent flags it, explains cause (mix vs unit cost), and suggests action.

2. Provenance: For every iteration save a JSON manifest (iteration, prompt, filters, group_by, SQL, row count, sample hash).
3. Simple stats: Attach % change, z‑score, and a volume flag to each driver. Mark low-volume findings as tentative.

4. Coverage: Track which dimensions/values were queried to reduce redundant analyses and improve coverage. Highlight high‑spend segments not touched. Track what seed data is inserted, when, and update analyses upon ETL.

5. Reviewer notes: Persist human feedback; feed back next run to avoid repeating retired drivers.

## First-Time Setup

### Installation

First clone and setup [aca_health repo](https://github.com/garthmortensen/aca_health), and then:

```bash
# 1. Clone and setup
git clone <repository-url>
cd trend-analyzer

# 2. Configure environment
cp .env.example .env

# 3. Install uv and dependencies
curl -LsSf https://astral.sh/uv/install.sh | sh
uv sync

# 4. Run
uv run python -m trend_analyzer
```

## Top-down flowchart/

The project workflow is illustrated by the following flowchart.

```mermaid
flowchart TD
    %% Simplified overview: setup, core tools, iterative loop (with SDK/API tags)

        subgraph Setup
            A[Start] --> C[Load config]
            C --> D{DB ready?}
            D -->|yes| E[Reflect tables - SQLA]
        end

    %% Load Tools (Option B condensed list)
        subgraph Load Tools
            E --> T1[get_trend_data - SQLA]
            T1 --> T2[list_dims - SQLA]
            T2 --> T3[dim_values - SQLA]
            T3 --> T4[save_csv - CSV]
            T4 --> R1[run_analysis_sync]
            E -.-> U1[ai_runner.ask - LLM]
        end

    subgraph Loop
        direction LR
        R1 --> L0
        L0[loop i=1..N] --> L1[HYPOTHESIZE make_analysis_prompt - LLM]
        L1 --> L2[QUERY get_trend_data - SQLA]
        L2 --> L3[RESULTS rows+sql]
        L3 --> L4[ANALYZE interpret metrics - LLM]
        L4 --> L5[REFINE next dims/filters]
        L5 --> L6[RECORD save_query_to_csv_tool - CSV]
        L6 --> L7{i < N ?}
        L7 -- yes --> L1
    end

    L7 -- no --> O1[Synthesize]
    O1 --> O2[Write report]

    classDef decision fill:#944,stroke:#333,stroke-width:2px,color:#fff
    class D,L7 decision
```

## Agent loop sequence

```mermaid
sequenceDiagram
    autonumber
    participant User
    participant Runner as run_analysis_sync
    participant Agent
    participant Tools
    participant DB as PostgreSQL (SQLAlchemy)
    participant OpenAI as OpenAI SDK
    participant FS as Filesystem

    User->>Runner: start(iterations=N)
    loop i=1..N
        Runner->>Agent: make_analysis_prompt [LLM]
        Agent->>OpenAI: generate hypothesis
        OpenAI-->>Agent: prompt text

        Agent->>Tools: get_trend_data
        Tools->>DB: SELECT via SQLAlchemy
        DB-->>Tools: rows + compiled SQL
        Tools-->>Agent: results

        Agent->>OpenAI: interpret metrics [LLM]
        OpenAI-->>Agent: insights / next dims+filters

        Agent->>Tools: save_query_to_csv
        Tools->>FS: write CSV
        FS-->>Tools: ok

        Agent->>Runner: continue?
        Runner-->>Agent: i < N ?
    end

    Agent->>Runner: synthesize findings
    Runner->>FS: write report
```

