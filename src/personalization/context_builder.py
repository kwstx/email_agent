import json
from typing import Dict, List, Any, Optional
from loguru import logger
from sqlmodel import select, Session

from src.storage.models import Company
from src.storage.db import get_session

class ContextBuilder:
    """
    Constructs a personalized deployment context for each company.
    Transforms raw scoring signals and enrichment data into narrative inputs.
    """
    
    def __init__(self):
        pass

    def _extract_integrations_from_signals(self, signals: Dict[str, Any]) -> List[str]:
        """Extracts specific tools/frameworks mentioned in matched keywords."""
        integrations = set()
        
        # Look at matches in LLM_API and AGENT_CORE
        relevant_categories = ["LLM_API", "AGENT_CORE", "AGENT_PROD"]
        for key in relevant_categories:
            if key in signals:
                matches = signals[key].get("matches", [])
                for match in matches:
                    # Normalize common tools
                    m_lower = match.lower()
                    if "langchain" in m_lower: integrations.add("LangChain")
                    elif "crewai" in m_lower: integrations.add("CrewAI")
                    elif "openai" in m_lower: integrations.add("OpenAI")
                    elif "anthropic" in m_lower: integrations.add("Anthropic")
                    elif "pinecone" in m_lower or "vector" in m_lower: integrations.add("Vector DB")
                    elif "pydantic" in m_lower: integrations.add("PydanticAI")
                    
        return list(integrations)

    def _identify_compliance_exposure(self, signals: Dict[str, Any], risk_data: Dict[str, Any]) -> List[str]:
        """Identifies compliance frameworks relevant to the company."""
        exposure = set()
        
        # Check industry signals
        industries = risk_data.get("detected_industries", [])
        
        if "healthcare" in industries or "healthtech" in str(industries):
            exposure.add("HIPAA")
        if "fintech" in industries or "banking" in str(industries):
            exposure.add("PCI-DSS")
            exposure.add("SOC2")
        if "gov" in industries:
            exposure.add("FedRAMP")
        if "legal" in industries:
            exposure.add("Client Confidentiality")

        # Check explicit signals
        if "COMP_L" in signals:
            matches = signals["COMP_L"].get("matches", [])
            for m in matches:
                exposure.add(m.upper())
                
        return list(exposure)

    def _identify_governance_gaps(self, signals: Dict[str, Any], risk_data: Dict[str, Any]) -> List[str]:
        """Identifies potential gaps between agent usage and security posture."""
        gaps = []
        
        has_agents = "AGENT_PROD" in signals or "AGENT_CORE" in signals
        security_features = risk_data.get("security_features", {})
        
        if has_agents:
            if not security_features.get("has_audit_logging"):
                gaps.append("Missing Agent Audit Trails")
            if not security_features.get("has_rbac"):
                gaps.append("Lack of Granular Agent Access Control")
            if not security_features.get("is_enterprise_ready"):
                gaps.append("Production Readiness Gap")
                
        # Check for shadow AI risk
        if "LLM_API" in signals and not has_agents:
             # Using APIs but not indicating full agent governance
             gaps.append("Unmonitored LLM API Usage")

        return gaps

    def generate_narrative(self, company_name: str, context: Dict[str, Any]) -> str:
        """Generates a summary paragraph for the email."""
        
        integrations = context.get("integrations", [])
        gaps = context.get("governance_gaps", [])
        compliance = context.get("compliance_exposure", [])
        maturity = context.get("agent_maturity", "unknown")
        
        narrative = f"{company_name} appears to be "
        
        if maturity == "production":
            narrative += "scaling production-grade agent workflows."
        elif maturity == "active_development":
            narrative += "actively building agentic capabilities."
        else:
            narrative += "exploring AI integration."
            
        if integrations:
            tech_stack = ", ".join(integrations[:2])
            narrative += f" utilizing {tech_stack}."
            
        if gaps:
            gap = gaps[0].lower()
            narrative += f" However, operational risks around {gap} may expose the organization"
            if compliance:
                comp = compliance[0]
                narrative += f" to {comp} compliance issues."
            else:
                narrative += " to reliability challenges."
        else:
            narrative += " Ensuring runtime safety is critical as these systems scale."
            
        return narrative

    def process_company(self, session: Session, company: Company):
        """Builds the personalization context for a company."""
        if not company.signal_metadata:
            return
            
        try:
            meta = json.loads(company.signal_metadata)
        except json.JSONDecodeError:
            return

        signals = meta.get("score_breakdown", {})
        # Fallback: if 'score_breakdown' is missing but signals look like they are at top level
        if not signals and any(k in meta for k in ["AGENT_PROD", "LLM_API", "AGENT_CORE", "AI_HIRING"]):
             signals = meta
             
        risk_data = meta.get("risk_enrichment", {})
        
        # 1. Extract Intelligence
        integrations = self._extract_integrations_from_signals(signals)
        compliance_exposure = self._identify_compliance_exposure(signals, risk_data)
        governance_gaps = self._identify_governance_gaps(signals, risk_data)
        agent_maturity = company.agent_maturity_level or "unknown"
        
        context_analysis = {
            "integrations": integrations,
            "compliance_exposure": compliance_exposure,
            "governance_gaps": governance_gaps,
            "agent_maturity": agent_maturity,
            "summary": ""
        }
        
        # 2. Generate Narrative Summary
        context_analysis["summary"] = self.generate_narrative(company.name or "your team", context_analysis)
        
        # 3. Store
        meta["context_analysis"] = context_analysis
        company.signal_metadata = json.dumps(meta)
        session.add(company)
        logger.info(f"Built personalization context for {company.domain}")

    def run(self):
        """Runs context building for scored companies."""
        with get_session() as session:
            # Look for scored companies that might need context (or update all)
            statement = select(Company).where(Company.is_scored == True)
            companies = session.exec(statement).all()
            
            if not companies:
                logger.info("No scored companies found.")
                return
                
            logger.info(f"Building context for {len(companies)} companies...")
            for company in companies:
                self.process_company(session, company)
            
            session.commit()

if __name__ == "__main__":
    builder = ContextBuilder()
    builder.run()
