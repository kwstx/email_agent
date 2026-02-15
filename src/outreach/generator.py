
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from sqlmodel import select, Session, desc
from loguru import logger

from src.storage.db import get_session
from src.storage.models import Company, Contact, Outreach
from src.outreach.templates import select_template_for_stage

# Configuration
SEQUENCE_GAP_DAYS = 3

class OutreachManager:
    """
    Manages the outreach lifecycle: generating initial drafts, scheduling follow-ups,
    and handling sequence exits upon reply.
    """
    
    def __init__(self):
        pass

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
        
        # 1. Check for Reply (Mock logic - in real world would check Outreach table for 'replied' status)
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


    def run(self):
        """Main execution loop."""
        with get_session() as session:
            # Get contacts that are eligible (high fit companies, verified emails?)
            # For iteration 1, let's look at all contacts in scored companies.
            
            statement = select(Company).where(Company.is_scored == True)
            companies = session.exec(statement).all()
            
            count = 0
            for company in companies:
                # Filter 'low_fit' if necessary, but assume scoring logic handles inclusion
                if not company.contacts:
                    continue
                    
                for contact in company.contacts:
                    if contact.outreach_status in ["completed", "replied", "bounced"]:
                        continue
                    
                    self.process_contact(session, contact, company)
                    count += 1
            
            session.commit()
            logger.info(f"Processed outreach logic for {count} contacts.")

if __name__ == "__main__":
    manager = OutreachManager()
    manager.run()
