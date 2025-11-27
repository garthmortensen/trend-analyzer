# Trend Decomposition Agent

## First-Time Setup

### Installation

First clone and setup aca_health repo, and then:

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

## Top-down flowchart

The project workflow is illustrated by the following flowchart.

```mermaid
flowchart TD
    %% Simplified overview: setup, core tools, iterative loop

    subgraph Setup
        A[Start] --> C[Load config]
        C --> D{DB ready?}
        D -->|yes| E[Reflect tables]
    end

    %% Load Tools (Option B condensed list)
    subgraph Load Tools
            E --> T1[get_trend_data]
            T1 --> T2[list_dims]
            T2 --> T3[dim_values]
            T3 --> T4[save_csv]
            T4 --> R1[run_analysis_sync]
            E -.-> U1[ai_runner.ask]
        end

    subgraph Loop
        direction LR
        R1 --> L0
        L0[loop i=1..N] --> L1[HYPOTHESIZE make_analysis_prompt]
            L1 --> L2[QUERY get_trend_data]
        L2 --> L3[RESULTS rows+sql]
        L3 --> L4[ANALYZE interpret metrics]
        L4 --> L5[REFINE next dims/filters]
        L5 --> L6[RECORD save_query_to_csv_tool]
        L6 --> L7{i < N ?}
        L7 -- yes --> L1
    end

    L7 -- no --> O1[Synthesize]
    O1 --> O2[Write report]

    classDef decision fill:#944,stroke:#333,stroke-width:2px,color:#fff
    class D,L7 decision
```

    Note: The app does not auto-create tables. If missing, run the SQL in `database/*.sql` to create `agg_trend_descriptor` and `agg_trend_normalizer` before analysis.
    Phases legend: HYPOTHESIZE = form next analytical question; QUERY = fetch grouped data; RESULTS = raw rows + compiled SQL; ANALYZE = interpret PMPM/mix shifts; REFINE = choose new dimensions or filters; RECORD = persist snapshot (CSV) for provenance; loop continues while i < N.