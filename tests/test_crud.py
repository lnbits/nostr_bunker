import json
from uuid import uuid4

import pytest
from coincurve import PrivateKey
from fastapi.exceptions import HTTPException
from lnbits.utils.nostr import sign_event
from nostr_sdk import Keys, Nip44Version, PublicKey, SecretKey, nip44_decrypt, nip44_encrypt

from nostr_bunker.crud import (  # type: ignore[import]
    create_bunkers_data,
    create_signing_request,
    create_url_data,
    delete_bunkers_data,
    delete_url_data,
    enrich_url_data,
    get_bunkers_data,
    get_bunkers_data_by_id,
    get_bunkers_data_ids_by_user,
    get_bunkers_data_paginated,
    get_signing_request_by_id,
    get_signing_requests_paginated,
    get_url_data_by_id,
    get_url_data_ids_by_bunkers_data_ids,
    get_url_data_paginated,
    update_bunkers_data,
    update_signing_request,
    update_url_data,
)
from nostr_bunker.helpers import derive_remote_signer_pubkey  # type: ignore[import]
from nostr_bunker.models import (  # type: ignore[import]
    BunkersData,
    CreateBunkersData,
    CreateSigningRequest,
    CreateUrlData,
    UpdateSigningRequest,
    UrlData,
)
from nostr_bunker.services import (  # type: ignore[import]
    _assert_post_rate_limit,
    _handle_request_event,
    _refresh_runtime_state,
    complete_signing_request_action,
    mark_runtime_state_dirty,
    runtime_state,
)
from nostr_bunker.views_api import api_delete_bunkers_data  # type: ignore[import]


@pytest.mark.asyncio
async def test_create_and_get_bunkers_data():
    user_id = uuid4().hex
    bunker_secret_hex = Keys.generate().secret_key().to_hex()

    data = CreateBunkersData(
        name="name_NbHwALeTLSHooBFqVySAP6",
        nsec=bunker_secret_hex,
    )
    bunkers_data_one = await create_bunkers_data(user_id, data)
    assert bunkers_data_one.id is not None
    assert bunkers_data_one.user_id == user_id

    bunkers_data_one = await get_bunkers_data(user_id, bunkers_data_one.id)
    assert bunkers_data_one.id is not None
    assert bunkers_data_one.user_id == user_id
    assert bunkers_data_one.name == data.name
    assert bunkers_data_one.nsec == data.nsec

    data = CreateBunkersData(
        name="name_NbHwALeTLSHooBFqVySAP6",
        nsec=bunker_secret_hex,
    )
    with pytest.raises(ValueError, match="already exists"):
        await create_bunkers_data(user_id, data)

    bunkers_data_list = await get_bunkers_data_ids_by_user(user_id=user_id)
    assert len(bunkers_data_list) == 1

    bunkers_data_page = await get_bunkers_data_paginated(user_id=user_id)
    assert bunkers_data_page.total == 1
    assert len(bunkers_data_page.data) == 1

    await delete_bunkers_data(user_id, bunkers_data_one.id)
    bunkers_data_list = await get_bunkers_data_ids_by_user(user_id=user_id)
    assert len(bunkers_data_list) == 0

    bunkers_data_page = await get_bunkers_data_paginated(user_id=user_id)
    assert bunkers_data_page.total == 0
    assert len(bunkers_data_page.data) == 0


@pytest.mark.asyncio
async def test_update_bunkers_data():
    user_id = uuid4().hex
    bunker_secret_hex = Keys.generate().secret_key().to_hex()
    updated_secret_hex = Keys.generate().secret_key().to_hex()

    data = CreateBunkersData(
        name="name_NbHwALeTLSHooBFqVySAP6",
        nsec=bunker_secret_hex,
    )
    bunkers_data_one = await create_bunkers_data(user_id, data)
    assert bunkers_data_one.id is not None
    assert bunkers_data_one.user_id == user_id

    bunkers_data_one = await get_bunkers_data(user_id, bunkers_data_one.id)
    assert bunkers_data_one.id is not None
    assert bunkers_data_one.user_id == user_id
    assert bunkers_data_one.name == data.name
    assert bunkers_data_one.nsec == data.nsec

    data_updated = CreateBunkersData(
        name="name_updated",
        nsec=updated_secret_hex,
    )
    bunkers_data_updated = BunkersData(**{**bunkers_data_one.dict(), **data_updated.dict()})

    await update_bunkers_data(bunkers_data_updated)
    bunkers_data_one = await get_bunkers_data_by_id(bunkers_data_one.id)
    assert bunkers_data_one.name == bunkers_data_updated.name
    assert bunkers_data_one.nsec == bunkers_data_updated.nsec


