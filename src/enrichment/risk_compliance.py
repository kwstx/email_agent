import json
import re
from typing import Dict, List, Any, Optional
from loguru import logger
from sqlmodel import select, Session

from src.storage.models import Company, Signal, CompanySignalLink
from src.storage.db import get_session
from src.scoring.detector import AgentSignalDetector

class RiskComplianceEnricher:
    """
    Enriches companies with detailed risk and compliance indicators.
    Focuses on security pages and enterprise readiness signals.
    """
    
    def __init__(self, config_path: str = "scoring_config.json"):
        self.detector = AgentSignalDetector(config_path)
        with open(config_path, "r") as f:
            self.config = json.load(f)
            
    def detect_industry_focus(self, text: str) -> List[str]:
        """Detects if a company operates in specific regulated industries."""
        industries = []
        patterns = {
            "fintech": r"\b(fintech|banking|financial services|payments|lending|wealth management|brokerage)\b",
            "healthcare": r"\b(healthcare|medical|biotech|pharma|healthtech|hipaa compliance|patient data)\b",
            "legal": r"\b(legaltech|law firm|egrc|compliance management|regulatory excellence)\b",
            "gov": r"\b(government|public sector|fedramp|defense|military|aerospace)\b"
        }
        
        text_lower = text.lower()
        for industry, pattern in patterns.items():
            if re.search(pattern, text_lower):
                industries.append(industry)
        return industries

    def detect_security_robustness(self, text: str) -> Dict[str, bool]:
        """Identifies specific security and trust references."""
        text_lower = text.lower()
        return {
            "has_audit_logging": bool(re.search(r"\b(audit logging|audit trails|activity logs|event logging)\b", text_lower)),
            "has_rbac": bool(re.search(r"\b(rbac|role-based access|access controls|identity management|sso|saml)\b", text_lower)),
            "has_data_protection": bool(re.search(r"\b(data protection|encryption at rest|encryption in transit|kms|hsm)\b", text_lower)),
            "has_compliance_cert": bool(re.search(r"\b(soc2|soc 2|iso 27001|hipaa|gdpr|pci dss|fedramp)\b", text_lower)),
            "is_enterprise_ready": bool(re.search(r"\b(enterprise readiness|enterprise grade|uptime sla|dedicated support)\b", text_lower))
        }

    def process_company(self, session: Session, company: Company):
        """Performs deep enrichment for a company."""
        if not company.website_content:
            return
            
        logger.info(f"Enriching risk/compliance for {company.domain}")
        
        # 1. Run the detector first to get base signals and score
        self.detector.process_company(session, company)
        
        # 2. Add extra enrichment based on specialized checks
        industries = self.detect_industry_focus(company.website_content)
        security_features = self.detect_security_robustness(company.website_content)
        
        # Merge into signal_metadata
        current_metadata = {}
        if company.signal_metadata:
            try:
                current_metadata = json.loads(company.signal_metadata)
            except:
                pass
        
        current_metadata["risk_enrichment"] = {
            "detected_industries": industries,
            "security_features": security_features
        }
        
        # Update industry field if detected
        if industries and not company.industry:
            company.industry = ", ".join(industries)
            
        company.signal_metadata = json.dumps(current_metadata)
        session.add(company)
        logger.success(f"Enriched {company.domain} with {len(industries)} industries and {sum(security_features.values())} security features.")

    def run(self, force: bool = False):
        """Runs the enrichment for all scraped companies."""
        with get_session() as session:
            # If force is true, process all scraped companies. 
            # Otherwise, maybe process ones that don't have risk_enrichment in metadata.
            statement = select(Company).where(Company.is_scraped == True)
            companies = session.exec(statement).all()
            
            if not companies:
                logger.info("No companies found for enrichment.")
                return
                
            logger.info(f"Starting risk/compliance enrichment for {len(companies)} companies.")
            for company in companies:
                # Check if already enriched
                if not force and company.signal_metadata:
                    try:
                        meta = json.loads(company.signal_metadata)
                        if "risk_enrichment" in meta:
                            continue
                    except:
                        pass
                        
                self.process_company(session, company)
            
            session.commit()

if __name__ == "__main__":
    enricher = RiskComplianceEnricher()
    enricher.run(force=True) # Run for everyone to pick up new config
