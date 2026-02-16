import json
import re
import math
from datetime import datetime
from typing import Dict, List, Any, Optional
from loguru import logger
from sqlmodel import select, Session

from src.storage.models import Company, Signal, CompanySignalLink
from src.storage.db import get_session

class AgentSignalDetector:
    """
    Unified ICP Scoring Model.
    Combines signals from:
    - Agent Deployment Intensity
    - Security Posture
    - Industry Risk Level
    - Hiring Activity
    - Developer Platform Maturity
    """
    
    def __init__(self, config_path: str = "scoring_config.json"):
        with open(config_path, "r") as f:
            self.config = json.load(f)
            
    def analyze_text(self, text: str) -> Dict[str, Any]:
        """
        Analyzes text and returns a unified score, tier, and reasoning.
        """
        if not text:
            return {
                "signals": {}, 
                "total_score": 0, 
                "tier": "disqualified", 
                "maturity_level": "unknown",
                "reasoning": []
            }
            
        text_lower = text.lower()
        results = {}
        total_score = 0
        reasoning = []
        
        for category, signals in self.config.get("signals", {}).items():
            category_score = 0
            category_signals = []
            
            for signal_key, details in signals.items():
                keywords = details.get("keywords", [])
                matches = []
                count = 0
                
                for kw in keywords:
                    pattern = rf"\b{re.escape(kw.lower())}\b"
                    found = re.findall(pattern, text_lower)
                    if found:
                        matches.append(kw)
                        count += len(found)
                
                if count > 0:
                    base_points = details.get("points", 0)
                    intensity = base_points * (1 + 0.5 * math.log(count))
                    
                    signal_data = {
                        "intensity": round(intensity, 2),
                        "count": count,
                        "matches": list(set(matches)),
                        "category": category,
                        "description": details.get("description"),
                        "points": base_points
                    }
                    results[signal_key] = signal_data
                    total_score += base_points
                    category_score += base_points
                    category_signals.append(signal_data)
            
            if category_score > 0:
                reasoning.append({
                    "category": category,
                    "score": category_score,
                    "signals": category_signals
                })

        # --- Step 4: Careers Page Intensity ---
        # Give extra weight if the careers page contains "Founding" or "First"
        if "--- CAREERS ---" in text:
            careers_parts = text.split("--- CAREERS ---")
            if len(careers_parts) > 1:
                careers_content = careers_parts[1].split("---")[0].lower()
                if "founding" in careers_content or "first" in careers_content:
                    bonus_points = 5
                    total_score += bonus_points
                    reasoning.append({
                        "category": "SMB_FILTRATION",
                        "score": bonus_points,
                        "signals": [{
                            "intensity": bonus_points,
                            "count": 1,
                            "matches": ["founding/first"],
                            "category": "SMB_FILTRATION",
                            "description": "Founding/First roles detected on Careers page (SMB Signal)",
                            "points": bonus_points
                        }]
                    })
        
        # Determine Tier based on thresholds
        thresholds = self.config.get("thresholds", {
            "high_fit": 18,
            "medium_fit": 10,
            "disqualified": 4
        })
        
        if total_score >= thresholds.get("high_fit"):
            tier = "high_priority"
        elif total_score >= thresholds.get("medium_fit"):
            tier = "medium_priority"
        else:
            tier = "disqualified"
            
        # Determine maturity level
        maturity = "unknown"
        if "AGENT_PROD" in results:
            maturity = "production"
        elif any(k in results for k in ["AGENT_CORE", "LLM_API", "AGENT_HIRING"]):
            maturity = "active_development"
        elif "AI_HIRING" in results:
            maturity = "experimenting"
            
        return {
            "signals": results,
            "total_score": total_score,
            "tier": tier,
            "maturity_level": maturity,
            "reasoning": reasoning
        }

    def process_company(self, session: Session, company: Company):
        """Processes a company and stores unified score + reasoning signals."""
        if not company.website_content:
            logger.warning(f"No content for {company.domain}, disqualifying.")
            company.fitness_score = 0
            company.fitness_level = "disqualified"
            company.is_scored = True
            session.add(company)
            return
            
        analysis = self.analyze_text(company.website_content)
        
        company.fitness_score = analysis["total_score"]
        company.fitness_level = analysis["tier"]
        company.agent_maturity_level = analysis["maturity_level"]
        
        # Store detailed reasoning for outreach
        metadata = {
            "last_scored": datetime.utcnow().isoformat(),
            "score_breakdown": analysis["signals"],
            "reasoning_summary": analysis["reasoning"]
        }
        company.signal_metadata = json.dumps(metadata)
        
        # Update Signal objects and Link table
        for signal_key, data in analysis["signals"].items():
            statement = select(Signal).where(Signal.name == signal_key)
            signal_obj = session.exec(statement).first()
            
            if signal_obj:
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
        logger.info(f"Qualified {company.domain}: Tier={company.fitness_level}, Score={company.fitness_score}")

    def run(self):
        """Processes all scraped but unscored companies."""
        with get_session() as session:
            # We also might want to re-score companies if the model updated
            # For now, just focus on is_scored=False
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

