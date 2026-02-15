
import json
from typing import List, Dict, Any
from sqlmodel import select, Session
from loguru import logger

from src.storage.db import get_session
from src.storage.models import Company, Contact, Outreach
from src.outreach.templates import select_template

class EmailGenerator:
    """
    Generates personalized email drafts for company contacts based on 
    enrichment data and context analysis.
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

    def generate_drifts(self, session: Session, company: Company):
        """Generates email drafts for all contacts in a company."""
        context = self._get_context(company)
        if not context:
            logger.warning(f"No context found for {company.name}, skipping email generation.")
            return

        # Fetch contacts
        # Assuming contacts related to the company are available via relationship or query
        # Using relationship `contacts`
        if not company.contacts:
            logger.info(f"No contacts found for {company.name}.")
            return

        # Select template based on company context
        template = select_template(context)
        
        for contact in company.contacts:
            # Skip if contact has no email
            if not contact.email:
                continue

            # Skip if outreach already exists
            existing = session.exec(select(Outreach).where(Outreach.contact_id == contact.id)).first()
            if existing:
                logger.info(f"Outreach already exists for {contact.email}, skipping.")
                continue

            # Skip unverified emails if policy dictates (optional, but good practice)
            # if not contact.is_verified: continue

            # Generate content
            # Need to pass company name explicitly because context might not have it or it might be raw
            contact_dict = {"name": contact.name, "email": contact.email}
            # Add company name to context for template filling
            context["company_name"] = company.name

            try:
                content = template.align_content(context, contact_dict)
                
                # Create Outreach record
                outreach = Outreach(
                    contact_id=contact.id,
                    template_id=template.id,
                    status="draft",
                    # Storing JSON of subject/body in content field for now
                    content=json.dumps(content) 
                )
                session.add(outreach)
                logger.info(f"Generated draft for {contact.email} using template {template.id}")
                
            except Exception as e:
                logger.error(f"Failed to generate email for {contact.email}: {e}")

    def run(self):
        """Main execution loop."""
        with get_session() as session:
            # Process companies that are scored and have context
            # We can filter by companies that have signal_metadata containing 'context_analysis'
            # But SQL LIKE is messy with JSON. 
            # Better to iterate high-fit companies.
            
            statement = select(Company).where(Company.is_scored == True) # Maybe add fitness_level filter later
            companies = session.exec(statement).all()
            
            if not companies:
                logger.info("No scored companies found to generate emails for.")
                return

            logger.info(f"Generating emails for {len(companies)} companies...")
            for company in companies:
                self.generate_drifts(session, company)
            
            session.commit()
            logger.info("Email generation complete.")

if __name__ == "__main__":
    generator = EmailGenerator()
    generator.run()
