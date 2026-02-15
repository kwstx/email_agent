# Ideal Customer Profile (ICP) - Operational Definition

This document translates the target customer for Engram into concrete, observable signals for automated discovery and scoring.

## 1. AI Agent & Workflow Signals
These signals indicate that the company is actively building, deploying, or scaling AI agents.

| Signal ID | Signal Name | Detection Source | Description | Points |
|-----------|-------------|------------------|-------------|--------|
| **AGN_KW** | Agent Keywords | Website Home/About | Mention of "AI Agents", "Autonomous Agents", "Agentic workflows". | 3 |
| **LLM_API** | LLM API Usage | Docs / Engineering Blogs | Reference to OpenAI, Anthropic, LangChain, CrewAI, PydanticAI, etc. | 3 |
| **AI_PROD** | AI Product Line | Product Pages | Dedicated AI features or autonomous modules in the product. | 2 |
| **DEV_TOOL** | Dev Tooling/APIs | Docs/GitHub | Providing automation platforms or developer tooling. | 2 |
| **INT_COP** | Internal Copilots | Blogs / Careers | Mentions of internal AI assistants or custom copilots. | 1 |

## 2. Company Market Positioning
These signals identify the nature of the business and its alignment with AI infrastructure needs.

| Signal ID | Signal Name | Detection Source | Description | Points |
|-----------|-------------|------------------|-------------|--------|
| **AI_NATV** | AI Native | LinkedIn / Crunchbase | Defined as an AI startup or AI infrastructure company. | 4 |
| **WKF_AUT** | Workflow Automation| Product / About | Core business is automation of processes/workflows. | 3 |
| **API_PLF** | API Platform | Docs / Homepage | API-first company or platform provider. | 2 |

## 3. Enterprise Risk & Sensitivity Signals
These signals indicate a high need for Engram's governance and security infrastructure.

| Signal ID | Signal Name | Detection Source | Description | Points |
|-----------|-------------|------------------|-------------|--------|
| **DATA_S** | Sensitive Data | Privacy Policy / Docs | Handles PHI, PII, PCI, or KYC data. | 4 |
| **COMP_L** | Compliance Certs | Security Page / Footer | Mentions SOC2, ISO 27001, HIPAA, GDPR, FedRAMP. | 3 |
| **REG_IND** | Regulated Vertical | About / LinkedIn | Operates in Finance, Healthcare, Gov, or Legal. | 3 |
| **ENT_RDY** | Enterprise Ready | Security Page | References audit logging, RBAC, SSO, or SLA. | 4 |
| **PRV_CLD** | Private Deployment | Pricing / Docs | Offers On-premises, Private Cloud, or VPC deployment. | 4 |
| **ENT_FOC** | Enterprise Focus | Pricing Page | Has an "Enterprise" tier or serves Fortune 500. | 2 |

## 4. Scoring Framework

Companies are scored automatically based on the sum of detected signals.

*   **Tier 1 (High Fit): 15+ Points**
    *   *Action:* Direct outbound via high-priority technical decision makers.
*   **Tier 2 (Medium Fit): 8-14 Points**
    *   *Action:* Nurture via content; monitor for new AI deployment signals.
*   **Tier 3 (Low Fit): <8 Points**
    *   *Action:* Discard or move to low-frequency monitoring.

## 5. Technical Detection Targets

| Target | Specific Patterns to Find |
|--------|---------------------------|
| **Website Text** | "agentic", "autonomous", "orchestration", "chain of thought", "memory" |
| **Documentation** | API keys, `/v1/chat/completions`, `langchain`, `vector database`, `embedding` |
| **GitHub** | `.github/workflows` containing LLM scripts, public agent-related repos |
| **Infrastructure** | "Air-gapped", "Docker/Kubernetes" (for self-hosting hints), "VPC" |
