from datetime import date, datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class DocumentKind(StrEnum):
    ENGAGEMENT_LETTER = "engagement_letter"
    CONSENT_ORDER = "consent_order"
    SETTLEMENT_AGREEMENT = "settlement_agreement"


class ImagePurpose(StrEnum):
    SIGNED_DELIVERY = "signed_delivery"
    DEADLINE_FOLLOW_UP = "deadline_follow_up"


class MatterImageRequest(BaseModel):
    matter_reference: str = Field(min_length=3, max_length=80)
    document_kind: DocumentKind
    signed_delivery_confirmed: bool
    deadline: date
    idempotency_key: str = Field(min_length=8, max_length=120)


class MatterImageResult(BaseModel):
    matter_reference: str
    purpose: ImagePurpose
    follow_up_on: date | None
    stored_path: str
    created_at: datetime
