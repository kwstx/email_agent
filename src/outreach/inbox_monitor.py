
import os
import imap_tools
from imap_tools import MailBox, AND
from sqlmodel import select
from loguru import logger
from datetime import datetime
from openai import OpenAI
from src.storage.db import get_session
from src.storage.models import Contact, Outreach, Reply
from src.compliance.suppression import SuppressionManager

class InboxMonitor:
    def __init__(self):
        self.imap_server = os.getenv("IMAP_SERVER", "imap.gmail.com")
        self.email_user = os.getenv("IMAP_USER", "")
        self.email_pass = os.getenv("IMAP_PASSWORD", "")
        self.openai_key = os.getenv("OPENAI_API_KEY")
        self.suppression_manager = SuppressionManager()
        
        self.openai_client = None
        if self.openai_key:
            try:
                self.openai_client = OpenAI(api_key=self.openai_key)
            except Exception as e:
                logger.warning(f"Could not initialize OpenAI client: {e}")

    def connect(self):
        if not self.email_user or not self.email_pass:
            raise ValueError("IMAP_USER and IMAP_PASSWORD must be set in .env")
        return MailBox(self.imap_server).login(self.email_user, self.email_pass)

    def classify_reply_content(self, subject: str, body: str) -> str:
        """
        Classify the reply into: interest, deferral, irrelevance, referral, opt_out.
        """
        content_lower = (subject + " " + body).lower()
        
        # 1. Critical Keywords (Rule-based)
        if any(x in content_lower for x in ["unsubscribe", "remove me", "stop emailing", "opt out", "take me off"]):
            return "opt_out"
            
        if any(x in content_lower for x in ["out of office", "vacation", "auto-reply", "automatic reply", "on leave"]):
            return "deferral"

        # 2. LLM-based classification (if available)
        if self.openai_client:
            try:
                response = self.openai_client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": (
                            "You are an email classifier for B2B sales outreach. "
                            "Classify the reply into one of these exact categories: 'interest', 'deferral', 'irrelevance', 'referral', 'opt_out'. "
                            "If the email is asking for a meeting, demo, or more info, classify as 'interest'. "
                            "If the email says 'not interested' or 'no thanks', classify as 'irrelevance'. "
                            "Return ONLY the category name."
                        )},
                        {"role": "user", "content": f"Subject: {subject}\n\nBody: {body[:1000]}"} # Truncate body
                    ],
                    max_tokens=10
                )
                category = response.choices[0].message.content.strip().lower()
                valid_categories = ["interest", "deferral", "irrelevance", "referral", "opt_out"]
                if category in valid_categories:
                    return category
                
                # Fallback if LLM returns something else
                if "interest" in category: return "interest"
                if "remove" in category or "stop" in category: return "opt_out"
                if "no" in category: return "irrelevance"
                
            except Exception as e:
                logger.error(f"OpenAI classification failed: {e}")
        
        # 3. Keyword Fallback
        if any(x in content_lower for x in ["interested", "call", "demo", "chat", "time for", "discuss", "pricing"]):
            return "interest"
        
        if any(x in content_lower for x in ["not interested", "no thanks", "pass", "unsubscribe"]):
            return "irrelevance" # or opt_out if explicit
            
        return "irrelevance" # Default safely

    def process_inbox(self):
        """Scans the inbox for unread replies and processes them."""
        logger.info("Scanning inbox for replies...")
        
        try:
            with self.connect() as mailbox:
                # Fetch UNSEEN messages
                # Mark as seen=False to avoid marking them read until processed? 
                # Actually, standard practice is to mark them read if processed.
                # However, for testing, maybe Keep as unread? No, production needs to mark as read.
                # imap_tools fetches are read-only unless mark_seen=True (default True in fetch).
                # We'll use default.
                
                # Fetch only UNSEEN
                messages = list(mailbox.fetch(AND(seen=False), limit=50, mark_seen=True))
                
                if not messages:
                    logger.info("No new unread messages found.")
                    return

                logger.info(f"Found {len(messages)} unread messages.")

                with get_session() as session:
                    for msg in messages:
                        sender_email = msg.from_values.email
                        logger.info(f"Processing email from {sender_email}: {msg.subject}")
                        
                        # Find contact by email
                        # Note: Email matching is tricky if user has aliases. Doing exact match for now.
                        contact = session.exec(select(Contact).where(Contact.email == sender_email)).first()
                        
                        if not contact:
                            logger.warning(f"Ignored email from unknown contact: {sender_email}")
                            continue
                        
                        # Extract content (prefer text, fallback to html)
                        body_content = msg.text or msg.html or ""
                        
                        # Classify
                        category = self.classify_reply_content(msg.subject, body_content)
                        logger.info(f"Classified reply from {contact.email} as: {category}")
                        
                        # Store Reply
                        reply = Reply(
                            contact_id=contact.id,
                            content=body_content,
                            classification=category,
                            received_at=msg.date,
                            original_subject=msg.subject,
                            thread_id=msg.headers.get("message-id", [None])[0]
                        )
                        session.add(reply)
                        
                        # Update last Outreach record to 'replied'
                        last_outreach = session.exec(select(Outreach).where(Outreach.contact_id == contact.id).order_by(Outreach.id.desc())).first()
                        if last_outreach:
                            last_outreach.status = "replied"
                            last_outreach.reply_received_at = msg.date
                            session.add(last_outreach)
                        
                        # Update Contact status based on classification
                        if category == "interest":
                            contact.outreach_status = "active_lead" # Ready for sales workflow
                        elif category == "deferral":
                            contact.outreach_status = "deferred"
                        elif category == "referral":
                            contact.outreach_status = "referral_needed"
                        elif category == "opt_out":
                            contact.outreach_status = "opt_out"
                            # Immediately add to suppression list
                            self.suppression_manager.suppress_email(
                                session, contact.email, reason="opt_out"
                            )
                            logger.info(f"Contact {contact.email} opted out — added to suppression list.")
                        elif category == "irrelevance":
                            if "bounced" not in contact.outreach_status:
                                contact.outreach_status = "not_interested"
                        
                        session.add(contact)
                    
                    session.commit()
                    logger.success(f"Processed {len(messages)} replies.")

        except Exception as e:
            logger.error(f"Error processing inbox: {e}")
            raise

if __name__ == "__main__":
    monitor = InboxMonitor()
    monitor.process_inbox()
