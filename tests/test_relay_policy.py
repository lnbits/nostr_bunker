import json
import sys
from types import ModuleType, SimpleNamespace
from unittest.mock import AsyncMock, Mock

import httpx
import pytest
from fastapi import FastAPI, HTTPException
from lnbits.decorators import check_account_id_exists

from .. import nostr_bunker_ext, services, views_api
from ..models import BunkersData, UrlData

APPROVED = "wss://approved.example/relay"


@pytest.fixture
def approved_configuration(monkeypatch):
    router = ModuleType("test_nostrclient.router")
    router.nostr_client = SimpleNamespace(running=True, relay_manager=Mock())
    crud = ModuleType("test_nostrclient.crud")
    crud.get_relays = AsyncMock(return_value=[SimpleNamespace(url=APPROVED)])
    monkeypatch.setitem(sys.modules, crud.__name__, crud)
    monkeypatch.setattr(services, "_get_nostrclient_router", lambda: router)
    return crud, router


@pytest.fixture
def api(monkeypatch, approved_configuration):
    app = FastAPI()
    app.include_router(nostr_bunker_ext)
    app.dependency_overrides[check_account_id_exists] = lambda: SimpleNamespace(id="ordinary")
    bunker = BunkersData(id="bunker", user_id="ordinary", name=None, nsec=None)
    url = UrlData(id="url", bunkers_data_id="bunker", name=None, relays=[APPROVED])
    monkeypatch.setattr(views_api, "get_bunkers_data", AsyncMock(return_value=bunker))
    monkeypatch.setattr(views_api, "get_url_data_by_id", AsyncMock(return_value=url))
    monkeypatch.setattr(views_api, "mark_runtime_state_dirty", lambda: None)
    create = AsyncMock(return_value=url)
    update = AsyncMock(return_value=url)
    monkeypatch.setattr(views_api, "create_url_data", create)
    monkeypatch.setattr(views_api, "update_url_data", update)
    return app, create, update


@pytest.mark.asyncio
@pytest.mark.parametrize("method, path", [("POST", "bunker"), ("PUT", "url")])
@pytest.mark.parametrize("relay", ["ws://127.0.0.1:8080", "wss://unapproved.example", APPROVED + "/other"])
async def test_api_rejects_unapproved_relays(api, method, path, relay):
    app, create, update = api
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        response = await client.request(method, f"/nostr_bunker/api/v1/url_data/{path}", json={"relays": [relay]})
    assert response.status_code == 400
    create.assert_not_awaited()
    update.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("method, path", [("POST", "bunker"), ("PUT", "url")])
async def test_ordinary_user_can_save_approved_relays(api, method, path):
    app, create, update = api
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        response = await client.request(method, f"/nostr_bunker/api/v1/url_data/{path}", json={"relays": [APPROVED]})
    assert response.status_code == (201 if method == "POST" else 200)
    assert response.json()["relays"] == [APPROVED]
    assert create.await_count + update.await_count == 1


@pytest.mark.asyncio
async def test_relay_options_are_authenticated_and_use_saved_configuration(api, approved_configuration):
    app, _, _ = api
    crud, router = approved_configuration
    router.nostr_client.relay_manager.relays = {"ws://127.0.0.1": Mock()}
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/nostr_bunker/api/v1/relays")
        assert response.status_code == 200
        assert response.json() == [APPROVED]

        async def unauthenticated():
            raise HTTPException(401, "Authentication required")

        app.dependency_overrides[check_account_id_exists] = unauthenticated
        assert (await client.get("/nostr_bunker/api/v1/relays")).status_code == 401
    crud.get_relays.assert_awaited_once()


@pytest.mark.asyncio
async def test_approval_removal_takes_effect_without_restart(approved_configuration):
    crud, _ = approved_configuration
    await services.check_approved_relays([APPROVED])
    crud.get_relays.return_value = []
    with pytest.raises(ValueError, match="administrator"):
        await services.check_approved_relays([APPROVED])


@pytest.mark.asyncio
async def test_missing_nostrclient_fails_closed(api, monkeypatch):
    app, create, update = api
    monkeypatch.setattr(services, "_get_nostrclient_router", Mock(side_effect=RuntimeError("Nostrclient unavailable")))
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        assert (await client.get("/nostr_bunker/api/v1/relays")).status_code == 503
        response = await client.post("/nostr_bunker/api/v1/url_data/bunker", json={"relays": [APPROVED]})
        assert response.status_code == 503
    create.assert_not_awaited()
    update.assert_not_awaited()


@pytest.mark.asyncio
async def test_runtime_does_not_connect_to_stored_user_relays(approved_configuration, monkeypatch):
    _, router = approved_configuration
    monkeypatch.setattr(services, "runtime_state", services.RuntimeState())
    monkeypatch.setattr(services, "get_all_bunkers_data", AsyncMock(return_value=[SimpleNamespace(nsec="key")]))
    monkeypatch.setattr(services, "derive_remote_signer_pubkey", lambda _: "signer")
    await services._refresh_runtime_state()
    manager = router.nostr_client.relay_manager
    manager.add_relay.assert_not_called()
    manager.add_subscription.assert_called_once()

    monkeypatch.setattr(services, "_get_secret_key", Mock())
    monkeypatch.setattr(services, "_get_signing_private_key", Mock())
    monkeypatch.setattr(services, "PublicKey", Mock())
    monkeypatch.setattr(services, "nip44_encrypt", Mock(return_value="encrypted"))
    monkeypatch.setattr(services, "sign_event", Mock(return_value={"id": "signed"}))
    await services._publish_response(
        SimpleNamespace(nsec="key"), SimpleNamespace(relays=["ws://127.0.0.1:8080"]), "recipient", "request"
    )
    manager.add_relay.assert_not_called()
    manager.publish_message.assert_called_once()


@pytest.mark.asyncio
async def test_switch_relays_does_not_advertise_removed_relays(approved_configuration):
    result = await services._dispatch_request(
        None, SimpleNamespace(relays=[APPROVED, "ws://127.0.0.1:8080"]), "client", "request", "switch_relays", []
    )
    assert json.loads(result) == [APPROVED]
