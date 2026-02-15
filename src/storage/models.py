from datetime import datetime
from typing import List, Optional
from sqlmodel import Field, Relationship, SQLModel, create_engine, Session

class CompanySignalLink(SQLModel, table=True):
    company_id: Optional[int] = Field(default=None, foreign_key="company.id", primary_key=True)
    signal_id: Optional[int] = Field(default=None, foreign_key="signal.id", primary_key=True)
    intensity: float = Field(default=0.0)
    occurrences: int = Field(default=0)

class Company(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    domain: str = Field(index=True, unique=True)
    name: Optional[str] = None
    description: Optional[str] = None
    industry: Optional[str] = None
    website_content: Optional[str] = None
    
    # Enrichment status
    is_scraped: bool = Field(default=False)
    is_scored: bool = Field(default=False)
    fitness_score: int = Field(default=0)
    fitness_level: Optional[str] = None # high_fit, medium_fit, low_fit
    agent_maturity_level: Optional[str] = None # experimenting, production_ready, unknown
    signal_metadata: Optional[str] = None # JSON string for detailed signal info
    
    # Relationships
    contacts: List["Contact"] = Relationship(back_populates="company")
    signals: List["Signal"] = Relationship(
        back_populates="companies", 
        link_model=CompanySignalLink,
        sa_relationship_kwargs={"viewonly": True} # Keep it simple for now or use the link model directly
    )
    tasks: List["TaskLog"] = Relationship(back_populates="company")

class Contact(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    company_id: int = Field(foreign_key="company.id")
    name: str
    title: Optional[str] = None
    email: Optional[str] = Field(default=None, index=True)
    linkedin_url: Optional[str] = None
    is_verified: bool = Field(default=False)
    outreach_status: str = Field(default="pending") # pending, sent, replied, bounced
    
    company: Company = Relationship(back_populates="contacts")

class Signal(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True, unique=True)
    description: Optional[str] = None
    category: str # AI_AGENT_MATURITY, MARKET_POSITION, ENTERPRISE_RISK
    points: int
    
    companies: List[Company] = Relationship(back_populates="signals", link_model=CompanySignalLink)

class TaskLog(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    task_name: str
    company_id: Optional[int] = Field(default=None, foreign_key="company.id")
    status: str # started, completed, failed
    message: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    company: Optional[Company] = Relationship(back_populates="tasks")

class Outreach(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    contact_id: int = Field(foreign_key="contact.id")
    template_id: str
    sent_at: Optional[datetime] = None
    reply_received_at: Optional[datetime] = None
    status: str = Field(default="draft") # draft, queued, sent, failed, opened, clicked, replied
    content: Optional[str] = None
