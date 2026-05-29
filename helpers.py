# Description: A place for helper functions.

import re
from urllib.parse import quote

from coincurve import PrivateKey
from lnbits.utils.nostr import normalize_private_key, is_ws_url


def is_valid_email_address(email: str) -> bool:
    email_regex = r"[A-Za-z0-9\._%+-]+@[A-Za-z0-9\.-]+\.[A-Za-z]{2,63}"
    return re.fullmatch(email_regex, email) is not None


def derive_remote_signer_pubkey(nsec: str | None) -> str | None:
    if not nsec:
        return None
    try:
        private_key_hex = normalize_private_key(nsec)
        public_key = PrivateKey(bytes.fromhex(private_key_hex)).public_key.format().hex()
        return public_key[2:]
    except Exception:
        return None


def validate_relay_urls(relays: list[str]) -> list[str]:
    cleaned_relays = [relay.strip() for relay in relays if relay and relay.strip()]
    if not cleaned_relays:
        raise ValueError("At least one relay is required.")
    invalid_relays = [relay for relay in cleaned_relays if not is_ws_url(relay)]
    if invalid_relays:
        raise ValueError("Relays must use ws:// or wss:// URLs.")
    return cleaned_relays


def build_bunker_url(
    remote_signer_pubkey: str | None,
    relays: list[str],
    secret: str | None,
) -> str | None:
    if not remote_signer_pubkey or not relays:
        return None

    query_params = [f"relay={quote(relay, safe='')}" for relay in relays]
    if secret:
        query_params.append(f"secret={quote(secret, safe='')}")
    return f"bunker://{remote_signer_pubkey}?{'&'.join(query_params)}"
