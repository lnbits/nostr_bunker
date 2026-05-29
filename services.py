import asyncio
import json
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

from coincurve import PrivateKey
from lnbits.core.models import Payment
from lnbits.utils.nostr import json_dumps, normalize_private_key, sign_event
from loguru import logger
from nostr_sdk import (
    Event,
    Nip44Version,
    PublicKey,
    SecretKey,
    nip04_decrypt,
    nip04_encrypt,
    nip44_decrypt,
    nip44_encrypt,
)

try:
    from lnbits.extensions.nostrclient.router import NostrRouter, nostr_client
except ModuleNotFoundError:
    try:
        from nostrclient.router import NostrRouter, nostr_client  # type: ignore[import]
    except ModuleNotFoundError:

        class _FallbackRelayManager:
            def add_relay(self, *_args, **_kwargs):
                return None

            def add_subscription(self, *_args, **_kwargs):
                return None

            def close_subscription(self, *_args, **_kwargs):
                return None

            def publish_message(self, *_args, **_kwargs):
                return None

        class _FallbackNostrClient:
            relay_manager = _FallbackRelayManager()

        class NostrRouter:
            received_subscription_events: dict[str, list] = {}

        nostr_client = _FallbackNostrClient()

from .crud import (
    create_signing_request,
    get_all_bunkers_data,
    get_bunkers_data_by_id,
    get_signing_request_by_id,
    get_signing_request_by_request_id,
    get_signing_requests_since,
    get_url_data_by_bunkers_data_id,
    get_url_data_by_client_pubkey,
    get_url_data_by_id,
    get_url_data_by_secret,
    update_signing_request,
    update_url_data,
)
from .helpers import derive_remote_signer_pubkey
from .models import BunkersData, CreateSigningRequest, SigningRequest, UpdateSigningRequest, UrlData

NIP46_KIND = 24133
SUBSCRIPTION_ID = "nostr_bunker_nip46"
REFRESH_INTERVAL_SECONDS = 30


@dataclass
class RuntimeState:
    subscribed_pubkeys: set[str] = field(default_factory=set)
    ensured_relays: set[str] = field(default_factory=set)
    next_refresh_at: float = 0


runtime_state = RuntimeState()


def mark_runtime_state_dirty() -> None:
    runtime_state.next_refresh_at = 0


async def payment_received_for_url_data(payment: Payment) -> bool:
    logger.info("Payment receive logic generation is disabled.")
    return True


async def run_nip46_runtime() -> None:
    while True:
        try:
            await _refresh_runtime_state()
            await _process_subscription_events()
        except Exception as exc:
            logger.warning(f"[nostr_bunker] NIP-46 runtime error: {exc}")
            await asyncio.sleep(1)
        await asyncio.sleep(0.2)


async def complete_signing_request_action(
    signing_request_id: str,
    requested_status: str,
    error_message: str | None = None,
) -> SigningRequest:
    signing_request = await get_signing_request_by_id(signing_request_id)
    if not signing_request:
        raise ValueError("Signing request not found.")

    url_data = await get_url_data_by_id(signing_request.url_data_id)
    if not url_data:
        raise ValueError("Url data not found.")

    bunkers_data = await get_bunkers_data_by_id(url_data.bunkers_data_id)
    if not bunkers_data:
        raise ValueError("Bunker not found.")

    status = requested_status.lower()
    if status in {"approved", "signed"}:
        signed_event = _sign_event_payload(bunkers_data, signing_request.event)
        await _publish_response(
            bunkers_data=bunkers_data,
            url_data=url_data,
            client_pubkey=signing_request.client_pubkey,
            request_id=signing_request.request_id,
            result=json.dumps(signed_event, separators=(",", ":")),
        )
        return await update_signing_request(
            signing_request,
            UpdateSigningRequest(status="signed", signed_event=signed_event),
        )

    rejection_message = error_message or signing_request.error or "Signing request rejected."
    await _publish_response(
        bunkers_data=bunkers_data,
        url_data=url_data,
        client_pubkey=signing_request.client_pubkey,
        request_id=signing_request.request_id,
        error=rejection_message,
    )
    return await update_signing_request(
        signing_request,
        UpdateSigningRequest(status="rejected", error=rejection_message),
    )


