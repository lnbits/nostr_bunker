# Description: Add your page endpoints here.


from fastapi import APIRouter, Depends
from lnbits.core.views.generic import index, index_public
from lnbits.decorators import check_account_exists
from lnbits.helpers import template_renderer

nostr_bunker_generic_router = APIRouter()


def nostr_bunker_renderer():
    return template_renderer(["nostr_bunker/templates"])


#######################################
##### ADD YOUR PAGE ENDPOINTS HERE ####
#######################################


# Backend admin page
nostr_bunker_generic_router.add_api_route(
    "/", methods=["GET"], endpoint=index, dependencies=[Depends(check_account_exists)]
)


# Frontend shareable page


