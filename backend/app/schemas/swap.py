"""
Pydantic Schemas for Skill Swap Economy
=======================================
Defines type-safe request/response schemas for:
- Skill taxonomy and suggestions
- User competencies (teaching and learning)
- Swap profiles (private view vs. public privacy-preserving view)
- Weekly availability windows and blackout intervals
- Geocoding responses with coarse grid coords (~1 km)
"""

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


# ── Canonical Taxonomy Schemas ───────────────────────────────────────
class SkillBase(BaseModel):
    slug: str = Field(..., max_length=100)
    display_name: str = Field(..., max_length=100)
    category: str = Field(..., max_length=50)
    aliases: list[str] = Field(default_factory=list)


class SkillResponse(SkillBase):
    id: uuid.UUID
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SkillSuggestRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    category: str = Field(..., min_length=2, max_length=50)


class SkillCategoryGroup(BaseModel):
    category: str
    skills: list[SkillResponse]


# ── User Skill Competency Schemas ────────────────────────────────────
class UserSkillItem(BaseModel):
    skill_slug: str
    level: Literal["beginner", "intermediate", "advanced", "expert"] = "intermediate"
    years_experience: int | None = Field(default=None, ge=0, le=70)
    notes: str | None = Field(default=None, max_length=500)


class UserSkillResponse(BaseModel):
    id: uuid.UUID
    skill: SkillResponse
    skill_type: Literal["teach", "learn"]
    level: str
    years_experience: int | None
    notes: str | None

    model_config = ConfigDict(from_attributes=True)


# ── Availability Schemas ─────────────────────────────────────────────
class AvailabilityWindowItem(BaseModel):
    day_of_week: int = Field(..., ge=0, le=6, description="0=Monday, 6=Sunday")
    start_time_utc: str = Field(..., pattern=r"^\d{2}:\d{2}$", description="HH:MM in UTC")
    end_time_utc: str = Field(..., pattern=r"^\d{2}:\d{2}$", description="HH:MM in UTC")

    @field_validator("end_time_utc")
    @classmethod
    def validate_times(cls, v: str, info: Any) -> str:
        start = info.data.get("start_time_utc")
        if start and v <= start:
            raise ValueError("end_time_utc must be after start_time_utc")
        return v


class AvailabilityWindowResponse(AvailabilityWindowItem):
    id: uuid.UUID

    model_config = ConfigDict(from_attributes=True)


class AvailabilityBlackoutItem(BaseModel):
    start_datetime_utc: datetime
    end_datetime_utc: datetime
    reason: str | None = Field(default=None, max_length=255)

    @field_validator("end_datetime_utc")
    @classmethod
    def validate_dates(cls, v: datetime, info: Any) -> datetime:
        start = info.data.get("start_datetime_utc")
        if start and v <= start:
            raise ValueError("end_datetime_utc must be after start_datetime_utc")
        return v


class AvailabilityBlackoutResponse(AvailabilityBlackoutItem):
    id: uuid.UUID

    model_config = ConfigDict(from_attributes=True)


# ── Geocoding Schemas ────────────────────────────────────────────────
class GeocodeSearchResult(BaseModel):
    name: str
    area_label: str
    coarse_lat: float = Field(..., description="Coarse latitude (~1 km grid)")
    coarse_lng: float = Field(..., description="Coarse longitude (~1 km grid)")
    country: str | None = None
    admin1: str | None = None


# ── Swap Profile Schemas ─────────────────────────────────────────────
class UserSwapProfileUpdate(BaseModel):
    bio: str | None = Field(default=None, max_length=2000)
    coarse_lat: float | None = None
    coarse_lng: float | None = None
    area_label: str | None = Field(default=None, max_length=150)
    radius_km: int = Field(default=10, ge=0, le=100)
    modes: list[str] = Field(default_factory=lambda: ["video", "in_person"])
    languages: list[str] = Field(default_factory=lambda: ["English"])
    is_invisible: bool = False
    accepts_newcomers: bool = True
    is_18_confirmed: bool = False

    teach_skills: list[UserSkillItem] = Field(default_factory=list)
    learn_skills: list[UserSkillItem] = Field(default_factory=list)
    availability_windows: list[AvailabilityWindowItem] = Field(default_factory=list)
    blackout_dates: list[AvailabilityBlackoutItem] = Field(default_factory=list)

    @field_validator("coarse_lat")
    @classmethod
    def round_lat(cls, v: float | None) -> float | None:
        return round(v, 2) if v is not None else None

    @field_validator("coarse_lng")
    @classmethod
    def round_lng(cls, v: float | None) -> float | None:
        return round(v, 2) if v is not None else None