@pytest.mark.asyncio
async def test_update_bunkers_data_rejects_duplicate_nsec():
    user_id = uuid4().hex
    first_secret_hex = Keys.generate().secret_key().to_hex()
    second_secret_hex = Keys.generate().secret_key().to_hex()

    await create_bunkers_data(
        user_id,
        CreateBunkersData(name="first", nsec=first_secret_hex),
    )
    second_bunker = await create_bunkers_data(
        user_id,
        CreateBunkersData(name="second", nsec=second_secret_hex),
    )

    duplicate_bunker = BunkersData(
        **{**second_bunker.dict(), "nsec": first_secret_hex},
    )
    with pytest.raises(ValueError, match="already exists"):
        await update_bunkers_data(duplicate_bunker)

    fetched = await get_bunkers_data_by_id(second_bunker.id)
    assert fetched.nsec == second_secret_hex


@pytest.mark.asyncio
async def test_create_update_and_delete_url_data():
    user_id = uuid4().hex
    bunker = await create_bunkers_data(
        user_id,
        CreateBunkersData(name="bunker", nsec=Keys.generate().secret_key().to_hex()),
    )

    data = CreateUrlData(
        name="mobile client",
        relays=["wss://relay.example"],
        permissions=["get_public_key", "sign_event:1", "nip44_encrypt"],
        auto_sign=True,
        confirm_sign=False,
        can_read=True,
        can_write=True,
        post_rate_limit_per_day=25,
    )
    url_data = await create_url_data(bunker.id, data)

    assert url_data.id is not None
    assert url_data.bunkers_data_id == bunker.id
    assert url_data.relays == ["wss://relay.example"]
    assert url_data.permissions == data.permissions
    assert url_data.auto_sign is True
    assert url_data.confirm_sign is False
    assert url_data.can_write is True
    assert url_data.post_rate_limit_per_day == 25
    assert url_data.secret is not None

    url_data_ids = await get_url_data_ids_by_bunkers_data_ids([bunker.id])
    assert url_data.id in url_data_ids

    page = await get_url_data_paginated([bunker.id])
    assert page.total == 1

    updated = UrlData(
        **{
            **url_data.dict(),
            **CreateUrlData(
                name="desktop client",
                relays=["wss://relay.example", "wss://relay2.example"],
                permissions=["get_public_key"],
                auto_sign=False,
                confirm_sign=True,
                can_read=True,
                can_write=False,
                post_rate_limit_per_day=1,
            ).dict(),
        }
    )
    await update_url_data(updated)
    fetched = await get_url_data_by_id(url_data.id)
    assert fetched
    assert fetched.name == "desktop client"
    assert fetched.permissions == ["get_public_key"]
    assert fetched.auto_sign is False
    assert fetched.confirm_sign is True

    await delete_url_data(bunker.id, url_data.id)
    assert await get_url_data_by_id(url_data.id) is None


@pytest.mark.asyncio
async def test_url_data_auto_sign_disables_confirm_sign():
    user_id = uuid4().hex
    bunker = await create_bunkers_data(
        user_id,
        CreateBunkersData(name="bunker", nsec=Keys.generate().secret_key().to_hex()),
    )

    url_data = await create_url_data(
        bunker.id,
        CreateUrlData(
            name="auto signer",
            relays=["wss://relay.example"],
            permissions=["sign_event:1"],
            auto_sign=True,
            confirm_sign=True,
            can_write=True,
        ),
    )
    assert url_data.auto_sign is True
    assert url_data.confirm_sign is False

    url_data.confirm_sign = True
    updated = await update_url_data(url_data)
    assert updated.auto_sign is True
    assert updated.confirm_sign is False


