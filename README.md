# Trend Analyzer

This repository contains a prototype notebook that shows how to use a large language model (LLM) to analyze period‑over‑period trends in your own data. The included Jupyter notebook **Trend_Composition_Agent_Directors+_Demo.ipynb** demonstrates how to:

1. Build BigQuery tables from a YAML configuration describing dimensions, metrics and source tables.
2. Define a system prompt and analysis plan for a conversational agent.
3. Expose data‑access functions (SQL queries, dimension lookups, chart creation) as tools the agent can call.
4. Let the agent iteratively drill into the data, write findings to a Google Doc and generate charts.

## Running the demo

1. Open the notebook in Colab or Jupyter and install the required Python packages when prompted.
2. Provide your Google Cloud project IDs and authentication credentials so the BigQuery queries run correctly.
3. Modify `dimensions.yml` or the YAML cell in the notebook to point to your own claim and membership tables and to customize dimensions or metrics.
4. Execute the cells to build the normalized data tables and launch the agent. The agent will produce a step‑by‑step analysis of the 2023→2024 trend and write a summary to a Google Doc.

## Using this approach for your data

- Adapt the YAML configuration to describe the dimensions, metrics and tables in your data warehouse.
- Customize the analysis plan in the notebook to specify the question you want the LLM to answer. The default plan walks through a pyramid‑style drill‑down.
- Add or remove tool wrappers to expose whatever data queries or visualization functions are useful for your analysis.
- Run the notebook and monitor the agent as it iteratively queries your data and records findings.

**Important:** This is a proof of concept and may produce inaccurate or incomplete interpretations. Always review the generated analysis before relying on it.
