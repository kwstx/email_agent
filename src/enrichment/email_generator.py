import asyncio
import re
import smtplib
import socket
import dns.resolver
import random
import string
from typing import List, Optional, Tuple, Dict

from sqlmodel import select
from loguru import logger
from src.storage.db import get_session
from src.storage.models import Company, Contact

class EmailGenerator:
    """
    Generates and validates corporate email addresses using pattern matching 
    and server-level verification (DNS/SMTP).
    """
    
    def __init__(self):
        self.common_patterns = [
            "{first}.{last}@{domain}",    # john.doe@company.com
            "{first}@{domain}",           # john@company.com
            "{f}{last}@{domain}",         # jdoe@company.com
            "{first}{l}@{domain}",        # johnd@company.com
            "{first}_{last}@{domain}",    # john_doe@company.com
            "{last}.{first}@{domain}",    # doe.john@company.com
            "{first}{last}@{domain}"      # johndoe@company.com
        ]
        # Regex to find emails in text
        self.email_regex = re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}')

    def _get_mx_record(self, domain: str) -> Optional[str]:
        """Resolves the MX record for a domain."""
        try:
            records = dns.resolver.resolve(domain, 'MX')
            # Sort by preference and pick the first one
            best_record = sorted(records, key=lambda r: r.preference)[0]
            return str(best_record.exchange).rstrip('.')
        except Exception as e:
            logger.debug(f"Could not get MX record for {domain}: {e}")
            return None

    def _verify_smtp(self, email: str, mx_host: str) -> bool:
        """
        Connects to the mail server to verify if the email exists.
        Note: This may fail if port 25 is blocked by ISP or if the server catches all.
        """
        try:
            # Determine local hostname
            local_hostname = socket.gethostname()
            
            # Connect to SMTP server
            server = smtplib.SMTP(mx_host, 25, timeout=5)
            server.set_debuglevel(0)
            
            # HELO/EHLO
            server.helo(local_hostname)
            
            # MAIL FROM (use a dummy sender)
            server.mail('verify@example.com')
            
            # RCPT TO (check the actual recipient)
            code, message = server.rcpt(email)
            server.quit()
            
            # 250 = Success (Address exists and can receive mail)
            if code == 250:
                logger.debug(f"SMTP Verify Success: {email} (Code {code})")
                return True
            else:
                logger.debug(f"SMTP Verify Failed: {email} (Code {code} - {message})")
                return False
                
        except socket.error as e:
            logger.debug(f"Socket error connecting to {mx_host}: {e}")
            return False
        except smtplib.SMTPException as e:
            logger.debug(f"SMTP error for {email} on {mx_host}: {e}")
            return False
        except Exception as e:
            logger.debug(f"Unexpected error verifying {email}: {e}")
            return False

    def _is_catch_all(self, domain: str, mx_host: str) -> bool:
        """Checks if the mail server accepts emails for non-existent users."""
        # Generate a random non-existent user
        random_user = ''.join(random.choices(string.ascii_lowercase + string.digits, k=15))
        test_email = f"{random_user}@{domain}"
        
        # If verify returns True for a gibberish user, it's a catch-all
        return self._verify_smtp(test_email, mx_host)

    def _extract_emails_from_text(self, text: str, domain: str) -> List[str]:
        """Finds emails in text that match the company domain."""
        if not text:
            return []
        found = self.email_regex.findall(text)
        # Filter for emails belonging to the domain
        return [e.lower() for e in found if e.lower().endswith(f"@{domain}")]

    def _infer_pattern(self, existing_emails: List[str], domain: str) -> Optional[str]:
        """
        Analyzes existing emails to determine the naming convention.
        Returns a format string like "{first}.{last}@{domain}" if a pattern is confident.
        """
        if not existing_emails:
            return None
        
        # Simple heuristic: Check which pattern matches the most existing emails
        # This requires reverse-engineering the names from the emails, which is hard without the names.
        # But we can look at the structure.
        
        pattern_counts = {p: 0 for p in self.common_patterns}
        
        for email in existing_emails:
            local_part = email.split('@')[0]
            
            if '.' in local_part:
                # Could be first.last or last.first
                pattern_counts["{first}.{last}@{domain}"] += 1 # Assume first.last is more common
            elif '_' in local_part:
                pattern_counts["{first}_{last}@{domain}"] += 1
            else:
                # No symbols. Hard to distinguish first vs fLast vs firstL etc.
                # Just ignore or guess based on length?
                pass
        
        # Get the most common pattern
        best_pattern = max(pattern_counts, key=pattern_counts.get)
        if pattern_counts[best_pattern] > 0:
            return best_pattern
        return None

    def generate_candidates(self, contact: Contact, domain: str, pattern: Optional[str] = None) -> List[str]:
        """Generates a list of probable emails for a contact."""
        if not contact.name:
            return []
            
        parts = contact.name.split()
        if len(parts) < 2:
            return [] # Need at least first and last name for most patterns
            
        first = parts[0].strip().replace("'", "").replace(".", "")
        last = parts[-1].strip().replace("'", "").replace(".", "") # Use last word as last name
        
        data = {
            "first": first.lower(),
            "last": last.lower(),
            "f": first[0].lower(),
            "l": last[0].lower(),
            "domain": domain
        }
        
        candidates = []
        if pattern:
            # If we have a high-confidence pattern, try that primarily
            try:
                candidates.append(pattern.format(**data))
            except:
                pass
        
        # Add all common patterns as backups (or primaries if no pattern)
        for p in self.common_patterns:
            try:
                cand = p.format(**data)
                if cand not in candidates:
                    candidates.append(cand)
            except:
                pass
                
        return candidates

    async def process_contacts(self):
        """Main loop to process contacts with missing emails."""
        with get_session() as session:
            # Fetch contacts without verified emails
            # We can filter by companies that are high_fit to save time
            statement = select(Contact, Company).join(Company).where(Contact.email == None).where(Company.fitness_level == "high_fit")
            results = session.exec(statement).all()
            
            logger.info(f"Found {len(results)} contacts to process for emails.")
            
            # Group by company to minimize MX lookups and pattern inference
            company_contacts = {}
            for contact, company in results:
                if company.id not in company_contacts:
                    company_contacts[company.id] = {"company": company, "contacts": []}
                company_contacts[company.id]["contacts"].append(contact)
            
            for company_id, data in company_contacts.items():
                company = data["company"]
                contacts = data["contacts"]
                domain = company.domain
                
                logger.info(f"Processing {len(contacts)} contacts for {company.name} ({domain})")
                
                # 1. Get MX Record
                mx_host = self._get_mx_record(domain)
                if not mx_host:
                    logger.warning(f"No MX record found for {domain}. Skipping SMTP verification.")
                    # Can't verify, skip or assume unverified? Prompt says "store only those that pass".
                    # If we can't verify, we can't store.
                    continue
                
                # 2. Check for Catch-All
                if await asyncio.to_thread(self._is_catch_all, domain, mx_host):
                    logger.warning(f"Domain {domain} is catch-all. Cannot verify individual emails via SMTP.")
                    # Strategies for catch-all:
                    # 1. Use inferred pattern if very strong (e.g. matched 3+ existing emails).
                    # 2. Store the most likely one but mark verification status as 'catch_all' or similar?
                    # The prompt says 'store only those addresses that pass verification'.
                    # A catch-all response technically 'passes' SMTP check (250 OK), but logic suggests it's not a verified *user*.
                    # We will skip processing for now to be safe, or perhaps store if we have a strong pattern.
                    # Let's verify if we have an inferred pattern.

                    existing_emails = self._extract_emails_from_text(company.website_content, domain)
                    inferred_pattern = self._infer_pattern(existing_emails, domain)
                    
                    if inferred_pattern:
                        logger.info(f"Catch-all domain {domain}, but found pattern {inferred_pattern}. Using pattern to generate best guess.")
                        # We will generate just ONE candidate based on the pattern and store it, 
                        # but perhaps we shouldn't mark it as fully verified?
                        # The Contact model has 'is_verified'. We can leave it False or add a note.
                        # For this task, "store only those addresses that pass verification" is strict.
                        # I will SKIP storing for catch-all to adhere to strict interpretation, 
                        # OR I could assume "pass verification" means "sending to it won't bounce immediate".
                        # But that's dangerous for sender reputation.
                        # Decision: Skip catch-all domains for "verified" email storage.
                        pass
                    continue

                # 3. Infer Pattern from website content
                existing_emails = self._extract_emails_from_text(company.website_content, domain)
                inferred_pattern = self._infer_pattern(existing_emails, domain)
                if inferred_pattern:
                    logger.info(f"Inferred email pattern for {domain}: {inferred_pattern}")
                
                # 4. Generate and Verify
                for contact in contacts:
                    candidates = self.generate_candidates(contact, domain, inferred_pattern)
                    
                    found_valid = False
                    for email in candidates:
                        # Use run_in_executor for blocking SMTP calls
                        is_valid = await asyncio.to_thread(self._verify_smtp, email, mx_host)
                        
                        if is_valid:
                            contact.email = email
                            contact.is_verified = True
                            session.add(contact)
                            session.commit()
                            logger.success(f"Verified email for {contact.name}: {email}")
                            found_valid = True
                            break # Stop after finding one valid email
                    
                    if not found_valid:
                        logger.info(f"Could not verify any email for {contact.name}")

if __name__ == "__main__":
    generator = EmailGenerator()
    asyncio.run(generator.process_contacts())