async def _refresh_runtime_state() -> None:
    now = time.time()
    if now < runtime_state.next_refresh_at:
        return

    bunkers = await get_all_bunkers_data()
    signer_pubkeys = {pubkey for pubkey in (derive_remote_signer_pubkey(bunker.nsec) for bunker in bunkers) if pubkey}

    for bunker in bunkers:
        url_rows = await get_url_data_by_bunkers_data_id(bunker.id)
        for url_data in url_rows:
            for relay in url_data.relays:
                if relay in runtime_state.ensured_relays:
                    continue
                try:
                    nostr_client.relay_manager.add_relay(relay)
                    runtime_state.ensured_relays.add(relay)
                except Exception as exc:
                    logger.warning(f"[nostr_bunker] Failed to add relay '{relay}': {exc}")

    if signer_pubkeys != runtime_state.subscribed_pubkeys:
        nostr_client.relay_manager.close_subscription(SUBSCRIPTION_ID)
        runtime_state.subscribed_pubkeys = signer_pubkeys
        if signer_pubkeys:
            nostr_client.relay_manager.add_subscription(
                SUBSCRIPTION_ID,
                [{"kinds": [NIP46_KIND], "#p": sorted(signer_pubkeys)}],
            )

    runtime_state.next_refresh_at = now + REFRESH_INTERVAL_SECONDS


async def _process_subscription_events() -> None:
    events = NostrRouter.received_subscription_events.get(SUBSCRIPTION_ID)
    if not events:
        return

    while events:
        event_message = events.pop(0)
        try:
            event_dict = json.loads(event_message.event)
            await _handle_request_event(event_dict)
        except Exception as exc:
            logger.warning(f"[nostr_bunker] Failed to process NIP-46 event: {exc}")


async def _handle_request_event(event_dict: dict) -> None:
    if event_dict.get("kind") != NIP46_KIND:
        return

    event_json = json.dumps(event_dict, separators=(",", ":"))
    try:
        if not Event.from_json(event_json).verify():
            logger.warning("[nostr_bunker] Ignoring NIP-46 event with invalid signature.")
            return
    except Exception as exc:
        logger.warning(f"[nostr_bunker] Failed to verify NIP-46 event: {exc}")
        return

    remote_signer_pubkey = _extract_first_p_tag(event_dict.get("tags", []))
    client_pubkey = event_dict.get("pubkey")
    if not remote_signer_pubkey or not client_pubkey:
        return

    bunker = await _get_bunker_by_remote_signer_pubkey(remote_signer_pubkey)
    if not bunker:
        return

    payload = _decrypt_request_payload(bunker, client_pubkey, event_dict["content"])
    if not payload:
        return

    request_id = payload.get("id")
    method = payload.get("method")
    params = payload.get("params") or []
    if not request_id or not method or not isinstance(params, list):
        return

    try:
        url_data = await _resolve_url_data(
            bunker=bunker,
            client_pubkey=client_pubkey,
            method=method,
            params=params,
        )
    except PermissionError as exc:
        await _publish_response(
            bunkers_data=bunker,
            url_data=None,
            client_pubkey=client_pubkey,
            request_id=request_id,
            error=str(exc),
        )
        return

    if not url_data:
        await _publish_response(
            bunkers_data=bunker,
            url_data=None,
            client_pubkey=client_pubkey,
            request_id=request_id,
            error="Unknown or expired bunker connection.",
        )
        return

    try:
        result = await _dispatch_request(
            bunker=bunker,
            url_data=url_data,
            client_pubkey=client_pubkey,
            request_id=request_id,
            method=method,
            params=params,
        )
    except PermissionError as exc:
        await _publish_response(
            bunkers_data=bunker,
            url_data=url_data,
            client_pubkey=client_pubkey,
            request_id=request_id,
            error=str(exc),
        )
        return
    except Exception as exc:
        await _publish_response(
            bunkers_data=bunker,
            url_data=url_data,
            client_pubkey=client_pubkey,
            request_id=request_id,
            error=str(exc),
        )
        return

    if result is None:
        return

    await _publish_response(
        bunkers_data=bunker,
        url_data=url_data,
        client_pubkey=client_pubkey,
        request_id=request_id,
        result=result,
    )


def _decrypt_request_payload(
    bunker: BunkersData,
    client_pubkey: str,
    encrypted_payload: str,
) -> dict | None:
    secret_key = _get_secret_key(bunker)
    author_pubkey = PublicKey.parse(client_pubkey)
    try:
        decrypted = nip44_decrypt(secret_key, author_pubkey, encrypted_payload)
    except Exception:
        try:
            decrypted = nip04_decrypt(secret_key, author_pubkey, encrypted_payload)
        except Exception as exc:
            logger.warning(f"[nostr_bunker] Could not decrypt NIP-46 payload: {exc}")
            return None

    return json.loads(decrypted)


