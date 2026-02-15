
from typing import Dict, Any

class EmailTemplate:
    def __init__(self, id: str, subject_template: str, body_template: str, trigger_condition: callable = None):
        self.id = id
        self.subject_template = subject_template
        self.body_template = body_template
        self.trigger_condition = trigger_condition

    def align_content(self, context: Dict[str, Any], contact: Dict[str, Any]) -> Dict[str, str]:
        """
        Fills the template with context and contact data.
        Returns a dictionary with 'subject' and 'body'.
        """
        # Prepare variables
        integrations = context.get("integrations", [])
        
        # Observation: "really like what you're doing with..."
        if integrations:
            observation = f"building agent workflows on {integrations[0]}"
        else:
            observation = "deploying autonomous agents"

        # Risk Phrase: "helping teams understand and manage..."
        gaps = context.get("governance_gaps", [])
        gap = gaps[0].lower() if gaps else "unexpected behavior"
        
        comps = context.get("compliance_exposure", [])
        if comps:
            risk_phrase = f"data privacy risks like {comps[0]}"
        elif "audit" in gap or "logging" in gap:
            risk_phrase = "auditability for unmonitored executions"
        else:
            risk_phrase = "moments when agents might act unexpectedly"

        variables = {
            "first_name": (contact.get("name") or "").split(" ")[0],
            "company_name": context.get("company_name", "your company"),
            "observation": observation,
            "risk_phrase": risk_phrase,
        }

        # Render
        subject = self.subject_template.format(**variables)
        body = self.body_template.format(**variables)

        return {"subject": subject, "body": body}

# Define Templates
TEMPLATES = [
    EmailTemplate(
        id="founder_discovery_compliance",
        subject_template="Quick question / {company_name} agents",
        body_template="""Hi {first_name},

I’ve been following {company_name} and really like to see that you're {observation}.

I’m currently working on a small startup, Engram, focused on runtime governance for autonomous agents — basically, helping teams understand and manage {risk_phrase}.

This isn’t a pitch — I’m just trying to learn from teams running real agent systems. I’d love to hear how your team thinks about these tricky situations and share a few insights I’ve seen work for other small AI teams.

Would you be open to a very quick 10-minute chat? Totally informal, just a conversation.

Thanks so much,
Kwstas""",
        trigger_condition=lambda ctx: bool(ctx.get("compliance_exposure"))
    ),
    EmailTemplate(
        id="founder_discovery_general",
        subject_template="Connecting / {company_name} agents",
        body_template="""Hi {first_name},

I’ve been following {company_name} and really like that you're {observation}.

I’m currently working on a small startup, Engram, focused on runtime governance for autonomous agents — basically, helping teams understand and manage {risk_phrase}.

This isn’t a pitch — I’m just trying to learn from teams running real agent systems. I’d love to hear how your team thinks about these tricky situations and share a few insights I’ve seen work for other small AI teams.

Would you be open to a very quick 10-minute chat? Totally informal, just a conversation.

Thanks so much,
Kwstas""",
        trigger_condition=lambda ctx: True # Fallback
    )
]

def select_template(context: Dict[str, Any]) -> EmailTemplate:
    """Selects the first matching template based on context."""
    for template in TEMPLATES:
        if template.trigger_condition and template.trigger_condition(context):
            return template
    return TEMPLATES[-1] # Fallback
