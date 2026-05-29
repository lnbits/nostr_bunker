from datetime import datetime, timezone

from lnbits.db import FilterModel
from lnbits.utils.nostr import normalize_private_key
from pydantic import BaseModel, Field, validator

from .helpers import validate_relay_urls


########################### Bunkers Data ############################
class CreateBunkersData(BaseModel):
    name: str | None
    nsec: str | None

    @validator("nsec")
    def validate_nsec(cls, value: str | None) -> str | None:
        if value is None or not value.strip():
            raise ValueError("nsec is required.")
        normalize_private_key(value.strip())
        return value.strip()


class BunkersData(BaseModel):
    id: str
    user_id: str
    name: str | None
    nsec: str | None

    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class BunkersDataFilters(FilterModel):
    __search_fields__ = [
        "name",
        "nsec",
    ]

    __sort_fields__ = [
        "name",
        "nsec",
        "created_at",
        "updated_at",
    ]

    created_at: datetime | None
    updated_at: datetime | None


################################# Url Data ###########################


class CreateUrlData(BaseModel):
    name: str | None
    relays: list[str] = Field(default_factory=list)
    permissions: list[str] = Field(default_factory=list)
    auto_sign: bool = False
    confirm_sign: bool = True
    expires_at: datetime | None = None
    can_read: bool = True
    can_write: bool = False
    post_rate_limit_per_day: int | None = None
    secret: str | None = None

    @validator("post_rate_limit_per_day")
    def validate_rate_limit(cls, value: int | None) -> int | None:
        if value is not None and value < 0:
            raise ValueError("post_rate_limit_per_day must be 0 or greater.")
        return value

    @validator("relays")
    def validate_relays(cls, value: list[str]) -> list[str]:
        return validate_relay_urls(value)

    @validator("secret")
    def normalize_secret(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        return value or None


class UrlData(BaseModel):
    id: str
    bunkers_data_id: str
    name: str | None
    relays: list[str] = Field(default_factory=list)
    permissions: list[str] = Field(default_factory=list)
    auto_sign: bool = False
    confirm_sign: bool = True
    expires_at: datetime | None = None
    can_read: bool = True
    can_write: bool = False
    post_rate_limit_per_day: int | None = None
    secret: str | None = None
    client_pubkey: str | None = None
    remote_signer_pubkey: str | None = Field(default=None, no_database=True)
    bunker_url: str | None = Field(default=None, no_database=True)

    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class UrlDataFilters(FilterModel):
    __search_fields__ = [
        "name",
        "relays",
        "permissions",
        "secret",
    ]

    __sort_fields__ = [
        "name",
        "relays",
        "auto_sign",
        "confirm_sign",
        "expires_at",
        "can_read",
        "can_write",
        "post_rate_limit_per_day",
        "created_at",
        "updated_at",
    ]

    created_at: datetime | None
    updated_at: datetime | None


############################ Signing Requests ############################


class CreateSigningRequest(BaseModel):
    request_id: str
    client_pubkey: str
    event: dict
    expires_at: datetime | None = None


class UpdateSigningRequest(BaseModel):
    status: str
    signed_event: dict | None = None
    error: str | None = None

    @validator("status")
    def validate_status(cls, value: str) -> str:
        normalized = value.strip().lower()
        allowed = {"pending", "approved", "signed", "rejected", "error"}
        if normalized not in allowed:
            raise ValueError(f"status must be one of: {', '.join(sorted(allowed))}.")
        return normalized


class SigningRequest(BaseModel):
    id: str
    url_data_id: str
    request_id: str
    client_pubkey: str
    event: dict
    status: str = "pending"
    signed_event: dict | None = None
    error: str | None = None
    expires_at: datetime | None = None

    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class SigningRequestFilters(FilterModel):
    __search_fields__ = [
        "request_id",
        "client_pubkey",
        "status",
    ]

    __sort_fields__ = [
        "request_id",
        "client_pubkey",
        "status",
        "expires_at",
        "created_at",
        "updated_at",
    ]

    created_at: datetime | None
    updated_at: datetime | None
