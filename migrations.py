# the migration file is where you build your database tables
# If you create a new release for your extension ,
# remember the migration file is like a blockchain, never edit only add!

empty_dict: dict[str, str] = {}


async def m002_bunkers_data(db):
    """
    Initial bunkers data table.
    """

    await db.execute(
        f"""
        CREATE TABLE nostr_bunker.bunkers_data (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            name TEXT,
            nsec TEXT,
            created_at TIMESTAMP NOT NULL DEFAULT {db.timestamp_now},
            updated_at TIMESTAMP NOT NULL DEFAULT {db.timestamp_now}
        );
    """
    )


async def m003_url_data(db):
    """
    Initial url data table.
    """

    await db.execute(
        f"""
        CREATE TABLE nostr_bunker.url_data (
            id TEXT PRIMARY KEY,
            bunkers_data_id TEXT NOT NULL,
            name TEXT,
            permisions TEXT DEFAULT '{empty_dict}',
            created_at TIMESTAMP NOT NULL DEFAULT {db.timestamp_now},
            updated_at TIMESTAMP NOT NULL DEFAULT {db.timestamp_now}
        );
    """
    )


async def m004_nip46_permissions_and_signing_requests(db):
    """
    Add NIP-46 bunker URL policy fields and pending signing requests.
    """

    await db.execute("ALTER TABLE nostr_bunker.bunkers_data ADD COLUMN remote_signer_pubkey TEXT;")
    await db.execute("ALTER TABLE nostr_bunker.bunkers_data ADD COLUMN user_pubkey TEXT;")
    await db.execute("ALTER TABLE nostr_bunker.bunkers_data ADD COLUMN relays TEXT DEFAULT '[]';")
    await db.execute("ALTER TABLE nostr_bunker.url_data ADD COLUMN permissions TEXT DEFAULT '[]';")
    await db.execute("ALTER TABLE nostr_bunker.url_data ADD COLUMN auto_sign BOOLEAN DEFAULT false;")
    await db.execute("ALTER TABLE nostr_bunker.url_data ADD COLUMN confirm_sign BOOLEAN DEFAULT true;")
    await db.execute("ALTER TABLE nostr_bunker.url_data ADD COLUMN expires_at TIMESTAMP;")
    await db.execute("ALTER TABLE nostr_bunker.url_data ADD COLUMN can_read BOOLEAN DEFAULT true;")
    await db.execute("ALTER TABLE nostr_bunker.url_data ADD COLUMN can_write BOOLEAN DEFAULT false;")
    await db.execute("ALTER TABLE nostr_bunker.url_data ADD COLUMN post_rate_limit_per_day INTEGER;")
    await db.execute("ALTER TABLE nostr_bunker.url_data ADD COLUMN secret TEXT;")

    await db.execute(
        f"""
        CREATE TABLE nostr_bunker.signing_requests (
            id TEXT PRIMARY KEY,
            url_data_id TEXT NOT NULL,
            request_id TEXT NOT NULL,
            client_pubkey TEXT NOT NULL,
            event TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            signed_event TEXT,
            error TEXT,
            expires_at TIMESTAMP,
            created_at TIMESTAMP NOT NULL DEFAULT {db.timestamp_now},
            updated_at TIMESTAMP NOT NULL DEFAULT {db.timestamp_now}
        );
    """
    )


async def m005_url_relays(db):
    """
    Add relay URLs to bunker invite records.
    """

    await db.execute("ALTER TABLE nostr_bunker.url_data ADD COLUMN relays TEXT DEFAULT '[]';")


async def m006_url_client_pubkey(db):
    """
    Track which client pubkey has claimed a bunker invite URL.
    """

    await db.execute("ALTER TABLE nostr_bunker.url_data ADD COLUMN client_pubkey TEXT;")
