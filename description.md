## Nostr Bunker

Nostr Bunker is an LNbits extension that acts as a NIP-46 remote signer.

Create a bunker from an `nsec`, then create multiple bunker URLs for it. Each URL can have its own relay list, secret, permissions, expiry, signing mode, and post rate limit.

This lets you run one signer with different policies for different Nostr clients:

- auto-sign trusted actions
- require confirmation for riskier signing
- limit what kinds of events a client can sign
- keep DM/profile permissions separate from posting permissions

The extension uses `nostrclient` as its relay utility layer and generates real `bunker://...` invite URLs for compatible clients.
