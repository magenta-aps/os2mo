# SPDX-FileCopyrightText: Magenta ApS <https://magenta.dk>
# SPDX-License-Identifier: MPL-2.0
import os
from operator import attrgetter

from fastapi import APIRouter
from fastapi.responses import RedirectResponse
from jinja2 import Environment
from jinja2 import FileSystemLoader
from structlog import get_logger

from oio_rest import klassifikation
from oio_rest import organisation

logger = get_logger()

current_directory = os.path.dirname(os.path.realpath(__file__))

jinja_env = Environment(
    loader=FileSystemLoader(os.path.join(current_directory, "templates", "html"))
)


# MARK: can delete
def create_lora_router():
    router = APIRouter()

    # MARK: can delete
    @router.get("/", tags=["Meta"])
    async def root():  # pragma: no cover
        return RedirectResponse(router.url_path_for("sitemap"))

    # MARK: can delete (Casper says "nuke it")
    @router.get("/site-map", tags=["Meta"])
    async def sitemap():  # pragma: no cover
        """Returns a site map over all valid urls.

        .. :quickref: :http:get:`/site-map`

        """
        links = router.routes
        links = filter(lambda route: "GET" in route.methods, links)
        links = map(attrgetter("path"), links)
        return {"site-map": sorted(links)}

    # MARK: can delete
    router.include_router(
        klassifikation.KlassifikationsHierarki.setup_api(),
        tags=["Klassifikation"],
    )

    # MARK: can delete
    router.include_router(
        organisation.OrganisationsHierarki.setup_api(),
        tags=["Organisation"],
    )

    return router
