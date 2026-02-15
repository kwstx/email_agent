"""
Outcome Tracker — Records and analyzes outreach outcomes per signal/tier.

Tracks reply rates, interest rates, and conversion rates per ICP signal
so that scoring weights can be refined based on what actually works.
"""

import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from sqlmodel import select, func, Session
from loguru import logger

from src.storage.db import get_session
from src.storage.models import (
    Company, Contact, Outreach, Reply,
    Signal, CompanySignalLink
)


class OutcomeTracker:
    """
    Collects outreach outcomes and correlates them with ICP signals
    to identify which signals predict engagement.
    """

    def __init__(self):
        self.metrics_cache = {}

    def _get_outreach_stats(self, session: Session) -> Dict[str, Any]:
        """Calculate global outreach statistics."""

        total_sent = session.exec(
            select(func.count(Outreach.id)).where(Outreach.status == "sent")
        ).one()

        total_replied = session.exec(
            select(func.count(Outreach.id)).where(Outreach.status == "replied")
        ).one()

        total_interest = session.exec(
            select(func.count(Reply.id)).where(Reply.classification == "interest")
        ).one()

        total_opt_out = session.exec(
            select(func.count(Reply.id)).where(Reply.classification == "opt_out")
        ).one()

        total_deferral = session.exec(
            select(func.count(Reply.id)).where(Reply.classification == "deferral")
        ).one()

        reply_rate = (total_replied / total_sent * 100) if total_sent > 0 else 0
        interest_rate = (total_interest / total_replied * 100) if total_replied > 0 else 0
        opt_out_rate = (total_opt_out / total_sent * 100) if total_sent > 0 else 0

        return {
            "total_sent": total_sent,
            "total_replied": total_replied,
            "total_interest": total_interest,
            "total_opt_out": total_opt_out,
            "total_deferral": total_deferral,
            "reply_rate_pct": round(reply_rate, 2),
            "interest_rate_pct": round(interest_rate, 2),
            "opt_out_rate_pct": round(opt_out_rate, 2),
        }

    def _get_signal_performance(self, session: Session) -> Dict[str, Dict[str, Any]]:
        """
        For each ICP signal, calculate how many companies with that signal
        resulted in replies vs. interest vs. opt-out.
        This tells us which signals are predictive of engagement.
        """
        signal_perf = {}

        signals = session.exec(select(Signal)).all()

        for signal in signals:
            # Get all companies linked to this signal
            links = session.exec(
                select(CompanySignalLink).where(
                    CompanySignalLink.signal_id == signal.id
                )
            ).all()

            company_ids = [link.company_id for link in links]
            if not company_ids:
                continue

            # Get contacts in those companies
            contacts = session.exec(
                select(Contact).where(Contact.company_id.in_(company_ids))
            ).all()
            contact_ids = [c.id for c in contacts]

            if not contact_ids:
                continue

            # Count outreach sent to those contacts
            sent_count = session.exec(
                select(func.count(Outreach.id)).where(
                    Outreach.contact_id.in_(contact_ids),
                    Outreach.status == "sent"
                )
            ).one()

            # Count replies
            replied_count = session.exec(
                select(func.count(Reply.id)).where(
                    Reply.contact_id.in_(contact_ids)
                )
            ).one()

            # Count interest replies
            interest_count = session.exec(
                select(func.count(Reply.id)).where(
                    Reply.contact_id.in_(contact_ids),
                    Reply.classification == "interest"
                )
            ).one()

            # Count opt-out replies
            opt_out_count = session.exec(
                select(func.count(Reply.id)).where(
                    Reply.contact_id.in_(contact_ids),
                    Reply.classification == "opt_out"
                )
            ).one()

            reply_rate = (replied_count / sent_count * 100) if sent_count > 0 else 0
            interest_rate = (interest_count / replied_count * 100) if replied_count > 0 else 0
            opt_out_rate = (opt_out_count / sent_count * 100) if sent_count > 0 else 0

            signal_perf[signal.name] = {
                "signal_description": signal.description,
                "category": signal.category,
                "current_points": signal.points,
                "companies_with_signal": len(company_ids),
                "contacts_reached": len(contact_ids),
                "emails_sent": sent_count,
                "replies": replied_count,
                "interests": interest_count,
                "opt_outs": opt_out_count,
                "reply_rate_pct": round(reply_rate, 2),
                "interest_rate_pct": round(interest_rate, 2),
                "opt_out_rate_pct": round(opt_out_rate, 2),
            }

        return signal_perf

    def _get_tier_performance(self, session: Session) -> Dict[str, Dict[str, Any]]:
        """
        Calculate outreach performance per fitness tier (high_priority, medium_priority, disqualified).
        """
        tier_perf = {}

        for tier in ["high_priority", "medium_priority", "disqualified"]:
            companies = session.exec(
                select(Company).where(Company.fitness_level == tier)
            ).all()
            company_ids = [c.id for c in companies]

            if not company_ids:
                tier_perf[tier] = {
                    "companies": 0, "contacts": 0, "sent": 0,
                    "replied": 0, "interest": 0, "reply_rate_pct": 0
                }
                continue

            contacts = session.exec(
                select(Contact).where(Contact.company_id.in_(company_ids))
            ).all()
            contact_ids = [c.id for c in contacts]

            sent = 0
            replied = 0
            interest = 0

            if contact_ids:
                sent = session.exec(
                    select(func.count(Outreach.id)).where(
                        Outreach.contact_id.in_(contact_ids),
                        Outreach.status == "sent"
                    )
                ).one()

                replied = session.exec(
                    select(func.count(Reply.id)).where(
                        Reply.contact_id.in_(contact_ids)
                    )
                ).one()

                interest = session.exec(
                    select(func.count(Reply.id)).where(
                        Reply.contact_id.in_(contact_ids),
                        Reply.classification == "interest"
                    )
                ).one()

            reply_rate = (replied / sent * 100) if sent > 0 else 0

            tier_perf[tier] = {
                "companies": len(company_ids),
                "contacts": len(contact_ids),
                "sent": sent,
                "replied": replied,
                "interest": interest,
                "reply_rate_pct": round(reply_rate, 2),
            }

        return tier_perf

    def generate_report(self) -> Dict[str, Any]:
        """Generate a full outcome report with all metrics."""
        with get_session() as session:
            report = {
                "generated_at": datetime.utcnow().isoformat(),
                "global_stats": self._get_outreach_stats(session),
                "signal_performance": self._get_signal_performance(session),
                "tier_performance": self._get_tier_performance(session),
            }

        self.metrics_cache = report
        return report

    def log_report(self):
        """Generate and log the outcome report."""
        report = self.generate_report()

        logger.info("=" * 70)
        logger.info("OUTREACH OUTCOME REPORT")
        logger.info("=" * 70)

        gs = report["global_stats"]
        logger.info(
            f"Global: {gs['total_sent']} sent → {gs['total_replied']} replied "
            f"({gs['reply_rate_pct']}%) → {gs['total_interest']} interested "
            f"({gs['interest_rate_pct']}%)"
        )
        logger.info(f"Opt-out rate: {gs['opt_out_rate_pct']}%")

        logger.info("-" * 40 + " TIER PERFORMANCE " + "-" * 40)
        for tier, data in report["tier_performance"].items():
            logger.info(
                f"  {tier}: {data['companies']} companies, {data['contacts']} contacts, "
                f"{data['sent']} sent, {data['replied']} replied ({data['reply_rate_pct']}%), "
                f"{data['interest']} interested"
            )

        logger.info("-" * 40 + " SIGNAL PERFORMANCE " + "-" * 40)
        for signal_name, data in report["signal_performance"].items():
            if data["emails_sent"] > 0:
                logger.info(
                    f"  {signal_name} ({data['current_points']}pts): "
                    f"{data['emails_sent']} sent → {data['reply_rate_pct']}% reply rate, "
                    f"{data['interest_rate_pct']}% interest rate"
                )

        logger.info("=" * 70)
        return report


if __name__ == "__main__":
    tracker = OutcomeTracker()
    tracker.log_report()