@pytest.mark.asyncio
async def test_create_and_update_signing_request():
    user_id = uuid4().hex
    bunker = await create_bunkers_data(
        user_id,
        CreateBunkersData(name="bunker", nsec="1" * 64),
    )
    url_data = await create_url_data(
        bunker.id,
        CreateUrlData(
            name="client",
            relays=["wss://relay.example"],
            permissions=["sign_event:1"],
        ),
    )

    signing_request = await create_signing_request(
        url_data.id,
        CreateSigningRequest(
            request_id="request-1",
            client_pubkey="client-pubkey",
            event={"kind": 1, "content": "hello", "tags": [], "created_at": 1},
        ),
    )
    assert signing_request.status == "pending"
    assert signing_request.event["kind"] == 1

    page = await get_signing_requests_paginated([url_data.id])
    assert page.total == 1

    updated = await update_signing_request(
        signing_request,
        UpdateSigningRequest(
            status="approved",
            signed_event={"id": "event-id"},
        ),
    )
    assert updated.status == "approved"
    assert updated.signed_event == {"id": "event-id"}

    fetched = await get_signing_request_by_id(signing_request.id)
    assert fetched
    assert fetched.status == "approved"

    enriched = enrich_url_data(url_data, bunker)
    assert enriched.remote_signer_pubkey is not None
    assert enriched.bunker_url
    assert enriched.bunker_url.startswith("bunker://")
    assert "relay=wss%3A%2F%2Frelay.example" in enriched.bunker_url


@pytest.mark.asyncio
async def test_nip46_connect_and_auto_sign(monkeypatch):
    bunker_keys = Keys.generate()
    client_keys = Keys.generate()
    bunker_secret_hex = bunker_keys.secret_key().to_hex()
    bunker_pubkey = bunker_keys.public_key().to_hex()
    client_secret_hex = client_keys.secret_key().to_hex()
    client_pubkey = client_keys.public_key().to_hex()

    bunker = await create_bunkers_data(
        uuid4().hex,
        CreateBunkersData(name="bunker", nsec=bunker_secret_hex),
    )
    url_data = await create_url_data(
        bunker.id,
        CreateUrlData(
            name="client",
            relays=["wss://relay.example"],
            permissions=["get_public_key", "sign_event:1"],
            auto_sign=True,
            confirm_sign=False,
            can_write=True,
            secret="wobble",
        ),
    )

    published_messages = []
    monkeypatch.setattr(
        "nostr_bunker.services.nostr_client.relay_manager.publish_message",
        published_messages.append,
    )
    monkeypatch.setattr(
        "nostr_bunker.services.nostr_client.relay_manager.add_relay",
        lambda *_args, **_kwargs: None,
    )

    connect_payload = {
        "id": "connect-1",
        "method": "connect",
        "params": [bunker_pubkey, "wobble", "get_public_key,sign_event:1"],
    }
    connect_event = _build_nip46_request_event(
        client_pubkey=client_pubkey,
        client_secret_hex=client_secret_hex,
        bunker_pubkey=bunker_pubkey,
        payload=connect_payload,
    )

    await _handle_request_event(connect_event)

    assert len(published_messages) == 1
    connect_response = _decrypt_published_response(
        published_messages.pop(),
        client_secret_hex=client_secret_hex,
        bunker_pubkey=bunker_pubkey,
    )
    assert connect_response["id"] == "connect-1"
    assert connect_response["result"] == "wobble"

    fetched_url_data = await get_url_data_by_id(url_data.id)
    assert fetched_url_data
    assert fetched_url_data.client_pubkey == client_pubkey

    sign_payload = {
        "id": "sign-1",
        "method": "sign_event",
        "params": [
            json.dumps(
                {
                    "kind": 1,
                    "content": "hello from bunker",
                    "tags": [],
                    "created_at": 1714078911,
                }
            )
        ],
    }
    sign_event_request = _build_nip46_request_event(
        client_pubkey=client_pubkey,
        client_secret_hex=client_secret_hex,
        bunker_pubkey=bunker_pubkey,
        payload=sign_payload,
    )

    await _handle_request_event(sign_event_request)

    assert len(published_messages) == 1
    sign_response = _decrypt_published_response(
        published_messages.pop(),
        client_secret_hex=client_secret_hex,
        bunker_pubkey=bunker_pubkey,
    )
    signed_event = json.loads(sign_response["result"])
    assert signed_event["kind"] == 1
    assert signed_event["content"] == "hello from bunker"
    assert signed_event["pubkey"] == bunker_pubkey

    page = await get_signing_requests_paginated([url_data.id])
    assert page.total == 1
    assert page.data[0].status == "signed"


