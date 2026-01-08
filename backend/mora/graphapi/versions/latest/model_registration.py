# SPDX-FileCopyrightText: Magenta ApS <https://magenta.dk>
# SPDX-License-Identifier: MPL-2.0
from datetime import datetime
from textwrap import dedent

# The below concrete classes are instantiated using `resolve_type` on the Registration
# interface within `registration.py`. Once the type is found a sanity check is performed
# by strawberry which validates that the instance being constructed is of the expected
# subtype, this is however not the case, as the instance is a SQLAlchemy Row instance
# produced by the registration_resolver and the expected type is a FacetRegistration
# for instance, thus the sanity check done by strawberry fails, and the mapping done by
# `resolve_type` is rejected. We know however that the implementation of `resolve_type`
# is trustworthy and that we simply wish to construct our FacetRegistration or similar
# using the SQLAlchemy row in our constructor, so we can safely return `True` within
# the base-class' `is_type_of` method to disable the sanity check and simply trust the
# decision made by `resolve_type`.
from typing import Any
from typing import Generic

import strawberry
from strawberry import UNSET
from strawberry import Info

from mora.graphapi.gmodels.mo import EmployeeRead
from mora.graphapi.gmodels.mo import OrganisationUnitRead
from mora.graphapi.gmodels.mo.details import AssociationRead
from mora.graphapi.gmodels.mo.details import EngagementRead
from mora.graphapi.gmodels.mo.details import ITSystemRead
from mora.graphapi.gmodels.mo.details import ITUserRead
from mora.graphapi.gmodels.mo.details import KLERead
from mora.graphapi.gmodels.mo.details import LeaveRead
from mora.graphapi.gmodels.mo.details import ManagerRead
from mora.graphapi.versions.latest.permissions import IsAuthenticatedPermission

from .models import AddressRead
from .models import ClassRead
from .models import FacetRead
from .models import RoleBindingRead
from .moobject import MOObject
from .registration import Registration


def name2model(name: str) -> Any:
    mapping = {
        "class": ClassRead,
        "employee": EmployeeRead,
        "facet": FacetRead,
        "org_unit": OrganisationUnitRead,
        "address": AddressRead,
        "association": AssociationRead,
        "engagement": EngagementRead,
        "itsystem": ITSystemRead,
        "ituser": ITUserRead,
        "kle": KLERead,
        "leave": LeaveRead,
        "rolebinding": RoleBindingRead,
        "manager": ManagerRead,
    }
    return mapping[name]


@strawberry.type
class ModelRegistration(Registration, Generic[MOObject]):
    @classmethod
    def is_type_of(cls, model: Registration, info: Info) -> bool:
        # We trust resolve_type made the right choice
        return True

    @strawberry.field(
        description=dedent(
            """\
            Actual / current state entrypoint.

            Returns the state of the object at current validity and current assertion time.

            A single object is returned as only one validity can be active at a given assertion time.

            Note:
            This the entrypoint is appropriate to use for actual-state integrations and UIs.
            """
        ),
        permission_classes=[IsAuthenticatedPermission],
    )
    async def current(
        self, root: "ModelRegistration", info: Info, at: datetime | None = UNSET
    ) -> MOObject | None:
        from .response import Response

        model_class = name2model(root.model)
        response = Response[MOObject](
            model=model_class, uuid=root.uuid, object_cache=None
        )
        return await response.current(
            root=response, info=info, at=at, registration_time=root.start
        )

    @strawberry.field(
        description=dedent(
            """\
            Actual / current state entrypoint.

            Returns the state of the object at current validity and current assertion time.

            A single object is returned as only one validity can be active at a given assertion time.

            Note:
            This the entrypoint is appropriate to use for actual-state integrations and UIs.
            """
        ),
        permission_classes=[IsAuthenticatedPermission],
    )
    async def validities(
        self,
        root: "ModelRegistration",
        info: Info,
        start: datetime | None = UNSET,
        end: datetime | None = UNSET,
    ) -> list[MOObject]:
        from .response import Response

        model_class = name2model(root.model)
        response = Response[MOObject](
            model=model_class, uuid=root.uuid, object_cache=None
        )
        return await response.validities(
            root=response, info=info, start=start, end=end, registration_time=root.start
        )
