import secrets
from datetime import datetime

from lnbits.db import Database, Filters, Page
from lnbits.helpers import urlsafe_short_hash

from .helpers import build_bunker_url, derive_remote_signer_pubkey
from .models import (
    BunkersData,
    BunkersDataFilters,
    CreateBunkersData,
    CreateSigningRequest,
    CreateUrlData,
    SigningRequest,
    SigningRequestFilters,
    UpdateSigningRequest,
    UrlData,
    UrlDataFilters,
)

db = Database("ext_nostr_bunker")


########################### Bunkers Data ############################
async def create_bunkers_data(user_id: str, data: CreateBunkersData) -> BunkersData:
    bunkers_data = BunkersData(**data.dict(), id=urlsafe_short_hash(), user_id=user_id)
    await db.insert("nostr_bunker.bunkers_data", bunkers_data)
    return bunkers_data


async def get_bunkers_data(
    user_id: str,
    bunkers_data_id: str,
) -> BunkersData | None:
    return await db.fetchone(
        """
            SELECT * FROM nostr_bunker.bunkers_data
            WHERE id = :id AND user_id = :user_id
        """,
        {"id": bunkers_data_id, "user_id": user_id},
        BunkersData,
    )


async def get_bunkers_data_by_id(
    bunkers_data_id: str,
) -> BunkersData | None:
    return await db.fetchone(
        """
            SELECT * FROM nostr_bunker.bunkers_data
            WHERE id = :id
        """,
        {"id": bunkers_data_id},
        BunkersData,
    )


async def get_bunkers_data_ids_by_user(
    user_id: str,
) -> list[str]:
    rows: list[dict] = await db.fetchall(
        """
            SELECT DISTINCT id FROM nostr_bunker.bunkers_data
            WHERE user_id = :user_id
        """,
        {"user_id": user_id},
    )

    return [row["id"] for row in rows]


async def get_bunkers_data_paginated(
    user_id: str | None = None,
    filters: Filters[BunkersDataFilters] | None = None,
) -> Page[BunkersData]:
    where = []
    values = {}
    if user_id:
        where.append("user_id = :user_id")
        values["user_id"] = user_id

    return await db.fetch_page(
        "SELECT * FROM nostr_bunker.bunkers_data",
        where=where,
        values=values,
        filters=filters,
        model=BunkersData,
    )


async def get_all_bunkers_data() -> list[BunkersData]:
    return await db.fetchall(
        """
            SELECT * FROM nostr_bunker.bunkers_data
        """,
        model=BunkersData,
    )


async def update_bunkers_data(data: BunkersData) -> BunkersData:
    await db.update("nostr_bunker.bunkers_data", data)
    return data


async def delete_bunkers_data(user_id: str, bunkers_data_id: str) -> None:
    await db.execute(
        """
            DELETE FROM nostr_bunker.bunkers_data
            WHERE id = :id AND user_id = :user_id
        """,
        {"id": bunkers_data_id, "user_id": user_id},
    )


################################# Url Data ###########################


async def create_url_data(bunkers_data_id: str, data: CreateUrlData) -> UrlData:
    payload = data.dict()
    payload["secret"] = payload.get("secret") or secrets.token_urlsafe(12)
    url_data = UrlData(
        **payload,
        id=urlsafe_short_hash(),
        bunkers_data_id=bunkers_data_id,
    )
    await db.insert("nostr_bunker.url_data", url_data)
    return url_data


async def get_url_data(
    bunkers_data_id: str,
    url_data_id: str,
) -> UrlData | None:
    return await db.fetchone(
        """
            SELECT * FROM nostr_bunker.url_data
            WHERE id = :id AND bunkers_data_id = :bunkers_data_id
        """,
        {"id": url_data_id, "bunkers_data_id": bunkers_data_id},
        UrlData,
    )


async def get_url_data_by_id(
    url_data_id: str,
) -> UrlData | None:
    return await db.fetchone(
        """
            SELECT * FROM nostr_bunker.url_data
            WHERE id = :id
        """,
        {"id": url_data_id},
        UrlData,
    )


