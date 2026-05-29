# Nostr Bunker - [LNbits](https://github.com/lnbits/lnbits) Extension

`nostr_bunker` turns an LNbits wallet account into a NIP-46 remote signer.

You create a bunker, then create one or more bunker URLs for that bunker. Each URL can have its own relay list, secret, permissions, signing mode, expiry, and post rate limit. That lets one bunker safely serve multiple clients with different policies.

## What It Does

- Creates real `bunker://...` invite URLs
- Uses `nostrclient` as the shared relay utility layer
- Handles NIP-46 `connect`, `ping`, `get_public_key`, `switch_relays`
- Supports `nip04_*` and `nip44_*` requests
- Supports `sign_event` with per-URL permission checks
- Supports auto-sign or confirm-before-sign flows
- Stores pending signing requests for manual approval

## Data Model

### Bunker

A bunker is the signer itself:

- `name`
- `nsec`

The signer pubkey is derived from the bunker `nsec`.

### URL

A bunker can have many URL records. Each URL record defines one client policy:

- `relays`
- `secret`
- `permissions`
- `auto_sign`
- `confirm_sign`
- `expires_at`
- `post_rate_limit_per_day`

## Friendly Capabilities

The UI maps common client needs to the underlying NIP-46 permissions, so you can grant things like:

- Read profile
- Update profile
- Read follows
- Update follows
- Read posts
- Sign posts
- Delete posts
- Repost posts
- React to posts
- Read DMs
- Sign DMs

## Runtime Notes

This extension depends on `nostrclient` for relay connectivity. The bunker runtime subscribes to NIP-46 requests and publishes replies through that shared relay layer.

If you change bunkers or bunker URLs, the runtime refreshes its subscriptions automatically. After code changes, restart LNbits.

## Current Scope

This extension is built around bunker-initiated login with `bunker://...` URLs and per-client policy enforcement. It is intended for Nostr clients that use standard NIP-46 bunker flows.
