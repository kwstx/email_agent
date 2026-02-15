"""
Auto-Discovery Expander — Dynamically generates new search queries
based on successful leads to discover similar companies.

When a company converts (reply with interest), this module:
1. Extracts patterns from the company's profile (industry, technology stack, keywords)
2. Generates new search queries targeting similar companies
3. Feeds them back into the Discovery Engine
"""

import json
from datetime import datetime
from typing import List, Dict, Set, Optional
from sqlmodel import select, Session
from loguru import logger

from src.storage.db import get_session
from src.storage.models import Company, Contact, Reply, Signal, CompanySignalLink


# Base query patterns that get customized with discovered patterns
QUERY_TEMPLATES = [
    "{keyword} AI agent platform startup",
    "{keyword} autonomous workflow company",
    "{keyword} LLM infrastructure startup 2025",
    "companies using {keyword} for enterprise automation",
    "{keyword} copilot agent deployment",
    "site:ycombinator.com '{keyword}' AI agent",
    "{keyword} agent orchestration startup funding",
]


class DiscoveryExpander:
    """
    Analyzes converted leads to find patterns and generate
    new discovery queries targeting similar companies.
    """

    def __init__(self):
        self.generated_queries: List[str] = []
        self.query_history_path = "data/query_history.json"
        self._load_history()

    def _load_history(self):
        """Load previously generated queries to avoid duplicates."""
        try:
            with open(self.query_history_path, "r") as f:
                self.history = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            self.history = {"generated_queries": [], "last_run": None}

    def _save_history(self):
        """Persist query history."""
        self.history["last_run"] = datetime.utcnow().isoformat()
        with open(self.query_history_path, "w") as f:
            json.dump(self.history, f, indent=2)

    def _extract_winning_keywords(self, session: Session) -> Set[str]:
        """
        Extract keywords and patterns from companies that received
        positive replies (interest, referral). These represent the
        profile of our most receptive targets.
        """
        winning_keywords = set()

        # Find contacts with positive replies
        positive_replies = session.exec(
            select(Reply).where(Reply.classification.in_(["interest", "referral"]))
        ).all()

        positive_contact_ids = {r.contact_id for r in positive_replies}
        if not positive_contact_ids:
            logger.info("No positive replies yet — no expansion queries to generate.")
            return winning_keywords

        # Get companies for those contacts
        contacts = session.exec(
            select(Contact).where(Contact.id.in_(positive_contact_ids))
        ).all()

        company_ids = {c.company_id for c in contacts}

        for company_id in company_ids:
            company = session.get(Company, company_id)
            if not company:
                continue

            # Extract keywords from signal metadata
            if company.signal_metadata:
                try:
                    meta = json.loads(company.signal_metadata)
                    breakdown = meta.get("score_breakdown", {})
                    for signal_key, signal_data in breakdown.items():
                        matches = signal_data.get("matches", [])
                        winning_keywords.update(matches)
                except json.JSONDecodeError:
                    pass

            # Extract industry keywords
            if company.industry:
                winning_keywords.add(company.industry.lower())

            # Extract from description
            if company.description:
                desc_lower = company.description.lower()
                industry_hints = [
                    "fintech", "healthcare", "legal", "insurance",
                    "cybersecurity", "devtools", "infrastructure",
                    "saas", "enterprise", "b2b"
                ]
                for hint in industry_hints:
                    if hint in desc_lower:
                        winning_keywords.add(hint)

        return winning_keywords

    def _extract_high_signal_patterns(self, session: Session) -> Set[str]:
        """
        Find which signals are most common among high-performing companies
        and extract their keyword patterns.
        """
        patterns = set()

        # Get high-fit companies
        companies = session.exec(
            select(Company).where(Company.fitness_level == "high_priority")
        ).all()

        if not companies:
            return patterns

        # Count signal frequency
        signal_counts: Dict[str, int] = {}
        for company in companies:
            links = session.exec(
                select(CompanySignalLink).where(
                    CompanySignalLink.company_id == company.id
                )
            ).all()
            for link in links:
                signal = session.get(Signal, link.signal_id)
                if signal:
                    signal_counts[signal.name] = signal_counts.get(signal.name, 0) + 1

        # Top signals → keywords for expansion
        sorted_signals = sorted(signal_counts.items(), key=lambda x: x[1], reverse=True)
        for signal_name, count in sorted_signals[:5]:
            # Use signal name and description as query seeds
            patterns.add(signal_name.lower().replace("_", " "))

        return patterns

    def generate_expansion_queries(self) -> List[str]:
        """
        Generate new search queries based on successful lead patterns.
        Returns list of new queries not previously used.
        """
        with get_session() as session:
            keywords = self._extract_winning_keywords(session)
            patterns = self._extract_high_signal_patterns(session)
            all_seeds = keywords | patterns

        if not all_seeds:
            logger.info("No seed keywords found for query expansion.")
            return []

        # Generate queries from templates
        new_queries = []
        existing = set(self.history.get("generated_queries", []))

        for seed in all_seeds:
            # Skip very generic terms
            if len(seed) < 3 or seed in {"api", "sdk", "sso", "the", "and", "for"}:
                continue

            for template in QUERY_TEMPLATES:
                query = template.format(keyword=seed)
                if query not in existing:
                    new_queries.append(query)
                    existing.add(query)

        # Limit to avoid overwhelming the search engine
        new_queries = new_queries[:25]

        # Save to history
        self.history["generated_queries"] = list(existing)
        self._save_history()

        logger.info(f"Generated {len(new_queries)} new expansion queries from {len(all_seeds)} seed keywords.")
        self.generated_queries = new_queries
        return new_queries

    def get_stats(self) -> Dict[str, Any]:
        """Get expansion stats."""
        return {
            "total_queries_generated": len(self.history.get("generated_queries", [])),
            "last_run": self.history.get("last_run"),
            "pending_queries": len(self.generated_queries),
        }


if __name__ == "__main__":
    expander = DiscoveryExpander()
    queries = expander.generate_expansion_queries()
    print(f"\nGenerated {len(queries)} new queries:")
    for q in queries:
        print(f"  - {q}")
