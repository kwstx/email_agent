"""
Re-scoring Engine — Periodically re-evaluates previously scored companies.

Handles two scenarios:
1. Scoring model updated (weights changed by ScoringRefiner) → re-score all
2. Company content refreshed (re-scraped) → re-score those companies
3. Periodic full re-score to catch companies near tier boundaries
"""

import json
from datetime import datetime, timedelta
from typing import List
from sqlmodel import select, Session
from loguru import logger

from src.storage.db import get_session
from src.storage.models import Company
from src.scoring.detector import AgentSignalDetector


class RescoringEngine:
    """
    Re-scores companies when the scoring model has been updated
    or when company data has been refreshed.
    """

    def __init__(self, config_path: str = "scoring_config.json"):
        self.config_path = config_path
        self._last_config_hash = None
        self._load_config_hash()

    def _load_config_hash(self):
        """Compute a hash of the current scoring config for change detection."""
        try:
            with open(self.config_path, "r") as f:
                config = json.load(f)

            # Hash based on signal points and thresholds only
            signals = config.get("signals", {})
            thresholds = config.get("thresholds", {})
            hash_input = json.dumps({"signals": signals, "thresholds": thresholds}, sort_keys=True)
            self._last_config_hash = hash(hash_input)
        except Exception as e:
            logger.error(f"Error loading config for hash: {e}")
            self._last_config_hash = None

    def _config_changed(self) -> bool:
        """Check if scoring config has been modified since last check."""
        old_hash = self._last_config_hash
        self._load_config_hash()
        return old_hash is not None and old_hash != self._last_config_hash

    def rescore_all(self):
        """Re-score all companies using the latest scoring config."""
        logger.info("Starting FULL re-score of all companies...")
        detector = AgentSignalDetector(config_path=self.config_path)

        with get_session() as session:
            companies = session.exec(
                select(Company).where(Company.is_scraped == True)
            ).all()

            if not companies:
                logger.info("No companies to re-score.")
                return 0

            changed_count = 0
            for company in companies:
                old_score = company.fitness_score
                old_tier = company.fitness_level

                detector.process_company(session, company)

                if company.fitness_score != old_score or company.fitness_level != old_tier:
                    changed_count += 1
                    logger.info(
                        f"Re-scored {company.domain}: "
                        f"{old_tier}/{old_score} → {company.fitness_level}/{company.fitness_score}"
                    )

            session.commit()
            logger.success(f"Re-scored {len(companies)} companies. {changed_count} changed tiers/scores.")
            return changed_count

    def rescore_if_model_updated(self) -> bool:
        """Re-score all companies if the scoring model has been updated."""
        if self._config_changed():
            logger.info("Scoring config changed. Triggering full re-score.")
            self.rescore_all()
            return True
        else:
            logger.info("Scoring config unchanged. No re-score needed.")
            return False

    def rescore_stale(self, days_threshold: int = 7):
        """
        Re-score companies that haven't been scored recently.
        Useful for catching companies whose content may have been
        refreshed or whose near-boundary scores might shift with
        minor model tweaks.
        """
        cutoff = datetime.utcnow() - timedelta(days=days_threshold)
        detector = AgentSignalDetector(config_path=self.config_path)

        with get_session() as session:
            companies = session.exec(
                select(Company).where(
                    Company.is_scraped == True,
                    Company.is_scored == True
                )
            ).all()

            stale_companies = []
            for company in companies:
                # Check last scored time from metadata
                if company.signal_metadata:
                    try:
                        meta = json.loads(company.signal_metadata)
                        last_scored = meta.get("last_scored")
                        if last_scored:
                            scored_dt = datetime.fromisoformat(last_scored)
                            if scored_dt < cutoff:
                                stale_companies.append(company)
                        else:
                            stale_companies.append(company)
                    except (json.JSONDecodeError, ValueError):
                        stale_companies.append(company)
                else:
                    stale_companies.append(company)

            if not stale_companies:
                logger.info(f"No companies stale (>{days_threshold} days). Skipping re-score.")
                return 0

            logger.info(f"Found {len(stale_companies)} stale companies to re-score.")
            changed = 0
            for company in stale_companies:
                old_tier = company.fitness_level
                detector.process_company(session, company)
                if company.fitness_level != old_tier:
                    changed += 1

            session.commit()
            logger.success(f"Re-scored {len(stale_companies)} stale companies. {changed} tier changes.")
            return changed


if __name__ == "__main__":
    engine = RescoringEngine()
    engine.rescore_stale(days_threshold=7)
