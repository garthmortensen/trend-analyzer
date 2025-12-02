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

## Illustrations

### Sequence diagram: detail low

```mermaid
sequenceDiagram
    autonumber
    participant U as User
    participant M as Model
    participant T as Tool

    Note over M,T: 1) Tool definitions provided

    U->>M: "Explain IP cost drivers 2023→2024"
    M->>T: get_trend_data_tool
    T->>M: data payload
    Note over M: Plans next step

    M->>T: save_cached_result_tool
    T->>M: saved_csv reference
    Note over M: Data saved

    M->>U: Final explanation
    Note over U,M: Loop ends
```


### Sequence diagram: detail high

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

### Top-down flowchart

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

The code uses iterations 1-(n-3) for data exploration, and with the final 3 iterations, synthesizes and finalizes.

```mermaid
gantt
    title Analysis Iteration Phases
    dateFormat X
    axisFormat %s
    section Iteration 1
    EXPLORATION Phase : 1, 2
    section Iteration 2
    EXPLORATION Phase : 2, 3
    section Iteration 3
    EXPLORATION Phase : 3, 4
    section Iteration 4
    EXPLORATION Phase : 4, 5
    section Iteration 5
    EXPLORATION Phase : 5, 6
    section Iteration 6
    EXPLORATION Phase : 6, 7
    section Iteration 7
    PRE_FINAL Phase : 7, 8
    section Iteration 8
    SYNTHESIS Phase : 8, 9
    section Iteration 9
    FINAL Phase : 9, 10
    section Iteration 10
    FINAL Phase : 10, 11
```