async def _resolve_url_data(
    bunker: BunkersData,
    client_pubkey: str,
    method: str,
    params: list,
) -> UrlData | None:
    if method == "connect":
        secret = params[1] if len(params) > 1 else None
        if not secret:
            raise PermissionError("Missing bunker secret.")
        url_data = await get_url_data_by_secret(bunker.id, secret)
        if not url_data:
            return None
        _assert_url_is_active(url_data)
        if url_data.client_pubkey != client_pubkey:
            url_data.client_pubkey = client_pubkey
            await update_url_data(url_data)
        requested_permissions = params[2] if len(params) > 2 else None
        if requested_permissions and not _requested_permissions_allowed(url_data, requested_permissions):
            raise PermissionError("Requested permissions exceed this bunker URL policy.")
        return url_data

    url_data = await get_url_data_by_client_pubkey(bunker.id, client_pubkey)
    if not url_data:
        return None
    _assert_url_is_active(url_data)
    return url_data


async def _dispatch_request(
    bunker: BunkersData,
    url_data: UrlData,
    client_pubkey: str,
    request_id: str,
    method: str,
    params: list,
) -> str | None:
    if method == "connect":
        return url_data.secret or "ack"

    if method == "ping":
        return "pong"

    if method == "switch_relays":
        return json.dumps(url_data.relays, separators=(",", ":"))

    if method == "get_public_key":
        _assert_method_allowed(url_data, method)
        return derive_remote_signer_pubkey(bunker.nsec) or ""

    if method == "nip04_encrypt":
        _assert_method_allowed(url_data, method)
        third_party_pubkey = PublicKey.parse(str(params[0]))
        return nip04_encrypt(_get_secret_key(bunker), third_party_pubkey, str(params[1]))

    if method == "nip04_decrypt":
        _assert_method_allowed(url_data, method)
        third_party_pubkey = PublicKey.parse(str(params[0]))
        return nip04_decrypt(_get_secret_key(bunker), third_party_pubkey, str(params[1]))

    if method == "nip44_encrypt":
        _assert_method_allowed(url_data, method)
        third_party_pubkey = PublicKey.parse(str(params[0]))
        return nip44_encrypt(
            _get_secret_key(bunker),
            third_party_pubkey,
            str(params[1]),
            Nip44Version.V2,
        )

    if method == "nip44_decrypt":
        _assert_method_allowed(url_data, method)
        third_party_pubkey = PublicKey.parse(str(params[0]))
        return nip44_decrypt(_get_secret_key(bunker), third_party_pubkey, str(params[1]))

    if method == "sign_event":
        unsigned_event = _parse_unsigned_event_param(params)
        kind = int(unsigned_event.get("kind", 0))
        _assert_method_allowed(url_data, method, kind=kind)
        await _assert_post_rate_limit(url_data, kind)

        existing_request = await get_signing_request_by_request_id(url_data.id, request_id)
        if existing_request:
            if existing_request.status == "signed" and existing_request.signed_event:
                return json.dumps(existing_request.signed_event, separators=(",", ":"))
            if existing_request.status == "rejected":
                raise PermissionError(existing_request.error or "Signing request rejected.")
            return None

        signing_request = await create_signing_request(
            url_data.id,
            CreateSigningRequest(
                request_id=request_id,
                client_pubkey=client_pubkey,
                event=unsigned_event,
            ),
        )

        if url_data.auto_sign:
            signed_event = _sign_event_payload(bunker, unsigned_event)
            await update_signing_request(
                signing_request,
                UpdateSigningRequest(status="signed", signed_event=signed_event),
            )
            return json.dumps(signed_event, separators=(",", ":"))

        if url_data.confirm_sign:
            return None

        await update_signing_request(
            signing_request,
            UpdateSigningRequest(
                status="rejected",
                error="This bunker URL is not allowed to sign events.",
            ),
        )
        raise PermissionError("This bunker URL is not allowed to sign events.")

    raise PermissionError(f"Unsupported NIP-46 method: {method}")