class UserSwapProfilePrivateResponse(BaseModel):
    """Full profile returned ONLY to the owner."""

    user_id: uuid.UUID
    bio: str | None
    coarse_lat: float | None
    coarse_lng: float | None
    area_label: str | None
    radius_km: int
    modes: list[str]
    languages: list[str]
    is_invisible: bool
    accepts_newcomers: bool
    is_18_confirmed: bool

    teach_skills: list[UserSkillResponse]
    learn_skills: list[UserSkillResponse]
    availability_windows: list[AvailabilityWindowResponse]
    blackout_dates: list[AvailabilityBlackoutResponse]

    trust_score: int
    avg_rating: float
    completed_swaps: int
    badges: list[str]
    reciprocity_balance_minutes: int

    model_config = ConfigDict(from_attributes=True)


class PublicUserMinimal(BaseModel):
    id: uuid.UUID
    username: str
    display_name: str
    avatar_url: str | None
    usn: str | None = None

    model_config = ConfigDict(from_attributes=True)


class UserSwapProfilePublicResponse(BaseModel):
    """
    Publicly visible swap profile.
    CRITICAL PRIVACY: Coarse coordinates and geohash are NEVER returned here.
    Distance is strictly serialized as a pre-computed distance bucket.
    """

    user: PublicUserMinimal
    bio: str | None
    area_label: str | None
    distance_bucket: str = Field(
        ...,
        description=(
            "Distance bucket: 'under 1 km', '1–3 km', '3–5 km', "
            "'5–10 km', '10–25 km', or 'remote'"
        ),
    )
    modes: list[str]
    languages: list[str]
    accepts_newcomers: bool

    teach_skills: list[UserSkillResponse]
    learn_skills: list[UserSkillResponse]

    trust_score: int
    avg_rating: float
    completed_swaps: int
    badges: list[str]

    model_config = ConfigDict(from_attributes=True)


# ── Swap Listing Schemas ─────────────────────────────────────────────
class SwapListingCreate(BaseModel):
    title: str = Field(..., min_length=3, max_length=150)
    skill_offered_id: uuid.UUID
    skill_wanted_id: uuid.UUID | None = None
    description: str = Field(..., min_length=10, max_length=2000)
    modes: list[str] = Field(default_factory=lambda: ["video"])
    area_label: str | None = Field(default=None, max_length=150)
    tags: list[str] = Field(default_factory=list)
    expires_at: datetime | None = None


class SwapListingUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=3, max_length=150)
    skill_offered_id: uuid.UUID | None = None
    skill_wanted_id: uuid.UUID | None = None
    description: str | None = Field(default=None, min_length=10, max_length=2000)
    modes: list[str] | None = None
    area_label: str | None = Field(default=None, max_length=150)
    tags: list[str] | None = None
    status: Literal["draft", "active", "paused", "closed"] | None = None
    expires_at: datetime | None = None


class SwapListingResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    user: PublicUserMinimal
    title: str
    skill_offered: SkillResponse
    skill_wanted: SkillResponse | None = None
    description: str
    modes: list[str]
    area_label: str | None
    status: str
    tags: list[str]
    distance_bucket: str | None = Field(
        default=None,
        description="Distance bucket relative to current viewer ('1–3 km', 'remote', etc.)",
    )
    expires_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SwapListingListResponse(BaseModel):
    items: list[SwapListingResponse]
    total: int
    next_cursor: str | None = None


class SwapListingShareResponse(BaseModel):
    listing_id: uuid.UUID
    post_id: uuid.UUID
    message: str


# ── AI Listing Helper Schemas ────────────────────────────────────────
class ListingAIDraftRequest(BaseModel):
    skill_offered_name: str = Field(..., min_length=2, max_length=100)
    skill_wanted_name: str | None = Field(default=None, max_length=100)
    notes: str | None = Field(default=None, max_length=500)


class ListingAIDraftResponse(BaseModel):
    title: str
    description: str
    suggested_tags: list[str]


# ── Match Recommendation Schemas ─────────────────────────────────────
class SwapMatchResponse(BaseModel):
    listing: SwapListingResponse
    match_score: float = Field(..., ge=0.0, le=1.0)
    explanation: str
    score_breakdown: dict[str, float]


