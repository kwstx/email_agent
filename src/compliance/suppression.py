
"""
Suppression List Manager

Manages the suppression list to prevent outreach to contacts who have
opted out, bounced, or been manually suppressed. Every outreach action
must check suppression status before sending.
"""

from datetime import datetime
from typing import List, Optional
from sqlmodel import select, Session
from loguru import logger

from src.storage.db import get_session
from src.storage.models import SuppressionList, Contact, Outreach


class SuppressionManager:
    """
    Central authority for suppression decisions. All outreach paths
    must consult this manager before sending any communication.
    """

    def is_suppressed(self, session: Session, email: str) -> bool:
        """
        Check if an email address or its domain is on the suppression list.
        Returns True if the contact must NOT be emailed.
        """
        email_lower = email.strip().lower()
        domain = email_lower.split("@")[-1] if "@" in email_lower else None

        # Check exact email suppression
        email_match = session.exec(
            select(SuppressionList).where(
                SuppressionList.type == "email",
                SuppressionList.value == email_lower
            )
        ).first()

        if email_match:
            logger.debug(f"Suppressed (email match): {email_lower} — reason: {email_match.reason}")
            return True

        # Check domain-level suppression
        if domain:
            domain_match = session.exec(
                select(SuppressionList).where(
                    SuppressionList.type == "domain",
                    SuppressionList.value == domain
                )
            ).first()

            if domain_match:
                logger.debug(f"Suppressed (domain match): {email_lower} — reason: {domain_match.reason}")
                return True

        return False

    def suppress_email(self, session: Session, email: str, reason: str = "manual") -> bool:
        """
        Add an email address to the suppression list.
        Returns True if newly added, False if already suppressed.
        """
        email_lower = email.strip().lower()

        existing = session.exec(
            select(SuppressionList).where(
                SuppressionList.type == "email",
                SuppressionList.value == email_lower
            )
        ).first()

        if existing:
            logger.info(f"Email already suppressed: {email_lower}")
            return False

        entry = SuppressionList(
            type="email",
            value=email_lower,
            reason=reason,
            created_at=datetime.utcnow()
        )
        session.add(entry)
        logger.info(f"Suppressed email: {email_lower} (reason: {reason})")
        return True

    def suppress_domain(self, session: Session, domain: str, reason: str = "manual") -> bool:
        """
        Add an entire domain to the suppression list.
        All contacts at this domain will be blocked from outreach.
        """
        domain_lower = domain.strip().lower()

        existing = session.exec(
            select(SuppressionList).where(
                SuppressionList.type == "domain",
                SuppressionList.value == domain_lower
            )
        ).first()

        if existing:
            logger.info(f"Domain already suppressed: {domain_lower}")
            return False

        entry = SuppressionList(
            type="domain",
            value=domain_lower,
            reason=reason,
            created_at=datetime.utcnow()
        )
        session.add(entry)
        logger.info(f"Suppressed domain: {domain_lower} (reason: {reason})")
        return True

    def unsuppress_email(self, session: Session, email: str) -> bool:
        """Remove an email from the suppression list."""
        email_lower = email.strip().lower()
        entry = session.exec(
            select(SuppressionList).where(
                SuppressionList.type == "email",
                SuppressionList.value == email_lower
            )
        ).first()

        if entry:
            session.delete(entry)
            logger.info(f"Unsuppressed email: {email_lower}")
            return True

        return False

    def unsuppress_domain(self, session: Session, domain: str) -> bool:
        """Remove a domain from the suppression list."""
        domain_lower = domain.strip().lower()
        entry = session.exec(
            select(SuppressionList).where(
                SuppressionList.type == "domain",
                SuppressionList.value == domain_lower
            )
        ).first()

        if entry:
            session.delete(entry)
            logger.info(f"Unsuppressed domain: {domain_lower}")
            return True

        return False

    def sync_from_contacts(self, session: Session) -> int:
        """
        Scan the contacts table and auto-suppress any contacts whose
        outreach_status is 'opt_out' or 'bounced'. This ensures the
        suppression list stays consistent with reply classification.
        Returns the number of newly suppressed entries.
        """
        count = 0

        # Opt-out contacts
        opt_out_contacts = session.exec(
            select(Contact).where(Contact.outreach_status == "opt_out")
        ).all()

        for contact in opt_out_contacts:
            if contact.email and self.suppress_email(session, contact.email, reason="opt_out"):
                count += 1

        # Bounced contacts
        bounced_contacts = session.exec(
            select(Contact).where(Contact.outreach_status == "bounced")
        ).all()

        for contact in bounced_contacts:
            if contact.email and self.suppress_email(session, contact.email, reason="bounced"):
                count += 1

        if count > 0:
            logger.info(f"Synced {count} new suppressions from contact statuses.")

        return count

    def get_all_suppressed(self, session: Session) -> List[SuppressionList]:
        """Return all entries on the suppression list."""
        return session.exec(select(SuppressionList)).all()

    def get_suppression_stats(self, session: Session) -> dict:
        """Return summary statistics of the suppression list."""
        all_entries = self.get_all_suppressed(session)

        stats = {
            "total": len(all_entries),
            "by_type": {"email": 0, "domain": 0},
            "by_reason": {}
        }

        for entry in all_entries:
            stats["by_type"][entry.type] = stats["by_type"].get(entry.type, 0) + 1
            reason = entry.reason or "unknown"
            stats["by_reason"][reason] = stats["by_reason"].get(reason, 0) + 1

        return stats
