# Personalization Intelligence Layer

This module transforms raw enrichment data into actionable messaging inputs.

## Components

### ContextBuilder

The `ContextBuilder` class in `context_builder.py` is responsible for:

1.  **Ingesting Data**: Reads `score_breakdown` (from Scoring) and `risk_enrichment` (from Enrichment).
2.  **Extracting Intelligence**:
    *   **Agent Use Cases**: Identifies if the company is building core agents, using LLMs via API, or deploying production workflows.
    *   **Integrations**: Detects tools like LangChain, CrewAI, OpenAI, etc.
    *   **Compliance Exposure**: Maps industries and content to frameworks like HIPAA, SOC2, PCI-DSS.
    *   **Governance Gaps**: Identifies mismatches between agent maturity and security controls (e.g., Production Agents but missing Audit Logs).
3.  **Generating Narrative**: Creates a natural language summary paragraph tailored to the company's specific context.

## Output

The builder updates the `Company.signal_metadata` field with a `context_analysis` object:

```json
"context_analysis": {
    "integrations": ["LangChain", "OpenAI"],
    "compliance_exposure": ["HIPAA"],
    "governance_gaps": ["Missing Agent Audit Trails"],
    "agent_maturity": "production",
    "summary": "Acme Corp appears to be scaling production-grade agent workflows utilizing LangChain. However, operational risks around missing agent audit trails may expose the organization to HIPAA compliance issues."
}
```

This output is designed to be directly injected into email templates.