@pytest.mark.asyncio
async def test_complete_signing_request_action_publishes_response(monkeypatch):
    bunker_keys = Keys.generate()
    client_keys = Keys.generate()
    bunker_secret_hex = bunker_keys.secret_key().to_hex()
    bunker_pubkey = bunker_keys.public_key().to_hex()
    client_secret_hex = client_keys.secret_key().to_hex()
    client_pubkey = client_keys.public_key().to_hex()

    bunker = await create_bunkers_data(
        uuid4().hex,
        CreateBunkersData(name="bunker", nsec=bunker_secret_hex),
    )
    url_data = await create_url_data(
        bunker.id,
        CreateUrlData(
            name="client",
            relays=["wss://relay.example"],
            permissions=["sign_event:1"],
            can_write=True,
        ),
    )
    url_data.client_pubkey = client_pubkey
    await update_url_data(url_data)

    signing_request = await create_signing_request(
        url_data.id,
        CreateSigningRequest(
            request_id="approve-1",
            client_pubkey=client_pubkey,
            event={
                "kind": 1,
                "content": "approve me",
                "tags": [],
                "created_at": 1714078911,
            },
        ),
    )

    published_messages = []
    monkeypatch.setattr(
        "nostr_bunker.services.nostr_client.relay_manager.publish_message",
        published_messages.append,
    )
    monkeypatch.setattr(
        "nostr_bunker.services.nostr_client.relay_manager.add_relay",
        lambda *_args, **_kwargs: None,
    )

    updated = await complete_signing_request_action(signing_request.id, "approved")
    assert updated.status == "signed"
    assert updated.signed_event is not None
    assert len(published_messages) == 1

    response = _decrypt_published_response(
        published_messages.pop(),
        client_secret_hex=client_secret_hex,
        bunker_pubkey=bunker_pubkey,
    )
    assert response["id"] == "approve-1"
    assert json.loads(response["result"])["content"] == "approve me"


@pytest.mark.asyncio
async def test_refresh_runtime_state_uses_structured_subscription_filters(monkeypatch):
    bunker_keys = Keys.generate()
    bunker = await create_bunkers_data(
        uuid4().hex,
        CreateBunkersData(name="bunker", nsec=bunker_keys.secret_key().to_hex()),
    )
    await create_url_data(
        bunker.id,
        CreateUrlData(
            name="client",
            relays=["wss://relay.example"],
            permissions=["get_public_key"],
        ),
    )

    calls = {"subscription": None, "relays": []}
    monkeypatch.setattr(
        "nostr_bunker.services.nostr_client.relay_manager.add_relay",
        lambda relay: calls["relays"].append(relay),
    )
    monkeypatch.setattr(
        "nostr_bunker.services.nostr_client.relay_manager.close_subscription",
        lambda sub_id: None,
    )
    monkeypatch.setattr(
        "nostr_bunker.services.nostr_client.relay_manager.add_subscription",
        lambda sub_id, filters: calls.__setitem__("subscription", (sub_id, filters)),
    )

    runtime_state.subscribed_pubkeys = set()
    runtime_state.ensured_relays = set()
    runtime_state.next_refresh_at = 0

    await _refresh_runtime_state()

    assert calls["relays"] == ["wss://relay.example"]
    assert calls["subscription"] is not None
    sub_id, filters = calls["subscription"]
    assert sub_id == "nostr_bunker_nip46"
    assert len(filters) == 1
    assert filters[0]["kinds"] == [24133]
    assert derive_remote_signer_pubkey(bunker.nsec) in filters[0]["#p"]


@pytest.mark.asyncio
async def test_connect_can_rebind_url_to_new_client_pubkey(monkeypatch):
    bunker_keys = Keys.generate()
    bunker_secret_hex = bunker_keys.secret_key().to_hex()
    bunker_pubkey = bunker_keys.public_key().to_hex()
    first_client = Keys.generate()
    second_client = Keys.generate()

    bunker = await create_bunkers_data(
        uuid4().hex,
        CreateBunkersData(name="bunker", nsec=bunker_secret_hex),
    )
    url_data = await create_url_data(
        bunker.id,
        CreateUrlData(
            name="client",
            relays=["wss://relay.example"],
            permissions=["get_public_key"],
            secret="wobble",
        ),
    )
    url_data.client_pubkey = first_client.public_key().to_hex()
    await update_url_data(url_data)

    published_messages = []
    monkeypatch.setattr(
        "nostr_bunker.services.nostr_client.relay_manager.publish_message",
        published_messages.append,
    )
    monkeypatch.setattr(
        "nostr_bunker.services.nostr_client.relay_manager.add_relay",
        lambda *_args, **_kwargs: None,
    )

    connect_payload = {
        "id": "connect-rebind",
        "method": "connect",
        "params": [bunker_pubkey, "wobble", "get_public_key"],
    }
    connect_event = _build_nip46_request_event(
        client_pubkey=second_client.public_key().to_hex(),
        client_secret_hex=second_client.secret_key().to_hex(),
        bunker_pubkey=bunker_pubkey,
        payload=connect_payload,
    )

    await _handle_request_event(connect_event)

    fetched = await get_url_data_by_id(url_data.id)
    assert fetched
    assert fetched.client_pubkey == second_client.public_key().to_hex()
    assert published_messages