# ── Swap Request & Proposal Schemas (Stage 3) ────────────────────────
class ProposedSlotItem(BaseModel):
    start_time_utc: datetime
    end_time_utc: datetime

    @field_validator("end_time_utc")
    @classmethod
    def validate_slot_times(cls, v: datetime, info: Any) -> datetime:
        start = info.data.get("start_time_utc")
        if start:
            diff = (v - start).total_seconds()
            if diff <= 0:
                raise ValueError("end_time_utc must be after start_time_utc")
            if diff != 1800:
                raise ValueError("Each proposed slot half must be exactly 30 minutes (1800s)")
        return v


class SwapRequestCreate(BaseModel):
    listing_id: uuid.UUID | None = None
    recipient_id: uuid.UUID
    offered_skill_id: uuid.UUID
    wanted_skill_id: uuid.UUID
    mode: Literal["video", "in_person"] = "video"
    message: str = Field(..., min_length=5, max_length=500)
    proposed_slots: list[ProposedSlotItem] = Field(..., min_length=1, max_length=3)
    public_place_name: str | None = Field(default=None, max_length=150)
    public_place_address: str | None = Field(default=None, max_length=255)


class SwapRequestCounter(BaseModel):
    message: str = Field(..., min_length=5, max_length=500)
    proposed_slots: list[ProposedSlotItem] = Field(..., min_length=1, max_length=3)
    mode: Literal["video", "in_person"] | None = None
    public_place_name: str | None = Field(default=None, max_length=150)
    public_place_address: str | None = Field(default=None, max_length=255)


class SwapRequestAccept(BaseModel):
    selected_slot_index: int = Field(default=0, ge=0, le=2)
    public_place_name: str | None = Field(default=None, max_length=150)
    public_place_address: str | None = Field(default=None, max_length=255)


class SwapRequestResponse(BaseModel):
    id: uuid.UUID
    listing_id: uuid.UUID | None
    requester: PublicUserMinimal
    recipient: PublicUserMinimal
    offered_skill: SkillResponse
    wanted_skill: SkillResponse
    mode: str
    message: str
    proposed_slots: list[dict[str, Any]]
    status: str
    counter_note: str | None = None
    expires_at: datetime
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SwapRequestListResponse(BaseModel):
    incoming: list[SwapRequestResponse]
    outgoing: list[SwapRequestResponse]


# ── Session & Halves Schemas (Stage 3) ───────────────────────────────
class SwapSessionHalfResponse(BaseModel):
    id: uuid.UUID
    session_id: uuid.UUID
    half_number: int
    mentor: PublicUserMinimal
    learner: PublicUserMinimal
    skill: SkillResponse
    start_time_utc: datetime
    end_time_utc: datetime
    status: str
    ics_uid: str

    model_config = ConfigDict(from_attributes=True)


class SwapSessionResponse(BaseModel):
    id: uuid.UUID
    request_id: uuid.UUID
    user_a: PublicUserMinimal
    user_b: PublicUserMinimal
    status: str
    mode: str
    public_place_name: str | None = None
    public_place_address: str | None = None
    jitsi_room_token: str | None = None
    jitsi_room_url: str | None = None
    user_a_confirmed: bool = False
    user_b_confirmed: bool = False
    dispute_reason: str | None = None
    halves: list[SwapSessionHalfResponse] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ── Logistics Chat Schemas (Stage 3) ─────────────────────────────────
class SwapMessageCreate(BaseModel):
    content: str = Field(..., min_length=1, max_length=1000)


class SwapMessageResponse(BaseModel):
    id: uuid.UUID
    session_id: uuid.UUID
    sender: PublicUserMinimal
    content: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ── Double-Blind Review Schemas (Stage 3) ────────────────────────────
class SwapReviewCreate(BaseModel):
    rating: int = Field(..., ge=1, le=5)
    tags: list[str] = Field(default_factory=list)
    public_comment: str | None = Field(default=None, max_length=1000)
    private_feedback: str | None = Field(default=None, max_length=1000)


class SwapReviewResponse(BaseModel):
    id: uuid.UUID
    session_id: uuid.UUID
    reviewer: PublicUserMinimal
    reviewee: PublicUserMinimal
    rating: int | None = None
    tags: list[str] = Field(default_factory=list)
    public_comment: str | None = None
    is_revealed: bool
    revealed_at: datetime | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ── Dispute & iCalendar Schemas (Stage 3) ────────────────────────────
class SwapDisputeCreate(BaseModel):
    reason: str = Field(..., min_length=10, max_length=1000)


class ICSExportResponse(BaseModel):
    filename: str
    content: str