async def get_url_data_by_bunkers_data_id(
    bunkers_data_id: str,
) -> list[UrlData]:
    return await db.fetchall(
        """
            SELECT * FROM nostr_bunker.url_data
            WHERE bunkers_data_id = :bunkers_data_id
        """,
        {"bunkers_data_id": bunkers_data_id},
        UrlData,
    )


async def get_url_data_by_secret(
    bunkers_data_id: str,
    secret: str,
) -> UrlData | None:
    return await db.fetchone(
        """
            SELECT * FROM nostr_bunker.url_data
            WHERE bunkers_data_id = :bunkers_data_id
              AND secret = :secret
        """,
        {"bunkers_data_id": bunkers_data_id, "secret": secret},
        UrlData,
    )


async def get_url_data_by_client_pubkey(
    bunkers_data_id: str,
    client_pubkey: str,
) -> UrlData | None:
    return await db.fetchone(
        """
            SELECT * FROM nostr_bunker.url_data
            WHERE bunkers_data_id = :bunkers_data_id
              AND client_pubkey = :client_pubkey
        """,
        {"bunkers_data_id": bunkers_data_id, "client_pubkey": client_pubkey},
        UrlData,
    )


async def get_url_data_paginated(
    bunkers_data_ids: list[str] | None = None,
    filters: Filters[UrlDataFilters] | None = None,
) -> Page[UrlData]:

    if not bunkers_data_ids:
        return Page(data=[], total=0)

    where = []
    values = {}
    id_clause = []
    for i, item_id in enumerate(bunkers_data_ids):
        # bunkers_data_ids are not user input, but DB entries, so this is safe
        bunkers_data_id = f"bunkers_data_id__{i}"
        id_clause.append(f"bunkers_data_id = :{bunkers_data_id}")
        values[bunkers_data_id] = item_id
    or_clause = " OR ".join(id_clause)
    where.append(f"({or_clause})")

    return await db.fetch_page(
        "SELECT * FROM nostr_bunker.url_data",
        where=where,
        values=values,
        filters=filters,
        model=UrlData,
    )


async def get_url_data_ids_by_bunkers_data_ids(
    bunkers_data_ids: list[str] | None = None,
) -> list[str]:
    if not bunkers_data_ids:
        return []

    values = {}
    id_clause = []
    for i, item_id in enumerate(bunkers_data_ids):
        bunkers_data_id = f"bunkers_data_id__{i}"
        id_clause.append(f"bunkers_data_id = :{bunkers_data_id}")
        values[bunkers_data_id] = item_id

    rows: list[dict] = await db.fetchall(
        f"""
            SELECT DISTINCT id FROM nostr_bunker.url_data
            WHERE {' OR '.join(id_clause)}
        """,
        values,
    )

    return [row["id"] for row in rows]


async def update_url_data(data: UrlData) -> UrlData:
    data.secret = data.secret or secrets.token_urlsafe(12)
    await db.update("nostr_bunker.url_data", data)
    return data


async def delete_url_data(bunkers_data_id: str, url_data_id: str) -> None:
    await delete_signing_requests_by_url_data_id(url_data_id)
    await db.execute(
        """
            DELETE FROM nostr_bunker.url_data
            WHERE id = :id AND bunkers_data_id = :bunkers_data_id
        """,
        {"id": url_data_id, "bunkers_data_id": bunkers_data_id},
    )


async def delete_url_data_by_bunkers_data_id(bunkers_data_id: str) -> None:
    rows: list[dict] = await db.fetchall(
        """
            SELECT id FROM nostr_bunker.url_data
            WHERE bunkers_data_id = :bunkers_data_id
        """,
        {"bunkers_data_id": bunkers_data_id},
    )
    for row in rows:
        await delete_signing_requests_by_url_data_id(row["id"])
    await db.execute(
        """
            DELETE FROM nostr_bunker.url_data
            WHERE bunkers_data_id = :bunkers_data_id
        """,
        {"bunkers_data_id": bunkers_data_id},
    )


############################ Signing Requests ############################