def test_mark_runtime_state_dirty_resets_refresh_timer():
    runtime_state.next_refresh_at = 12345
    mark_runtime_state_dirty()
    assert runtime_state.next_refresh_at == 0


@pytest.mark.asyncio
async def test_update_url_data_regenerates_blank_secret():
    bunker = await create_bunkers_data(
        uuid4().hex,
        CreateBunkersData(name="bunker", nsec=Keys.generate().secret_key().to_hex()),
    )
    url_data = await create_url_data(
        bunker.id,
        CreateUrlData(
            name="client",
            relays=["wss://relay.example"],
            permissions=["get_public_key"],
            secret="wobble",
        ),
    )

    url_data.secret = None
    updated = await update_url_data(url_data)
    assert updated.secret
    assert updated.secret != "wobble"


@pytest.mark.asyncio
async def test_post_rate_limit_only_counts_kind_one_requests():
    bunker = await create_bunkers_data(
        uuid4().hex,
        CreateBunkersData(name="bunker", nsec=Keys.generate().secret_key().to_hex()),
    )
    url_data = await create_url_data(
        bunker.id,
        CreateUrlData(
            name="client",
            relays=["wss://relay.example"],
            permissions=["sign_event:1", "sign_event:4"],
            can_write=True,
            post_rate_limit_per_day=1,
        ),
    )

    await create_signing_request(
        url_data.id,
        CreateSigningRequest(
            request_id="dm-1",
            client_pubkey="client",
            event={"kind": 4, "content": "dm", "tags": [], "created_at": 1},
        ),
    )
    await _assert_post_rate_limit(url_data, 1)

    await create_signing_request(
        url_data.id,
        CreateSigningRequest(
            request_id="post-1",
            client_pubkey="client",
            event={"kind": 1, "content": "post", "tags": [], "created_at": 1},
        ),
    )
    with pytest.raises(PermissionError):
        await _assert_post_rate_limit(url_data, 1)


@pytest.mark.asyncio
async def test_delete_bunker_requires_clear_flag_when_urls_exist():
    user_id = uuid4().hex
    bunker = await create_bunkers_data(
        user_id,
        CreateBunkersData(name="bunker", nsec=Keys.generate().secret_key().to_hex()),
    )
    await create_url_data(
        bunker.id,
        CreateUrlData(
            name="client",
            relays=["wss://relay.example"],
            permissions=["get_public_key"],
        ),
    )

    account = type("Account", (), {"id": user_id})()
    with pytest.raises(HTTPException) as exc:
        await api_delete_bunkers_data(bunker.id, False, account)
    assert exc.value.status_code == 409

    response = await api_delete_bunkers_data(bunker.id, True, account)
    assert response.success is True


def _build_nip46_request_event(
    *,
    client_pubkey: str,
    client_secret_hex: str,
    bunker_pubkey: str,
    payload: dict,
) -> dict:
    encrypted_content = nip44_encrypt(
        SecretKey.parse(client_secret_hex),
        PublicKey.parse(bunker_pubkey),
        json.dumps(payload, separators=(",", ":")),
        Nip44Version.V2,
    )
    event = {
        "kind": 24133,
        "content": encrypted_content,
        "tags": [["p", bunker_pubkey]],
        "created_at": 1714078911,
    }
    return sign_event(
        event,
        client_pubkey,
        PrivateKey(bytes.fromhex(client_secret_hex)),
    )


def _decrypt_published_response(
    message: str,
    *,
    client_secret_hex: str,
    bunker_pubkey: str,
) -> dict:
    envelope = json.loads(message)
    assert envelope[0] == "EVENT"
    event = envelope[1]
    decrypted = nip44_decrypt(
        SecretKey.parse(client_secret_hex),
        PublicKey.parse(bunker_pubkey),
        event["content"],
    )
    return json.loads(decrypted)
