# Ideal Customer Profile (ICP) - Operational Definition

This document translates the target customer for Engram into concrete, observable signals for automated discovery and scoring.

## 1. Scoring Dimensions

Companies are evaluated across five key dimensions to determine fit:

| Dimension | Weight | Description |
|-----------|--------|-------------|
| **Agent Deployment Intensity** | High | Usage of production agent systems, autonomous workflows, and LLM APIs. |
| **Security Posture** | Medium | Compliance certifications, enterprise readiness (RBAC, SSO), and private cloud offerings. |
| **Industry Risk Level** | Medium | Presence in regulated verticals and handling of sensitive data (PII, PHI). |
| **Hiring Activity** | High | Active job postings for AI, ML, and automation engineering roles. |
| **Dev Platform Maturity** | Low | API platforms, SDKs, and developer-centric tooling/documentation. |

## 2. Scoring Framework

Companies are categorized into tiers based on their total score:

*   **Tier 1: High Priority (15+ Points)**
    *   *Action:* Immediate technical outreach to CTO/VP Eng.
*   **Tier 2: Medium Priority (7-14 Points)**
    *   *Action:* Automated nurturing and monitoring for new signals.
*   **Tier 3: Disqualified (<7 Points)**
    *   *Action:* Move to low-frequency monitoring or discard.

## 3. Signal Categories

### AI Agent Maturity
- **AGN_PROD (6 pts):** Production agent orchestration systems.
- **AGN_CORE (4 pts):** Core agentic workflows/copilots.
- **LLM_API (3 pts):** Explicit usage of LLM APIs/frameworks.

### Security & Risk
- **COMP_L (3 pts):** SOC2, ISO 27001, HIPAA, etc.
- **DATA_S (5 pts):** Sensitive data handling (PII/PHI).
- **REG_IND (3 pts):** Fintech, Healthcare, Gov, Defense.
- **ENT_RDY (4 pts):** RBAC, SSO, Audit Logs.
- **PRV_CLD (4 pts):** On-prem/VPC deployment options.

### Growth & Developer Focus
- **AI_HIRING (4 pts):** Hiring AI/ML Engineers.
- **AGN_HIRING (5 pts):** Hiring Automation/Agent Engineers.
- **API_PLF (3 pts):** API-first companies or developer platforms.
- **OPEN_SRC (2 pts):** Strong OSS focus or public GitHub presence.

## 4. Reasoning Storage

For every scored lead, we store:
1.  **Total Score**
2.  **Tier Level**
3.  **Signal Breakdown**: Exact matches found and their intensity.
4.  **Personalization Context**: Reasoning summary for use in outreach templates.
