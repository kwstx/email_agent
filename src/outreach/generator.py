
import json
import os
import smtplib
import ssl
from email.message import EmailMessage
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from sqlmodel import select, Session, desc
from loguru import logger
from dotenv import load_dotenv

load_dotenv()

from src.storage.db import get_session
from src.storage.models import Company, Contact, Outreach
from src.outreach.templates import select_template_for_stage
from src.compliance.suppression import SuppressionManager

# Configuration
SEQUENCE_GAP_DAYS = 3

class OutreachManager:
    """
    Manages the outreach lifecycle: generating initial drafts, scheduling follow-ups,
    and handling sequence exits upon reply.
    """
    
    def __init__(self):
        self.suppression_manager = SuppressionManager()
        self.smtp_server = os.getenv("SMTP_SERVER")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.smtp_user = os.getenv("SMTP_USER")
        self.smtp_pass = os.getenv("SMTP_PASSWORD")
        self.email_from = os.getenv("EMAIL_FROM", self.smtp_user)

    def _get_context(self, company: Company) -> Dict[str, Any]:
        """Attributes the context dictionary from company metadata."""
        if not company.signal_metadata:
            return {}
        try:
            meta = json.loads(company.signal_metadata)
            return meta.get("context_analysis", {})
        except json.JSONDecodeError:
            return {}

    def _generate_draft(self, session: Session, contact: Contact, company: Company, stage: int):
        """Generates an email draft for a specific stage."""
        context = self._get_context(company)
        # Add company name to context for template filling
        context["company_name"] = company.name
        
        template = select_template_for_stage(stage, context)
        if not template:
            logger.info(f"No template found for stage {stage}, ending sequence for {contact.email}.")
            contact.outreach_status = "completed"
            session.add(contact)
            return

        # Generate content
        contact_dict = {"name": contact.name, "email": contact.email}
        try:
            content = template.align_content(context, contact_dict)
            
            # Create Outreach record
            outreach = Outreach(
                contact_id=contact.id,
                template_id=template.id,
                stage=stage,
                status="draft",
                content=json.dumps(content) 
            )
            session.add(outreach)
            
            # Update Contact state
            contact.outreach_stage = stage
            # Note: last_outreach_sent_at should be updated when the email is actually SENT.
            # But for the sequence logic to proceed, we assume the draft will be handled.
            # If we don't send it, the next check will see 'draft' status and wait.
            
            logger.info(f"Generated Stage {stage} draft for {contact.email} ({template.id})")
            
        except Exception as e:
            logger.error(f"Failed to generate email for {contact.email}: {e}")

    def process_contact(self, session: Session, contact: Contact, company: Company):
        """Decides the next action for a single contact."""
        
        # 0. COMPLIANCE GATE: Check suppression list before any action
        if contact.email and self.suppression_manager.is_suppressed(session, contact.email):
            if contact.outreach_status not in ["suppressed", "opt_out"]:
                contact.outreach_status = "suppressed"
                session.add(contact)
                logger.info(f"Contact {contact.email} is suppressed. Blocking outreach.")
            return

        # 1. Check for Reply
        # If any outreach has status 'replied', update contact and stop.
        last_outreach = session.exec(select(Outreach).where(Outreach.contact_id == contact.id).order_by(desc(Outreach.id))).first()
        
        if last_outreach and last_outreach.status == "replied":
            # If already classified (e.g. active_lead, opt_out), don't overwrite with generic 'replied'
            ignore_statuses = ["replied", "active_lead", "deferred", "opt_out", "referral_needed", "not_interested"]
            if contact.outreach_status not in ignore_statuses:
                contact.outreach_status = "replied"
                session.add(contact)
                logger.info(f"Contact {contact.email} replied. Sequence stopped.")
            return

        # 2. Status: PENDING (Start Sequence)
        if contact.outreach_status == "pending":
            # Start Stage 1
            if contact.email: # Verify email exists
                logger.info(f"Starting sequence for {contact.email}...")
                contact.outreach_status = "active"
                self._generate_draft(session, contact, company, 1)
                session.add(contact)
            return

        # 3. Status: ACTIVE (Continue Sequence)
        if contact.outreach_status == "active":
            if not last_outreach:
                # Should not happen if active, but fail safe to Stage 1
                self._generate_draft(session, contact, company, 1)
                return

            # Check if pending draft exists
            if last_outreach.status in ["draft", "queued"]:
                # Waiting for send, do nothing
                return
            
            # Check for generic failure or bounce
            if last_outreach.status in ["failed", "bounced"]:
                contact.outreach_status = "bounced"
                session.add(contact)
                logger.warning(f"Outreach failed for {contact.email}, stopping sequence.")
                return

            # Check gap if sent
            if last_outreach.status == "sent":
                if not last_outreach.sent_at:
                    # Fallback if sent_at is missing for some reason
                    last_outreach.sent_at = datetime.utcnow()
                    session.add(last_outreach)
                
                # Check time passed
                delta = datetime.utcnow() - last_outreach.sent_at
                if delta.days >= SEQUENCE_GAP_DAYS:
                    next_stage = last_outreach.stage + 1
                    logger.info(f"Gap requirement met ({delta.days} days). Advancing {contact.email} to Stage {next_stage}.")
                    self._generate_draft(session, contact, company, next_stage)
                else:
                    # Still waiting in gap
                    pass


    def _send_email(self, recipient_email: str, subject: str, body: str) -> bool:
        """Actually transmits the email via SMTP."""
        if not all([self.smtp_server, self.smtp_user, self.smtp_pass]):
            logger.error("SMTP credentials not fully configured in .env")
            return False

        msg = EmailMessage()
        msg.set_content(body)
        msg['Subject'] = subject
        msg['From'] = self.email_from
        msg['To'] = recipient_email

        try:
            context = ssl.create_default_context()
            if self.smtp_port == 465:
                with smtplib.SMTP_SSL(self.smtp_server, self.smtp_port, context=context) as server:
                    server.login(self.smtp_user, self.smtp_pass)
                    server.send_message(msg)
            else:
                with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                    server.starttls(context=context)
                    server.login(self.smtp_user, self.smtp_pass)
                    server.send_message(msg)
            return True
        except Exception as e:
            logger.error(f"Failed to send email to {recipient_email}: {e}")
            return False

    def send_drafts(self):
        """Finds all drafts and sends them."""
        with get_session() as session:
            statement = select(Outreach).where(Outreach.status == "draft")
            drafts = session.exec(statement).all()

            if not drafts:
                logger.info("No outreach drafts to send.")
                return

            logger.info(f"Found {len(drafts)} drafts to send.")
            for outreach in drafts:
                contact = session.get(Contact, outreach.contact_id)
                if not contact or not contact.email:
                    continue

                try:
                    content = json.loads(outreach.content)
                    subject = content.get("subject")
                    body = content.get("body")

                    if self._send_email(contact.email, subject, body):
                        outreach.status = "sent"
                        outreach.sent_at = datetime.utcnow()
                        contact.last_outreach_sent_at = outreach.sent_at
                        session.add(outreach)
                        session.add(contact)
                        logger.success(f"Sent Stage {outreach.stage} email to {contact.email}")
                    else:
                        outreach.status = "failed"
                        session.add(outreach)
                except Exception as e:
                    logger.error(f"Error processing draft {outreach.id}: {e}")
                    outreach.status = "failed"
                    session.add(outreach)

            session.commit()

    def run(self):
        """Main execution loop."""
        with get_session() as session:
            # 1. Generate new drafts
            statement = select(Company).where(Company.is_scored == True)
            companies = session.exec(statement).all()
            
            count = 0
            for company in companies:
                if not company.contacts:
                    continue
                    
                for contact in company.contacts:
                    if contact.outreach_status in ["completed", "replied", "bounced", "opt_out", "suppressed"]:
                        continue
                    
                    self.process_contact(session, contact, company)
                    count += 1
            
            session.commit()
            logger.info(f"Processed outreach sequence logic for {count} contacts.")
        
        # 2. Send the drafts
        self.send_drafts()

if __name__ == "__main__":
    manager = OutreachManager()
    manager.run()
