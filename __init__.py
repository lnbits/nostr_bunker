import asyncio

from fastapi import APIRouter
from lnbits.tasks import create_permanent_unique_task
from loguru import logger

from .crud import db
from .tasks import start_nip46_runtime, wait_for_paid_invoices
from .views import nostr_bunker_generic_router
from .views_api import nostr_bunker_api_router

nostr_bunker_ext: APIRouter = APIRouter(prefix="/nostr_bunker", tags=["Nostr Bunker"])
nostr_bunker_ext.include_router(nostr_bunker_generic_router)
nostr_bunker_ext.include_router(nostr_bunker_api_router)


nostr_bunker_static_files = [
    {
        "path": "/nostr_bunker/static",
        "name": "nostr_bunker_static",
    }
]

scheduled_tasks: list[asyncio.Task] = []


def nostr_bunker_stop():
    for task in scheduled_tasks:
        try:
            task.cancel()
        except Exception as ex:
            logger.warning(ex)


def nostr_bunker_start():
    task = create_permanent_unique_task("ext_nostr_bunker", wait_for_paid_invoices)
    scheduled_tasks.append(task)
    runtime_task = create_permanent_unique_task(
        "ext_nostr_bunker_nip46_runtime",
        start_nip46_runtime,
    )
    scheduled_tasks.append(runtime_task)


__all__ = [
    "db",
    "nostr_bunker_ext",
    "nostr_bunker_start",
    "nostr_bunker_static_files",
    "nostr_bunker_stop",
]
