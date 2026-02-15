import json
import re
from typing import Dict, List, Any, Optional
from loguru import logger
from sqlmodel import select, Session

from src.storage.models import Company, Signal, CompanySignalLink
from src.storage.db import get_session

class AgentSignalDetector:
    """Detects and scores AI agent deployment signals from text."""
    
    def __init__(self, config_path: str = "scoring_config.json"):
        with open(config_path, "r") as f:
            self.config = json.load(f)
            
    def analyze_text(self, text: str) -> Dict[str, Any]:
        """
        Analyzes text for AI signals and returns detailed scores.
        Returns: {
            "signals": { "SIGNAL_KEY": {"intensity": float, "count": int, "matches": List[str]} },
            "total_score": int,
            "maturity_level": str
        }
        """
        if not text:
            return {"signals": {}, "total_score": 0, "maturity_level": "unknown"}
            
        text_lower = text.lower()
        results = {}
        total_score = 0
        
        for category, signals in self.config.get("signals", {}).items():
            for signal_key, details in signals.items():
                keywords = details.get("keywords", [])
                matches = []
                count = 0
                
                for kw in keywords:
                    # Use regex for better matching (word boundaries)
                    pattern = rf"\b{re.escape(kw.lower())}\b"
                    found = re.findall(pattern, text_lower)
                    if found:
                        matches.append(kw)
                        count += len(found)
                
                if count > 0:
                    # Calculate intensity: base points * (1 + log(count)) capped at points * 2
                    # This gives more weight to multiple mentions but with diminishing returns
                    base_points = details.get("points", 0)
                    import math
                    intensity = base_points * (1 + 0.5 * math.log(count))
                    
                    results[signal_key] = {
                        "intensity": round(intensity, 2),
                        "count": count,
                        "matches": matches,
                        "category": category
                    }
                    total_score += base_points
        
        # Determine maturity level
        maturity = "unknown"
        if "AGENT_PROD" in results:
            maturity = "production_ready"
        elif "AGENT_CORE" in results or "LLM_API" in results:
            maturity = "experimenting"
        elif "AI_EXP" in results:
            maturity = "experimenting"
            
        return {
            "signals": results,
            "total_score": total_score,
            "maturity_level": maturity
        }

    def process_company(self, session: Session, company: Company):
        """Processes a company's scraped content and updates signals in DB."""
        if not company.website_content:
            logger.warning(f"No content for {company.domain}, skipping detection.")
            return
            
        analysis = self.analyze_text(company.website_content)
        
        company.fitness_score = analysis["total_score"]
        company.agent_maturity_level = analysis["maturity_level"]
        
        # Merge signals into existing metadata
        existing_meta = {}
        if company.signal_metadata:
            try:
                existing_meta = json.loads(company.signal_metadata)
            except:
                pass
        
        # We want to keep existing top-level keys (like risk_enrichment) 
        # and update/add signals. We'll store signals under a 'signals' key
        # or just keep them at top level but merge safely.
        # For simplicity and backward compatibility, let's keep them at top level
        # but only update keys that are in analysis["signals"]
        
        existing_meta.update(analysis["signals"])
        company.signal_metadata = json.dumps(existing_meta)
        
        # Update fitness level based on threshold
        thresholds = self.config.get("thresholds", {})
        if company.fitness_score >= thresholds.get("high_fit", 15):
            company.fitness_level = "high_fit"
        elif company.fitness_score >= thresholds.get("medium_fit", 8):
            company.fitness_level = "medium_fit"
        else:
            company.fitness_level = "low_fit"
            
        # Update Signal objects and Link table
        for signal_key, data in analysis["signals"].items():
            # Find signal object
            statement = select(Signal).where(Signal.name == signal_key)
            signal_obj = session.exec(statement).first()
            
            if signal_obj:
                # Check for existing link
                link_statement = select(CompanySignalLink).where(
                    CompanySignalLink.company_id == company.id,
                    CompanySignalLink.signal_id == signal_obj.id
                )
                link = session.exec(link_statement).first()
                
                if not link:
                    link = CompanySignalLink(
                        company_id=company.id,
                        signal_id=signal_obj.id,
                        intensity=data["intensity"],
                        occurrences=data["count"]
                    )
                    session.add(link)
                else:
                    link.intensity = data["intensity"]
                    link.occurrences = data["count"]
                    session.add(link)
                    
        company.is_scored = True
        session.add(company)
        logger.info(f"Scored {company.domain}: Match level {company.fitness_level}, Maturity: {company.agent_maturity_level}")

    def run(self):
        """Processes all scraped but unscored companies."""
        with get_session() as session:
            statement = select(Company).where(Company.is_scraped == True, Company.is_scored == False)
            companies = session.exec(statement).all()
            
            if not companies:
                logger.info("No companies ready for scoring.")
                return
                
            logger.info(f"Found {len(companies)} companies to score.")
            for company in companies:
                self.process_company(session, company)
            
            session.commit()

if __name__ == "__main__":
    detector = AgentSignalDetector()
    detector.run()
