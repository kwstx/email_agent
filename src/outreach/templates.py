
from typing import Dict, Any, List, Optional

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
            "agent_platform": integrations[0] if integrations else "your agent infrastructure"
        }

        # Render
        subject = self.subject_template.format(**variables)
        body = self.body_template.format(**variables)

        return {"subject": subject, "body": body}

# --- STAGE 1: INITIAL OUTREACH ---
STAGE_1_TEMPLATES = [
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

# --- STAGE 2: ARCHITECTURAL CONSIDERATIONS ---
STAGE_2_TEMPLATES = [
    EmailTemplate(
        id="followup_architecture",
        subject_template="Re: Connecting / {company_name} agents", # Threading
        body_template="""Hi {first_name},

Wanted to bump this just in case it got buried.

I was thinking more about how {company_name} is structuring its agent systems. One thing I’ve noticed talking to other teams using {agent_platform} is the tension between monolithic agent definitions and micro-agent architectures.

When agents start calling other agents, maintaining a single source of truth for permissions becomes a nightmare. We’ve been exploring a "policy-as-infrastructure" approach that sits between the orchestration layer and the LLM 

Curious if you've run into this architectural bottleneck yet?

Best,
Kwstas""",
        trigger_condition=lambda ctx: True
    )
]

# --- STAGE 3: GOVERNANCE RISKS ---
STAGE_3_TEMPLATES = [
    EmailTemplate(
        id="followup_governance",
        subject_template="Re: Connecting / {company_name} agents",
        body_template="""Hi {first_name},

I promise not to swamp your inbox, but wanted to share one last thought on governance.

As you scale {company_name}'s agent deployment, "shadow agents" (unmonitored scripts running in production) often become a silent risk. Without a dedicated governance layer, it's hard to prove who authorized a specific tool execution or API call.

We're building lightweight logging that captures the full "chain of thought" alongside the actual tool outputs for auditability.

Is compliance or auditability something currently on your radar?

Best,
Kwstas""",
        trigger_condition=lambda ctx: True
    )
]

# --- STAGE 4: OPERATIONAL SAFEGUARDS (BREAKUP) ---
STAGE_4_TEMPLATES = [
    EmailTemplate(
        id="followup_operational",
        subject_template="Re: Connecting / {company_name} agents",
        body_template="""Hi {first_name},

I’ll keep this brief and this will be my last email.

From an operational standpoint, we’ve found that most teams lack a "kill switch" for specific agent behaviors. If an agent enters a loop or starts hallucinating tool parameters, you often have to restart the whole container rather than just blocking that specific action.

If you ever want to chat about operational safeguards or runtime interception for agents, let me know. I’ll stop reaching out for now to save your inbox!

Best of luck with {company_name},
Kwstas""",
        trigger_condition=lambda ctx: True
    )
]

STAGES = {
    1: STAGE_1_TEMPLATES,
    2: STAGE_2_TEMPLATES,
    3: STAGE_3_TEMPLATES,
    4: STAGE_4_TEMPLATES
}

def select_template_for_stage(stage: int, context: Dict[str, Any]) -> Optional[EmailTemplate]:
    """Selects the appropriate template for a given stage and context."""
    templates = STAGES.get(stage)
    if not templates:
        return None
        
    for template in templates:
        if template.trigger_condition and template.trigger_condition(context):
            return template
    return templates[-1] # Fallback for that stage
