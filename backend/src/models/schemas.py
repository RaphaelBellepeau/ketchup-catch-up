"""Pydantic v2 models for the Catch-Up API."""

from datetime import datetime

from pydantic import BaseModel, Field


# ── Profile ─────────────────────────────────────────────

class UserProfile(BaseModel):
    id: str
    phone: str
    name: str
    created_at: datetime


# ── Friends ─────────────────────────────────────────────

class Friend(BaseModel):
    id: str
    name: str
    phone: str
    is_on_app: bool = False


class AddFriendRequest(BaseModel):
    phone: str
    name: str


# ── Groups ──────────────────────────────────────────────

class CreateGroupRequest(BaseModel):
    name: str
    member_ids: list[str]


class Group(BaseModel):
    id: str
    name: str
    members: list[str] = []


# ── Catchups ────────────────────────────────────────────

class CreateCatchupRequest(BaseModel):
    group_id: str
    type: str = "one_shot"  # one_shot | recurring
    time_window: str = "next 2 weeks"
    vibe: str = ""  # dinner, drinks, activity...
    frequency: str | None = None  # for recurring (mocked)


class Catchup(BaseModel):
    id: str
    group_id: str
    type: str
    status: str = "pending"  # pending | negotiating | proposed | accepted | done
    time_window: str
    vibe: str
    created_at: datetime


# ── Negotiation ─────────────────────────────────────────

class NegotiationMessage(BaseModel):
    """A single message in the A2A negotiation dialogue."""

    agent_name: str
    role: str  # propose | counter | accept | reject | info
    content: str
    data: dict = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.now)


class Proposal(BaseModel):
    id: str
    catchup_id: str
    venue: str
    time: str
    activity: str = ""
    justification: str = ""


class VoteRequest(BaseModel):
    vote: str  # accept | reject
    reason: str = ""


# ── Feedback ────────────────────────────────────────────

class FeedbackRequest(BaseModel):
    catchup_id: str
    rating: int = Field(ge=1, le=5)
    tags: list[str] = []
    comment: str = ""


class Feedback(BaseModel):
    id: str
    catchup_id: str
    user_id: str
    rating: int
    liked: list[str] = []
    disliked: list[str] = []
    comment: str = ""


# ── Memory ──────────────────────────────────────────────

class Memory(BaseModel):
    id: str
    user_id: str
    scope: str = "general"  # general | cuisine | schedule | social
    content: str
    source: str = "onboarding"  # onboarding | feedback | manual
    created_at: datetime