async def create_signing_request(url_data_id: str, data: CreateSigningRequest) -> SigningRequest:
    signing_request = SigningRequest(
        **data.dict(),
        id=urlsafe_short_hash(),
        url_data_id=url_data_id,
    )
    await db.insert("nostr_bunker.signing_requests", signing_request)
    return signing_request


async def get_signing_request_by_id(
    signing_request_id: str,
) -> SigningRequest | None:
    return await db.fetchone(
        """
            SELECT * FROM nostr_bunker.signing_requests
            WHERE id = :id
        """,
        {"id": signing_request_id},
        SigningRequest,
    )


async def get_signing_request_by_request_id(
    url_data_id: str,
    request_id: str,
) -> SigningRequest | None:
    return await db.fetchone(
        """
            SELECT * FROM nostr_bunker.signing_requests
            WHERE url_data_id = :url_data_id
              AND request_id = :request_id
        """,
        {"url_data_id": url_data_id, "request_id": request_id},
        SigningRequest,
    )


async def get_signing_request(
    url_data_id: str,
    signing_request_id: str,
) -> SigningRequest | None:
    return await db.fetchone(
        """
            SELECT * FROM nostr_bunker.signing_requests
            WHERE id = :id AND url_data_id = :url_data_id
        """,
        {"id": signing_request_id, "url_data_id": url_data_id},
        SigningRequest,
    )


async def count_signing_requests_since(
    url_data_id: str,
    since: datetime,
) -> int:
    row = await db.fetchone(
        """
            SELECT COUNT(*) AS count
            FROM nostr_bunker.signing_requests
            WHERE url_data_id = :url_data_id
              AND created_at >= :since
        """,
        {"url_data_id": url_data_id, "since": since},
    )
    return int(row["count"]) if row else 0


async def get_signing_requests_since(
    url_data_id: str,
    since: datetime,
) -> list[SigningRequest]:
    return await db.fetchall(
        """
            SELECT * FROM nostr_bunker.signing_requests
            WHERE url_data_id = :url_data_id
              AND created_at >= :since
        """,
        {"url_data_id": url_data_id, "since": since},
        SigningRequest,
    )


async def get_signing_requests_paginated(
    url_data_ids: list[str] | None = None,
    filters: Filters[SigningRequestFilters] | None = None,
) -> Page[SigningRequest]:

    if not url_data_ids:
        return Page(data=[], total=0)

    where = []
    values = {}
    id_clause = []
    for i, item_id in enumerate(url_data_ids):
        url_data_id = f"url_data_id__{i}"
        id_clause.append(f"url_data_id = :{url_data_id}")
        values[url_data_id] = item_id
    where.append(f"({' OR '.join(id_clause)})")

    return await db.fetch_page(
        "SELECT * FROM nostr_bunker.signing_requests",
        where=where,
        values=values,
        filters=filters,
        model=SigningRequest,
    )


async def update_signing_request(
    signing_request: SigningRequest,
    data: UpdateSigningRequest,
) -> SigningRequest:
    signing_request.status = data.status
    signing_request.signed_event = data.signed_event
    signing_request.error = data.error
    await db.update("nostr_bunker.signing_requests", signing_request)
    return signing_request


async def delete_signing_request(url_data_id: str, signing_request_id: str) -> None:
    await db.execute(
        """
            DELETE FROM nostr_bunker.signing_requests
            WHERE id = :id AND url_data_id = :url_data_id
        """,
        {"id": signing_request_id, "url_data_id": url_data_id},
    )


async def delete_signing_requests_by_url_data_id(url_data_id: str) -> None:
    await db.execute(
        """
            DELETE FROM nostr_bunker.signing_requests
            WHERE url_data_id = :url_data_id
        """,
        {"url_data_id": url_data_id},
    )


def enrich_url_data(url_data: UrlData, bunkers_data: BunkersData) -> UrlData:
    remote_signer_pubkey = derive_remote_signer_pubkey(bunkers_data.nsec)
    url_data.remote_signer_pubkey = remote_signer_pubkey
    url_data.bunker_url = build_bunker_url(
        remote_signer_pubkey=remote_signer_pubkey,
        relays=url_data.relays,
        secret=url_data.secret,
    )
    return url_data
