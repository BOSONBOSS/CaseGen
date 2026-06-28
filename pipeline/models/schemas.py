from pydantic import BaseModel, Field
from typing import List, Optional


class TimelineEvent(BaseModel):
    year: Optional[str] = None
    event: str
    source: Optional[str] = None
    theme_tags: List[str] = Field(default_factory=list)


class KeyQuote(BaseModel):
    speaker: str
    quote: str
    source: Optional[str] = None
    theme_tags: List[str] = Field(default_factory=list)


class TaggedFact(BaseModel):
    fact: str
    theme_tags: List[str] = Field(default_factory=list)
    source: Optional[str] = None


class FactSheet(BaseModel):
    company_name: str = Field(description="Full legal name of the company")
    founding_year: Optional[str] = None
    industry: Optional[str] = None
    headquarters: Optional[str] = None
    revenue: Optional[str] = Field(None, description="Revenue figure with currency and year")
    key_people: List[str] = Field(default_factory=list)
    timeline_events: List[TimelineEvent] = Field(default_factory=list)
    challenges: List[str] = Field(default_factory=list)
    interventions: List[str] = Field(default_factory=list)
    outcomes: List[str] = Field(default_factory=list)
    key_quotes: List[KeyQuote] = Field(default_factory=list)
    themes: List[str] = Field(description="2-4 distinct narrative themes discovered")
    raw_facts: List[str] = Field(default_factory=list, description="Any other hard facts not captured above")
    tagged_facts: List[TaggedFact] = Field(
        default_factory=list,
        description="Facts with theme tags for filtering (e.g. Supply Chain, HR Culture)",
    )
