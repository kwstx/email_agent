
import sys
import os
import json
sys.path.append(os.getcwd())

from sqlmodel import select
from src.storage.db import get_session
from src.storage.models import Outreach, Contact, Company

def check():
    with get_session() as session:
        outreaches = session.exec(select(Outreach)).all()
        
        with open("outreach_samples_v2.txt", "w", encoding="utf-8") as f:
            f.write(f"Total outreaches: {len(outreaches)}\n")
            
            for i, outreach in enumerate(outreaches[:3]):
                contact = session.get(Contact, outreach.contact_id)
                if not contact:
                    continue
                company = contact.company
                
                f.write(f"\n--- SAMPLE {i+1} ---\n")
                f.write(f"To: {contact.name} <{contact.email}>\n")
                f.write(f"Company: {company.name} ({company.domain})\n")
                f.write(f"Template: {outreach.template_id}\n")
                
                try:
                    content = json.loads(outreach.content)
                    f.write(f"Subject: {content.get('subject')}\n")
                    f.write("Body:\n")
                    f.write(content.get('body'))
                except Exception as e:
                    f.write(f"Error parse: {e}")
                f.write("\n-------------------\n")
    print("Samples written to outreach_samples_v2.txt")

if __name__ == "__main__":
    check()
