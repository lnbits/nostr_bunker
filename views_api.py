# Description: This file contains the extensions API endpoints.
from http import HTTPStatus

from fastapi import APIRouter, Depends
from fastapi.exceptions import HTTPException
from lnbits.core.models import SimpleStatus
from lnbits.core.models.users import AccountId
from lnbits.db import Filters, Page
from lnbits.decorators import (
    check_account_id_exists,
    parse_filters,
)
from lnbits.helpers import generate_filter_params_openapi

from .crud import (
    create_bunkers_data,
    create_signing_request,
    create_url_data,
    delete_bunkers_data,
    delete_signing_request,
    delete_url_data,
    delete_url_data_by_bunkers_data_id,
    enrich_url_data,
    get_bunkers_data,
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
from .services import complete_signing_request_action, mark_runtime_state_dirty

bunkers_data_filters = parse_filters(BunkersDataFilters)
url_data_filters = parse_filters(UrlDataFilters)
signing_request_filters = parse_filters(SigningRequestFilters)

nostr_bunker_api_router = APIRouter()


############################# Bunkers Data #############################
@nostr_bunker_api_router.post("/api/v1/bunkers_data", status_code=HTTPStatus.CREATED)
async def api_create_bunkers_data(
    data: CreateBunkersData,
    account_id: AccountId = Depends(check_account_id_exists),
) -> BunkersData:
    bunkers_data = await create_bunkers_data(account_id.id, data)
    mark_runtime_state_dirty()
    return bunkers_data


@nostr_bunker_api_router.put("/api/v1/bunkers_data/{bunkers_data_id}", status_code=HTTPStatus.CREATED)
async def api_update_bunkers_data(
    bunkers_data_id: str,
    data: CreateBunkersData,
    account_id: AccountId = Depends(check_account_id_exists),
) -> BunkersData:
    bunkers_data = await get_bunkers_data(account_id.id, bunkers_data_id)
    if not bunkers_data:
        raise HTTPException(HTTPStatus.NOT_FOUND, "Bunkers Data not found.")
    if bunkers_data.user_id != account_id.id:
        raise HTTPException(HTTPStatus.FORBIDDEN, "You do not own this bunkers data.")
    bunkers_data = await update_bunkers_data(BunkersData(**{**bunkers_data.dict(), **data.dict()}))
    mark_runtime_state_dirty()
    return bunkers_data


@nostr_bunker_api_router.get(
    "/api/v1/bunkers_data/paginated",
    name="Bunkers Data List",
    summary="get paginated list of bunkers_data",
    response_description="list of bunkers_data",
    openapi_extra=generate_filter_params_openapi(BunkersDataFilters),
    response_model=Page[BunkersData],
)
async def api_get_bunkers_data_paginated(
    account_id: AccountId = Depends(check_account_id_exists),
    filters: Filters = Depends(bunkers_data_filters),
) -> Page[BunkersData]:

    return await get_bunkers_data_paginated(
        user_id=account_id.id,
        filters=filters,
    )


@nostr_bunker_api_router.get(
    "/api/v1/bunkers_data/{bunkers_data_id}",
    name="Get BunkersData",
    summary="Get the bunkers_data with this id.",
    response_description="An bunkers_data or 404 if not found",
    response_model=BunkersData,
)
async def api_get_bunkers_data(
    bunkers_data_id: str,
    account_id: AccountId = Depends(check_account_id_exists),
) -> BunkersData:

    bunkers_data = await get_bunkers_data(account_id.id, bunkers_data_id)
    if not bunkers_data:
        raise HTTPException(HTTPStatus.NOT_FOUND, "BunkersData not found.")

    return bunkers_data


@nostr_bunker_api_router.delete(
    "/api/v1/bunkers_data/{bunkers_data_id}",
    name="Delete Bunkers Data",
    summary="Delete the bunkers_data " "and optionally all its associated url_data.",
    response_description="The status of the deletion.",
    response_model=SimpleStatus,
)
async def api_delete_bunkers_data(
    bunkers_data_id: str,
    clear_url_data: bool | None = False,
    account_id: AccountId = Depends(check_account_id_exists),
) -> SimpleStatus:
    bunkers_data = await get_bunkers_data(account_id.id, bunkers_data_id)
    if not bunkers_data:
        raise HTTPException(HTTPStatus.NOT_FOUND, "Bunkers Data not found.")

    url_data_page = await get_url_data_paginated(
        bunkers_data_ids=[bunkers_data_id],
    )
    if url_data_page.total and clear_url_data is not True:
        raise HTTPException(
            HTTPStatus.CONFLICT,
            "Bunkers Data still has URL records. Delete with clear_url_data=true.",
        )

    if clear_url_data is True:
        await delete_url_data_by_bunkers_data_id(bunkers_data_id)
    await delete_bunkers_data(account_id.id, bunkers_data_id)
    mark_runtime_state_dirty()
    return SimpleStatus(success=True, message="Bunkers Data Deleted")


############################# Url Data #############################
@nostr_bunker_api_router.post(
    "/api/v1/url_data/{bunkers_data_id}",
    name="Create Url Data",
    summary="Create new url data for the specified bunkers data.",
    response_description="The created url data.",
    response_model=UrlData,
    status_code=HTTPStatus.CREATED,
)
async def api_create_url_data(
    bunkers_data_id: str,
    data: CreateUrlData,
    account_id: AccountId = Depends(check_account_id_exists),
) -> UrlData:
    bunkers_data = await get_bunkers_data(account_id.id, bunkers_data_id)
    if not bunkers_data:
        raise HTTPException(HTTPStatus.NOT_FOUND, "Bunkers Data not found.")

    url_data = await create_url_data(bunkers_data_id, data)
    mark_runtime_state_dirty()
    return enrich_url_data(url_data, bunkers_data)


@nostr_bunker_api_router.put(
    "/api/v1/url_data/{url_data_id}",
    name="Update Url Data",
    summary="Update the url_data with this id.",
    response_description="The updated url data.",
    response_model=UrlData,
)
async def api_update_url_data(
    url_data_id: str,
    data: CreateUrlData,
    account_id: AccountId = Depends(check_account_id_exists),
) -> UrlData:
    url_data = await get_url_data_by_id(url_data_id)
    if not url_data:
        raise HTTPException(HTTPStatus.NOT_FOUND, "Url Data not found.")

    bunkers_data = await get_bunkers_data(account_id.id, url_data.bunkers_data_id)
    if not bunkers_data:
        raise HTTPException(HTTPStatus.NOT_FOUND, "Bunkers Data not found.")

    url_data = await update_url_data(UrlData(**{**url_data.dict(), **data.dict()}))
    mark_runtime_state_dirty()
    return enrich_url_data(url_data, bunkers_data)


@nostr_bunker_api_router.get(
    "/api/v1/url_data/paginated",
    name="Url Data List",
    summary="get paginated list of url_data",
    response_description="list of url_data",
    openapi_extra=generate_filter_params_openapi(UrlDataFilters),
    response_model=Page[UrlData],
)
async def api_get_url_data_paginated(
    account_id: AccountId = Depends(check_account_id_exists),
    bunkers_data_id: str | None = None,
    filters: Filters = Depends(url_data_filters),
) -> Page[UrlData]:

    bunkers_data_ids = await get_bunkers_data_ids_by_user(account_id.id)

    if bunkers_data_id:
        if bunkers_data_id not in bunkers_data_ids:
            raise HTTPException(HTTPStatus.FORBIDDEN, "Not your bunkers data.")
        bunkers_data_ids = [bunkers_data_id]

    page = await get_url_data_paginated(
        bunkers_data_ids=bunkers_data_ids,
        filters=filters,
    )
    enriched_rows = []
    for row in page.data:
        bunkers_data = await get_bunkers_data(account_id.id, row.bunkers_data_id)
        if bunkers_data:
            enriched_rows.append(enrich_url_data(row, bunkers_data))
    return Page(data=enriched_rows, total=page.total)


@nostr_bunker_api_router.get(
    "/api/v1/url_data/{url_data_id}",
    name="Get Url Data",
    summary="Get the url data with this id.",
    response_description="An url data or 404 if not found",
    response_model=UrlData,
)
async def api_get_url_data(
    url_data_id: str,
    account_id: AccountId = Depends(check_account_id_exists),
) -> UrlData:

    url_data = await get_url_data_by_id(url_data_id)
    if not url_data:
        raise HTTPException(HTTPStatus.NOT_FOUND, "UrlData not found.")
    bunkers_data = await get_bunkers_data(account_id.id, url_data.bunkers_data_id)
    if not bunkers_data:
        raise HTTPException(HTTPStatus.NOT_FOUND, "Bunkers Data deleted for this Url Data.")

    return enrich_url_data(url_data, bunkers_data)


@nostr_bunker_api_router.delete(
    "/api/v1/url_data/{url_data_id}",
    name="Delete Url Data",
    summary="Delete the url_data",
    response_description="The status of the deletion.",
    response_model=SimpleStatus,
)
async def api_delete_url_data(
    url_data_id: str,
    account_id: AccountId = Depends(check_account_id_exists),
) -> SimpleStatus:

    url_data = await get_url_data_by_id(url_data_id)
    if not url_data:
        raise HTTPException(HTTPStatus.NOT_FOUND, "UrlData not found.")
    bunkers_data = await get_bunkers_data(account_id.id, url_data.bunkers_data_id)
    if not bunkers_data:
        raise HTTPException(HTTPStatus.NOT_FOUND, "Bunkers Data deleted for this Url Data.")

    await delete_url_data(bunkers_data.id, url_data_id)
    mark_runtime_state_dirty()
    return SimpleStatus(success=True, message="Url Data Deleted")


############################ Signing Requests ############################
@nostr_bunker_api_router.post(
    "/api/v1/signing_requests/{url_data_id}",
    name="Create Signing Request",
    summary="Create a pending signing request for a bunker URL.",
    response_description="The created signing request.",
    response_model=SigningRequest,
    status_code=HTTPStatus.CREATED,
)
async def api_create_signing_request(
    url_data_id: str,
    data: CreateSigningRequest,
    account_id: AccountId = Depends(check_account_id_exists),
) -> SigningRequest:
    url_data = await get_url_data_by_id(url_data_id)
    if not url_data:
        raise HTTPException(HTTPStatus.NOT_FOUND, "Url Data not found.")
    bunkers_data = await get_bunkers_data(account_id.id, url_data.bunkers_data_id)
    if not bunkers_data:
        raise HTTPException(HTTPStatus.NOT_FOUND, "Bunkers Data not found.")

    return await create_signing_request(url_data_id, data)


@nostr_bunker_api_router.get(
    "/api/v1/signing_requests/paginated",
    name="Signing Request List",
    summary="get paginated list of signing_requests",
    response_description="list of signing_requests",
    openapi_extra=generate_filter_params_openapi(SigningRequestFilters),
    response_model=Page[SigningRequest],
)
async def api_get_signing_requests_paginated(
    account_id: AccountId = Depends(check_account_id_exists),
    url_data_id: str | None = None,
    filters: Filters = Depends(signing_request_filters),
) -> Page[SigningRequest]:

    bunkers_data_ids = await get_bunkers_data_ids_by_user(account_id.id)
    url_data_ids = await get_url_data_ids_by_bunkers_data_ids(bunkers_data_ids)

    if url_data_id:
        if url_data_id not in url_data_ids:
            raise HTTPException(HTTPStatus.FORBIDDEN, "Not your url data.")
        url_data_ids = [url_data_id]

    return await get_signing_requests_paginated(
        url_data_ids=url_data_ids,
        filters=filters,
    )


@nostr_bunker_api_router.get(
    "/api/v1/signing_requests/{signing_request_id}",
    name="Get Signing Request",
    summary="Get the signing request with this id.",
    response_description="A signing request or 404 if not found",
    response_model=SigningRequest,
)
async def api_get_signing_request(
    signing_request_id: str,
    account_id: AccountId = Depends(check_account_id_exists),
) -> SigningRequest:

    signing_request = await get_signing_request_by_id(signing_request_id)
    if not signing_request:
        raise HTTPException(HTTPStatus.NOT_FOUND, "SigningRequest not found.")
    url_data = await get_url_data_by_id(signing_request.url_data_id)
    if not url_data:
        raise HTTPException(HTTPStatus.NOT_FOUND, "Url Data not found.")
    bunkers_data = await get_bunkers_data(account_id.id, url_data.bunkers_data_id)
    if not bunkers_data:
        raise HTTPException(HTTPStatus.NOT_FOUND, "Bunkers Data not found.")

    return signing_request


@nostr_bunker_api_router.put(
    "/api/v1/signing_requests/{signing_request_id}",
    name="Update Signing Request",
    summary="Update the signing request status.",
    response_description="The updated signing request.",
    response_model=SigningRequest,
)
async def api_update_signing_request(
    signing_request_id: str,
    data: UpdateSigningRequest,
    account_id: AccountId = Depends(check_account_id_exists),
) -> SigningRequest:
    signing_request = await api_get_signing_request(signing_request_id, account_id)
    if data.status.lower() in {"approved", "signed", "rejected", "error"}:
        return await complete_signing_request_action(
            signing_request.id,
            data.status,
            error_message=data.error,
        )
    return await update_signing_request(signing_request, data)


@nostr_bunker_api_router.delete(
    "/api/v1/signing_requests/{signing_request_id}",
    name="Delete Signing Request",
    summary="Delete the signing request.",
    response_description="The status of the deletion.",
    response_model=SimpleStatus,
)
async def api_delete_signing_request(
    signing_request_id: str,
    account_id: AccountId = Depends(check_account_id_exists),
) -> SimpleStatus:

    signing_request = await api_get_signing_request(signing_request_id, account_id)
    await delete_signing_request(signing_request.url_data_id, signing_request_id)
    return SimpleStatus(success=True, message="Signing Request Deleted")