async def _publish_response(
    bunkers_data: BunkersData,
    url_data: UrlData | None,
    client_pubkey: str,
    request_id: str,
    result: str | None = None,
    error: str | None = None,
) -> None:
    signer_pubkey = derive_remote_signer_pubkey(bunkers_data.nsec)
    if not signer_pubkey:
        raise ValueError("Bunker has no signer key configured.")

    payload = {"id": request_id, "result": result}
    if error is not None:
        payload["error"] = error

    encrypted_content = nip44_encrypt(
        _get_secret_key(bunkers_data),
        PublicKey.parse(client_pubkey),
        json_dumps(payload),
        Nip44Version.V2,
    )

    if url_data:
        for relay in url_data.relays:
            if relay in runtime_state.ensured_relays:
                continue
            try:
                nostr_client.relay_manager.add_relay(relay)
                runtime_state.ensured_relays.add(relay)
            except Exception as exc:
                logger.warning(f"[nostr_bunker] Failed to add response relay '{relay}': {exc}")

    response_event = {
        "kind": NIP46_KIND,
        "content": encrypted_content,
        "tags": [["p", client_pubkey]],
        "created_at": int(time.time()),
    }
    signed_response = sign_event(
        response_event,
        signer_pubkey,
        _get_signing_private_key(bunkers_data),
    )
    nostr_client.relay_manager.publish_message(json.dumps(["EVENT", signed_response]))


def _get_signing_private_key(bunker: BunkersData) -> PrivateKey:
    if not bunker.nsec:
        raise ValueError("Bunker has no nsec configured.")
    private_key_hex = normalize_private_key(bunker.nsec)
    return PrivateKey(bytes.fromhex(private_key_hex))


def _get_secret_key(bunker: BunkersData) -> SecretKey:
    if not bunker.nsec:
        raise ValueError("Bunker has no nsec configured.")
    private_key_hex = normalize_private_key(bunker.nsec)
    return SecretKey.parse(private_key_hex)


def _parse_unsigned_event_param(params: list) -> dict:
    if not params:
        raise PermissionError("Missing unsigned event payload.")
    raw_event = params[0]
    if isinstance(raw_event, str):
        return json.loads(raw_event)
    if isinstance(raw_event, dict):
        return raw_event
    raise PermissionError("Invalid unsigned event payload.")


def _sign_event_payload(bunker: BunkersData, unsigned_event: dict) -> dict:
    signer_pubkey = derive_remote_signer_pubkey(bunker.nsec)
    if not signer_pubkey:
        raise ValueError("Bunker has no signer key configured.")
    payload = dict(unsigned_event)
    return sign_event(payload, signer_pubkey, _get_signing_private_key(bunker))


async def _assert_post_rate_limit(url_data: UrlData, kind: int) -> None:
    if kind != 1 or not url_data.post_rate_limit_per_day:
        return

    since = datetime.now(timezone.utc) - timedelta(days=1)
    recent_requests = await get_signing_requests_since(url_data.id, since)
    count = sum(1 for request in recent_requests if int(request.event.get("kind", 0)) == 1)
    if count >= url_data.post_rate_limit_per_day:
        raise PermissionError("Daily post signing limit reached for this bunker URL.")


def _assert_url_is_active(url_data: UrlData) -> None:
    if url_data.expires_at and url_data.expires_at <= datetime.now(timezone.utc):
        raise PermissionError("This bunker URL has expired.")


def _assert_method_allowed(url_data: UrlData, method: str, kind: int | None = None) -> None:
    if method in {"ping", "switch_relays"}:
        return
    if method == "get_public_key" and (url_data.can_read or "get_public_key" in url_data.permissions):
        return
    if method == "sign_event":
        if not url_data.can_write:
            raise PermissionError("This bunker URL is not allowed to write.")
        if "sign_event" in url_data.permissions:
            return
        if kind is not None and f"sign_event:{kind}" in url_data.permissions:
            return
        raise PermissionError(f"Missing NIP-46 permission for sign_event:{kind}.")
    if method in url_data.permissions:
        return
    raise PermissionError(f"Missing NIP-46 permission for {method}.")


def _requested_permissions_allowed(url_data: UrlData, requested_permissions: str) -> bool:
    requested = {permission.strip() for permission in str(requested_permissions).split(",") if permission.strip()}
    allowed = set(url_data.permissions)
    for permission in requested:
        if permission.startswith("sign_event:"):
            if permission in allowed or "sign_event" in allowed:
                continue
            return False
        if permission not in allowed:
            return False
    return True


async def _get_bunker_by_remote_signer_pubkey(
    remote_signer_pubkey: str,
) -> BunkersData | None:
    bunkers = await get_all_bunkers_data()
    return next(
        (bunker for bunker in bunkers if derive_remote_signer_pubkey(bunker.nsec) == remote_signer_pubkey),
        None,
    )


def _extract_first_p_tag(tags: list[list[str]]) -> str | None:
    for tag in tags:
        if len(tag) >= 2 and tag[0] == "p":
            return tag[1]
    return None
