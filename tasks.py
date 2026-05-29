import asyncio

from lnbits.core.models import Payment
from lnbits.tasks import register_invoice_listener
from loguru import logger

from .services import payment_received_for_url_data, run_nip46_runtime

#######################################
########## RUN YOUR TASKS HERE ########
#######################################

# The usual task is to listen to invoices related to this extension


async def wait_for_paid_invoices():
    invoice_queue = asyncio.Queue()
    register_invoice_listener(invoice_queue, "ext_nostr_bunker")
    while True:
        payment = await invoice_queue.get()
        await on_invoice_paid(payment)


# Do somethhing when an invoice related top this extension is paid


async def on_invoice_paid(payment: Payment) -> None:
    if payment.extra.get("tag") != "nostr_bunker":
        return

    logger.info(f"Invoice paid for nostr_bunker: {payment.payment_hash}")

    try:
        await payment_received_for_url_data(payment)
    except Exception as e:
        logger.error(f"Error processing payment for nostr_bunker: {e}")


async def start_nip46_runtime() -> None:
    await run_nip46_runtime()
