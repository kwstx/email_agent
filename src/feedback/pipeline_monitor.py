"""
Pipeline Health Monitor — Tracks the overall health and throughput of the
outbound prospecting engine.

Provides a unified dashboard view of:
- Pipeline stage counts (discovered → scraped → scored → contacted → replied)
- Conversion rates at each stage
- Pipeline velocity (leads per day through each stage)
- Bottleneck detection
- System health alerts
"""

import json
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from sqlmodel import select, func, Session
from loguru import logger

from src.storage.db import get_session
from src.storage.models import (
    Company, Contact, Outreach, Reply,
    TaskLog, SuppressionList
)


class PipelineHealthMonitor:
    """
    Monitors pipeline health metrics and generates reports/alerts.
    """

    def __init__(self):
        self.alerts: List[Dict[str, str]] = []

    def _get_pipeline_counts(self, session: Session) -> Dict[str, int]:
        """Count leads at each pipeline stage."""
        total_companies = session.exec(select(func.count(Company.id))).one()
        scraped = session.exec(
            select(func.count(Company.id)).where(Company.is_scraped == True)
        ).one()
        scored = session.exec(
            select(func.count(Company.id)).where(Company.is_scored == True)
        ).one()
        high_fit = session.exec(
            select(func.count(Company.id)).where(Company.fitness_level == "high_priority")
        ).one()
        medium_fit = session.exec(
            select(func.count(Company.id)).where(Company.fitness_level == "medium_priority")
        ).one()
        disqualified = session.exec(
            select(func.count(Company.id)).where(Company.fitness_level == "disqualified")
        ).one()

        total_contacts = session.exec(select(func.count(Contact.id))).one()
        verified_contacts = session.exec(
            select(func.count(Contact.id)).where(Contact.is_verified == True)
        ).one()

        active_outreach = session.exec(
            select(func.count(Contact.id)).where(Contact.outreach_status == "active")
        ).one()
        pending_outreach = session.exec(
            select(func.count(Contact.id)).where(Contact.outreach_status == "pending")
        ).one()
        total_replied = session.exec(
            select(func.count(Contact.id)).where(
                Contact.outreach_status.in_(["replied", "active_lead", "deferred", "referral_needed"])
            )
        ).one()
        active_leads = session.exec(
            select(func.count(Contact.id)).where(Contact.outreach_status == "active_lead")
        ).one()
        opted_out = session.exec(
            select(func.count(Contact.id)).where(Contact.outreach_status == "opt_out")
        ).one()

        total_emails_sent = session.exec(
            select(func.count(Outreach.id)).where(Outreach.status == "sent")
        ).one()
        total_drafts = session.exec(
            select(func.count(Outreach.id)).where(Outreach.status == "draft")
        ).one()

        suppressed = session.exec(select(func.count(SuppressionList.id))).one()

        return {
            "companies": {
                "total": total_companies,
                "scraped": scraped,
                "unscraped": total_companies - scraped,
                "scored": scored,
                "unscored": scraped - scored,
                "high_fit": high_fit,
                "medium_fit": medium_fit,
                "disqualified": disqualified,
            },
            "contacts": {
                "total": total_contacts,
                "verified": verified_contacts,
                "unverified": total_contacts - verified_contacts,
            },
            "outreach": {
                "pending": pending_outreach,
                "active": active_outreach,
                "total_emails_sent": total_emails_sent,
                "drafts_queued": total_drafts,
                "replied": total_replied,
                "active_leads": active_leads,
                "opted_out": opted_out,
            },
            "compliance": {
                "suppressed": suppressed,
            }
        }

    def _get_conversion_rates(self, counts: Dict) -> Dict[str, float]:
        """Calculate conversion rates at each pipeline stage."""
        companies = counts["companies"]
        outreach = counts["outreach"]

        # Scraped → Scored
        scrape_to_score = (companies["scored"] / companies["scraped"] * 100) if companies["scraped"] > 0 else 0

        # Scored → High Fit
        score_to_high = (companies["high_fit"] / companies["scored"] * 100) if companies["scored"] > 0 else 0

        # Scored → Medium+ Fit (actionable leads)
        score_to_actionable = ((companies["high_fit"] + companies["medium_fit"]) / companies["scored"] * 100) if companies["scored"] > 0 else 0

        # Sent → Replied
        sent_to_reply = (outreach["replied"] / outreach["total_emails_sent"] * 100) if outreach["total_emails_sent"] > 0 else 0

        # Replied → Active Lead
        reply_to_lead = (outreach["active_leads"] / outreach["replied"] * 100) if outreach["replied"] > 0 else 0

        return {
            "scrape_to_score_pct": round(scrape_to_score, 1),
            "score_to_high_fit_pct": round(score_to_high, 1),
            "score_to_actionable_pct": round(score_to_actionable, 1),
            "sent_to_reply_pct": round(sent_to_reply, 1),
            "reply_to_active_lead_pct": round(reply_to_lead, 1),
        }

    def _detect_bottlenecks(self, counts: Dict) -> List[Dict[str, str]]:
        """Identify pipeline bottlenecks and generate alerts."""
        alerts = []
        companies = counts["companies"]
        contacts = counts["contacts"]
        outreach = counts["outreach"]

        # Bottleneck: Too many unscraped companies
        if companies["unscraped"] > 50:
            alerts.append({
                "level": "warning",
                "stage": "scraping",
                "message": f"{companies['unscraped']} companies awaiting scraping. Consider increasing scraping frequency.",
            })

        # Bottleneck: Too many unscored companies
        if companies["unscored"] > 20:
            alerts.append({
                "level": "warning",
                "stage": "scoring",
                "message": f"{companies['unscored']} companies scraped but not scored. Scoring may be lagging.",
            })

        # Bottleneck: High-fit companies but no contacts discovered
        if companies["high_fit"] > 5 and contacts["total"] == 0:
            alerts.append({
                "level": "critical",
                "stage": "enrichment",
                "message": f"{companies['high_fit']} high-fit companies but 0 contacts discovered. People discovery may be failing.",
            })

        # Bottleneck: Contacts but no outreach
        if contacts["total"] > 10 and outreach["pending"] > contacts["total"] * 0.8:
            alerts.append({
                "level": "warning",
                "stage": "outreach",
                "message": f"{outreach['pending']} contacts pending outreach. Email generation may be stalled.",
            })

        # Health: High opt-out rate
        if outreach["total_emails_sent"] > 20 and outreach["opted_out"] > outreach["total_emails_sent"] * 0.05:
            alerts.append({
                "level": "critical",
                "stage": "compliance",
                "message": f"High opt-out rate: {outreach['opted_out']}/{outreach['total_emails_sent']} sent. Review targeting and messaging.",
            })

        # Health: Too many drafts queued
        if outreach["drafts_queued"] > 50:
            alerts.append({
                "level": "warning",
                "stage": "sending",
                "message": f"{outreach['drafts_queued']} email drafts queued. Email sending may be delayed.",
            })

        # Positive: Pipeline empty, need more companies
        if companies["unscraped"] == 0 and companies["total"] < 50:
            alerts.append({
                "level": "info",
                "stage": "discovery",
                "message": "All companies scraped. Consider expanding discovery queries.",
            })

        return alerts

    def _get_recent_activity(self, session: Session, hours: int = 24) -> Dict[str, int]:
        """Get activity counts from the last N hours."""
        cutoff = datetime.utcnow() - timedelta(hours=hours)

        recent_tasks = session.exec(
            select(TaskLog).where(TaskLog.created_at >= cutoff)
        ).all()

        task_counts: Dict[str, int] = {}
        for task in recent_tasks:
            key = f"{task.task_name}_{task.status}"
            task_counts[key] = task_counts.get(key, 0) + 1

        return task_counts

    def generate_health_report(self) -> Dict[str, Any]:
        """Generate a full pipeline health report."""
        with get_session() as session:
            counts = self._get_pipeline_counts(session)
            conversions = self._get_conversion_rates(counts)
            alerts = self._detect_bottlenecks(counts)
            recent = self._get_recent_activity(session)

        self.alerts = alerts

        return {
            "generated_at": datetime.utcnow().isoformat(),
            "pipeline_counts": counts,
            "conversion_rates": conversions,
            "alerts": alerts,
            "recent_activity_24h": recent,
        }

    def log_health_report(self):
        """Generate and log the pipeline health report."""
        report = self.generate_health_report()

        logger.info("=" * 70)
        logger.info("PIPELINE HEALTH REPORT")
        logger.info("=" * 70)

        c = report["pipeline_counts"]["companies"]
        logger.info(
            f"Companies: {c['total']} total → {c['scraped']} scraped → "
            f"{c['scored']} scored → {c['high_fit']} high / {c['medium_fit']} medium / {c['disqualified']} disqualified"
        )

        ct = report["pipeline_counts"]["contacts"]
        logger.info(f"Contacts: {ct['total']} total, {ct['verified']} verified")

        o = report["pipeline_counts"]["outreach"]
        logger.info(
            f"Outreach: {o['total_emails_sent']} sent → "
            f"{o['replied']} replied → {o['active_leads']} active leads | "
            f"{o['opted_out']} opted out"
        )

        conv = report["conversion_rates"]
        logger.info(
            f"Conversions: Scrape→Score {conv['scrape_to_score_pct']}% | "
            f"Score→HighFit {conv['score_to_high_fit_pct']}% | "
            f"Sent→Reply {conv['sent_to_reply_pct']}% | "
            f"Reply→Lead {conv['reply_to_active_lead_pct']}%"
        )

        for alert in report["alerts"]:
            level = alert["level"].upper()
            if level == "CRITICAL":
                logger.error(f"[{level}] [{alert['stage']}] {alert['message']}")
            elif level == "WARNING":
                logger.warning(f"[{level}] [{alert['stage']}] {alert['message']}")
            else:
                logger.info(f"[{level}] [{alert['stage']}] {alert['message']}")

        logger.info("=" * 70)
        return report

    def save_report(self, report: Optional[Dict] = None, path: str = "data/pipeline_health.json"):
        """Persist the health report to disk."""
        if report is None:
            report = self.generate_health_report()

        with open(path, "w") as f:
            json.dump(report, f, indent=2)
        logger.info(f"Pipeline health report saved to {path}")


if __name__ == "__main__":
    monitor = PipelineHealthMonitor()
    monitor.log_health_report()
