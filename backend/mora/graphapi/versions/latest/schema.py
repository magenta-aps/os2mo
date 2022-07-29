# SPDX-FileCopyrightText: 2021 Magenta ApS <https://magenta.dk>
# SPDX-License-Identifier: MPL-2.0
"""Strawberry types describing the MO graph."""
import asyncio
import json
import re
from base64 import b64encode
from typing import Any
from typing import cast
from typing import Generic
from typing import Optional
from typing import TypeVar
from uuid import UUID

import strawberry
from fastapi.encoders import jsonable_encoder
from more_itertools import one
from more_itertools import only
from ramodels.mo import ClassRead
from ramodels.mo import EmployeeRead
from ramodels.mo import FacetRead
from ramodels.mo import OrganisationRead
from ramodels.mo import OrganisationUnitRead
from ramodels.mo._shared import DynamicClasses as DynamicClassesRead
from ramodels.mo._shared import OpenValidity as OpenValidityModel
from ramodels.mo._shared import Validity as ValidityModel
from ramodels.mo.details import AddressRead
from ramodels.mo.details import AssociationRead
from ramodels.mo.details import EngagementAssociationRead
from ramodels.mo.details import EngagementRead
from ramodels.mo.details import ITSystemRead
from ramodels.mo.details import ITUserRead
from ramodels.mo.details import KLERead
from ramodels.mo.details import LeaveRead
from ramodels.mo.details import ManagerRead
from ramodels.mo.details import RelatedUnitRead
from ramodels.mo.details import RoleRead
from starlette_context import context
from strawberry.dataloader import DataLoader
from strawberry.types import Info

from mora import common
from mora import config
from mora import lora
from mora.service.address_handler import dar
from mora.service.address_handler import multifield_text
from mora.service.facet import is_class_uuid_primary
from .files import load_file
from .health import health_map
from .models import ConfigurationRead
from .models import FileRead
from .models import HealthRead
from .models import OrganisationUnitRefreshRead

MOObject = TypeVar("MOObject")


@strawberry.type
class Response(Generic[MOObject]):
    uuid: UUID
    objects: list[MOObject]


# Validities
# ----------


@strawberry.experimental.pydantic.type(
    model=ValidityModel,
    all_fields=True,
    description="Validity of objects with required from date",
)
class Validity:
    pass


@strawberry.experimental.pydantic.type(
    model=OpenValidityModel,
    all_fields=True,
    description="Validity of objects with optional from date",
)
class OpenValidity:
    pass


# Address
# -------


@strawberry.experimental.pydantic.type(
    model=AddressRead,
    all_fields=True,
    description="Address information for an employee or organisation unit",
)
class Address:
    @strawberry.field(description="Address type")
    async def address_type(self, root: AddressRead, info: Info) -> "Class":
        loader: DataLoader = info.context["class_loader"]
        return await loader.load(root.address_type_uuid)

    @strawberry.field(description="Address visibility")
    async def visibility(self, root: AddressRead, info: Info) -> Optional["Class"]:
        loader: DataLoader = info.context["class_loader"]
        if root.visibility_uuid is None:
            return None
        return await loader.load(root.visibility_uuid)

    @strawberry.field(
        description="Connected employee. "
        "Note that this is mutually exclusive with the org_unit field"
    )
    async def employee(
        self, root: AddressRead, info: Info
    ) -> Optional[list["Employee"]]:
        loader: DataLoader = info.context["employee_loader"]
        if root.employee_uuid is None:
            return None
        return (await loader.load(root.employee_uuid)).objects

    @strawberry.field(
        description="Connected organisation unit. "
        "Note that this is mutually exclusive with the employee field"
    )
    async def org_unit(
        self, root: AddressRead, info: Info
    ) -> Optional[list["OrganisationUnit"]]:
        loader: DataLoader = info.context["org_unit_loader"]
        if root.org_unit_uuid is None:
            return None
        return (await loader.load(root.org_unit_uuid)).objects

    @strawberry.field(description="Name of address")
    async def name(self, root: AddressRead, info: Info) -> Optional[str]:
        address_type = await Address.address_type(self, root, info)

        if address_type.scope == "MULTIFIELD_TEXT":
            return multifield_text.name(root.value, root.value2)

        if address_type.scope == "DAR":
            dar_loader = context["dar_loader"]
            address_object = await dar_loader.load(UUID(root.value))
            return dar.name_from_dar_object(address_object)

        return root.value

    @strawberry.field(description="href of address")
    async def href(self, root: AddressRead, info: Info) -> Optional[str]:
        address_type = await Address.address_type(self, root, info)

        if address_type.scope == "PHONE":
            return f"tel:{root.value}"

        if address_type.scope == "EMAIL":
            return f"mailto:{root.value}"

        if address_type.scope == "DAR":
            dar_loader = context["dar_loader"]
            address_object = await dar_loader.load(UUID(root.value))
            if address_object is None:
                return None
            return dar.open_street_map_href_from_dar_object(address_object)

        return None


async def filter_address_types(
    addresses: list[AddressRead], address_types: Optional[list[UUID]]
) -> list[AddressRead]:
    """Filter a list of addresses based on their address type UUID.

    Args:
        addresses: The addresses to filter
        address_types: The address type UUIDs to filter by.

    Returns:
        list[AddressRead]: Addresses optionally filtered by their address type.
    """
    if address_types is None:
        return addresses
    address_type_list: list[UUID] = address_types
    return list(
        filter(lambda addr: addr.address_type_uuid in address_type_list, addresses)
    )


# Association
# -----------


@strawberry.experimental.pydantic.type(
    model=DynamicClassesRead,
    all_fields=True,
    description="Dynamic class overload for associations",
)
class DynamicClasses:
    pass


@strawberry.experimental.pydantic.type(
    model=AssociationRead,
    all_fields=True,
    description="Connects organisation units and employees",
)
class Association:
    @strawberry.field(description="Association type")
    async def association_type(
        self, root: AssociationRead, info: Info
    ) -> Optional["Class"]:
        loader: DataLoader = info.context["class_loader"]
        if root.association_type_uuid:
            return await loader.load(root.association_type_uuid)
        else:
            return None

    @strawberry.field(description="Primary status")
    async def primary(self, root: AssociationRead, info: Info) -> Optional["Class"]:
        loader: DataLoader = info.context["class_loader"]
        if root.primary_uuid is None:
            return None
        return await loader.load(root.primary_uuid)

    @strawberry.field(description="Connected employee")
    async def employee(self, root: AssociationRead, info: Info) -> list["Employee"]:
        loader: DataLoader = info.context["employee_loader"]
        return (await loader.load(root.employee_uuid)).objects

    @strawberry.field(description="Connected organisation unit")
    async def org_unit(
        self, root: AssociationRead, info: Info
    ) -> list["OrganisationUnit"]:
        loader: DataLoader = info.context["org_unit_loader"]
        return (await loader.load(root.org_unit_uuid)).objects

    @strawberry.field(description="Connected substitute employee")
    async def substitute(self, root: AssociationRead, info: Info) -> list["Employee"]:
        loader: DataLoader = info.context["employee_loader"]
        if root.substitute_uuid:
            return (await loader.load(root.substitute_uuid)).objects
        else:
            return []

    @strawberry.field(description="Connected job function")
    async def job_function(
        self, root: AssociationRead, info: Info
    ) -> Optional["Class"]:
        loader: DataLoader = info.context["class_loader"]
        if root.job_function_uuid:
            return await loader.load(root.job_function_uuid)
        else:
            return None

    @strawberry.field(description="Connected IT user")
    async def it_user(self, root: AssociationRead, info: Info) -> list["ITUser"]:
        loader: DataLoader = info.context["ituser_loader"]
        if root.it_user_uuid:
            return (await loader.load(root.it_user_uuid)).objects
        else:
            return []


# Class
# -----


@strawberry.experimental.pydantic.type(
    model=ClassRead,
    all_fields=True,
    description="The value component of the class/facet choice setup",
)
class Class:
    @strawberry.field(description="Immediate parent class")
    async def parent(self, root: ClassRead, info: Info) -> Optional["Class"]:
        """Get the immediate parent class.

        Returns:
            Class: Parent class
        """
        loader: DataLoader = info.context["class_loader"]
        if root.parent_uuid is None:
            return None

        return await loader.load(root.parent_uuid)

    @strawberry.field(description="Immediate descendants of the class")
    async def children(self, root: ClassRead, info: Info) -> list["Class"]:
        """Get the immediate descendants of the class.

        Returns:
            list[Class]: list of descendants, if any.
        """
        loader: DataLoader = info.context["class_children_loader"]
        if not isinstance(root.uuid, UUID):  # TODO: What? We never reach this
            root.parent_uuid = UUID(root.uuid)  # but why?
        return await loader.load(root.uuid)

    @strawberry.field(description="Associated facet")
    async def facet(self, root: ClassRead, info: Info) -> "Facet":
        """Get the associated facet.

        Returns:
            The associated facet.
        """
        loader: DataLoader = info.context["facet_loader"]
        return await loader.load(root.facet_uuid)

    @strawberry.field(description="Associated top-level facet")
    async def top_level_facet(self, root: ClassRead, info: Info) -> "Facet":
        parent: ClassRead = root

        # Traverse class tree
        loader: DataLoader = info.context["class_loader"]
        while parent.parent_uuid is not None:
            parent = await loader.load(parent.parent_uuid)

        return await info.context["facet_loader"].load(parent.facet_uuid)

    @strawberry.field(description="Full name, for backwards compatibility")
    async def full_name(self, root: ClassRead) -> str:
        return root.name


# Employee
# --------


@strawberry.experimental.pydantic.type(
    model=EmployeeRead,
    all_fields=True,
    description="Employee/identity specific information",
)
class Employee:
    @strawberry.field(description="Full name of the employee")
    async def name(self, root: EmployeeRead) -> str:
        return f"{root.givenname} {root.surname}".strip()

    @strawberry.field(description="Full nickname of the employee")
    async def nickname(self, root: EmployeeRead) -> str:
        return f"{root.nickname_givenname} {root.nickname_surname}".strip()

    @strawberry.field(description="Engagements for the employee")
    async def engagements(self, root: EmployeeRead, info: Info) -> list["Engagement"]:
        loader: DataLoader = info.context["employee_engagement_loader"]
        return await loader.load(root.uuid)

    @strawberry.field(description="Manager roles for the employee")
    async def manager_roles(self, root: EmployeeRead, info: Info) -> list["Manager"]:
        loader: DataLoader = info.context["employee_manager_role_loader"]
        return await loader.load(root.uuid)

    @strawberry.field(description="Addresses for the employee")
    async def addresses(
        self,
        root: EmployeeRead,
        info: Info,
        address_types: Optional[list[UUID]] = None,
    ) -> list["Address"]:
        loader: DataLoader = info.context["employee_address_loader"]
        result = await loader.load(root.uuid)
        address_reads = await filter_address_types(result, address_types)
        return list(map(Address.from_pydantic, address_reads))

    @strawberry.field(description="Leaves for the employee")
    async def leaves(self, root: EmployeeRead, info: Info) -> list["Leave"]:
        loader: DataLoader = info.context["employee_leave_loader"]
        return await loader.load(root.uuid)

    @strawberry.field(description="Associations for the employee")
    async def associations(self, root: EmployeeRead, info: Info) -> list["Association"]:
        loader: DataLoader = info.context["employee_association_loader"]
        return await loader.load(root.uuid)

    @strawberry.field(description="Roles for the employee")
    async def roles(self, root: EmployeeRead, info: Info) -> list["Role"]:
        loader: DataLoader = info.context["employee_role_loader"]
        return await loader.load(root.uuid)

    @strawberry.field(description="IT users for the employee")
    async def itusers(self, root: EmployeeRead, info: Info) -> list["ITUser"]:
        loader: DataLoader = info.context["employee_ituser_loader"]
        return await loader.load(root.uuid)

    @strawberry.field(description="Engagement associations")
    async def engagement_associations(
        self, root: EmployeeRead, info: Info
    ) -> list["EngagementAssociation"]:
        loader: DataLoader = info.context["employee_engagement_association_loader"]
        return await loader.load(root.uuid)


# Engagement
# ----------


@strawberry.experimental.pydantic.type(
    model=EngagementRead,
    all_fields=True,
    description="Employee engagement in an organisation unit",
)
class Engagement:
    @strawberry.field(description="Engagement type")
    async def engagement_type(self, root: EngagementRead, info: Info) -> "Class":
        loader: DataLoader = info.context["class_loader"]
        return await loader.load(root.engagement_type_uuid)

    @strawberry.field(description="Job function")
    async def job_function(self, root: EngagementRead, info: Info) -> "Class":
        loader: DataLoader = info.context["class_loader"]
        return await loader.load(root.job_function_uuid)

    @strawberry.field(description="The primary status")
    async def primary(self, root: EngagementRead, info: Info) -> Optional["Class"]:
        loader: DataLoader = info.context["class_loader"]
        if root.primary_uuid is None:
            return None
        return await loader.load(root.primary_uuid)

    @strawberry.field(description="Is it primary")
    async def is_primary(self, root: EngagementRead, info: Info) -> bool:
        if not root.primary_uuid:
            return False
        return await is_class_uuid_primary(str(root.primary_uuid))

    @strawberry.field(description="Related leave")
    async def leave(self, root: EngagementRead, info: Info) -> Optional["Leave"]:
        loader: DataLoader = info.context["leave_loader"]
        if root.leave_uuid is None:
            return None
        return await loader.load(root.leave_uuid)

    @strawberry.field(description="Related employee")
    async def employee(self, root: EngagementRead, info: Info) -> list["Employee"]:
        loader: DataLoader = info.context["employee_loader"]
        return (await loader.load(root.employee_uuid)).objects

    @strawberry.field(description="Related organisation unit")
    async def org_unit(
        self, root: EngagementRead, info: Info
    ) -> list["OrganisationUnit"]:
        loader: DataLoader = info.context["org_unit_loader"]
        return (await loader.load(root.org_unit_uuid)).objects

    @strawberry.field(description="Engagement associations")
    async def engagement_associations(
        self, root: EngagementRead, info: Info
    ) -> list["EngagementAssociation"]:
        loader: DataLoader = info.context["engagement_engagement_association_loader"]
        return await loader.load(root.uuid)


# Engagement Association
# ----------


@strawberry.experimental.pydantic.type(
    model=EngagementAssociationRead,
    all_fields=True,
    description="Employee engagement in an organisation unit",
)
class EngagementAssociation:
    @strawberry.field(description="Related organisation unit")
    async def org_unit(
        self, root: EngagementAssociationRead, info: Info
    ) -> list["OrganisationUnit"]:
        loader: DataLoader = info.context["org_unit_loader"]
        return (await loader.load(root.org_unit_uuid)).objects

    @strawberry.field(description="Related engagement")
    async def engagement(
        self, root: EngagementAssociationRead, info: Info
    ) -> list["Engagement"]:
        loader: DataLoader = info.context["engagement_loader"]
        return (await loader.load(root.engagement_uuid)).objects

    @strawberry.field(description="Related engagement association type")
    async def engagement_association_type(
        self, root: EngagementAssociationRead, info: Info
    ) -> "Class":
        loader: DataLoader = info.context["class_loader"]
        return await loader.load(root.engagement_association_type_uuid)


# Facet
# -----


@strawberry.experimental.pydantic.type(
    model=FacetRead,
    all_fields=True,
    description="The key component of the class/facet choice setup",
)
class Facet:
    @strawberry.field(description="Associated classes")
    async def classes(self, root: FacetRead, info: Info) -> list["Class"]:
        """Get the associated classes.

        Returns:
            The associated classes.
        """
        loader: DataLoader = info.context["facet_classes_loader"]
        return await loader.load(root.uuid)


# IT
# --


@strawberry.experimental.pydantic.type(
    model=ITSystemRead,
    all_fields=True,
    description="Systems that IT users are connected to",
)
class ITSystem:
    pass


@strawberry.experimental.pydantic.type(
    model=ITUserRead,
    all_fields=True,
    description="User information related to IT systems",
)
class ITUser:
    @strawberry.field(description="Connected employee")
    async def employee(
        self, root: ITUserRead, info: Info
    ) -> Optional[list["Employee"]]:
        loader: DataLoader = info.context["employee_loader"]
        if root.employee_uuid is None:
            return None
        return (await loader.load(root.employee_uuid)).objects

    @strawberry.field(description="Connected organisation unit")
    async def org_unit(
        self, root: ITUserRead, info: Info
    ) -> Optional[list["OrganisationUnit"]]:
        loader: DataLoader = info.context["org_unit_loader"]
        if root.org_unit_uuid is None:
            return None
        return (await loader.load(root.org_unit_uuid)).objects


# KLE
# ---


@strawberry.experimental.pydantic.type(
    model=KLERead,
    all_fields=True,
    description="Kommunernes Landsforenings Emnesystematik",
)
class KLE:
    @strawberry.field(description="KLE number")
    async def kle_number(self, root: KLERead, info: Info) -> "Class":
        loader: DataLoader = info.context["class_loader"]
        return await loader.load(root.kle_number_uuid)

    @strawberry.field(description="KLE Aspects")
    async def kle_aspects(self, root: KLERead, info: Info) -> list["Class"]:
        loader: DataLoader = info.context["class_loader"]
        return await loader.load_many(root.kle_aspect_uuids)

    @strawberry.field(description="Associated organisation unit")
    async def org_unit(
        self, root: KLERead, info: Info
    ) -> Optional[list["OrganisationUnit"]]:
        loader: DataLoader = info.context["org_unit_loader"]
        if root.org_unit_uuid is None:
            return None
        return (await loader.load(root.org_unit_uuid)).objects


# Leave
# -----


@strawberry.experimental.pydantic.type(
    model=LeaveRead,
    all_fields=True,
    description="Leave (e.g. parental leave) for employees",
)
class Leave:
    @strawberry.field(description="Leave type")
    async def leave_type(self, root: LeaveRead, info: Info) -> "Class":
        loader: DataLoader = info.context["class_loader"]
        return await loader.load(root.leave_type_uuid)

    @strawberry.field(description="Related employee")
    async def employee(self, root: LeaveRead, info: Info) -> list["Employee"]:
        loader: DataLoader = info.context["employee_loader"]
        return (await loader.load(root.employee_uuid)).objects

    @strawberry.field(description="Related engagement")
    async def engagement(self, root: LeaveRead, info: Info) -> Optional["Engagement"]:
        loader: DataLoader = info.context["engagement_loader"]
        if root.engagement_uuid is None:
            return None
        engagement = await loader.load(root.engagement_uuid)
        return only(engagement.objects)


# Manager
# -------


@strawberry.experimental.pydantic.type(
    model=ManagerRead,
    all_fields=True,
    description="Managers of organisation units and their connected identities",
)
class Manager:
    @strawberry.field(description="Manager type")
    async def manager_type(self, root: ManagerRead, info: Info) -> Optional["Class"]:
        loader: DataLoader = info.context["class_loader"]
        if root.manager_type_uuid is None:
            return None
        return await loader.load(root.manager_type_uuid)

    @strawberry.field(description="Manager level")
    async def manager_level(self, root: ManagerRead, info: Info) -> Optional["Class"]:
        loader: DataLoader = info.context["class_loader"]
        if root.manager_level_uuid is None:
            return None
        return await loader.load(root.manager_level_uuid)

    @strawberry.field(description="Manager responsibilities")
    async def responsibilities(self, root: ManagerRead, info: Info) -> list["Class"]:
        loader: DataLoader = info.context["class_loader"]
        if root.responsibility_uuids is None:
            return []
        return await loader.load_many(root.responsibility_uuids)

    @strawberry.field(description="Manager identity details")
    async def employee(
        self, root: ManagerRead, info: Info
    ) -> Optional[list["Employee"]]:
        loader: DataLoader = info.context["employee_loader"]
        if root.employee_uuid is None:
            return None
        return (await loader.load(root.employee_uuid)).objects

    @strawberry.field(description="Managed organisation unit")
    async def org_unit(self, root: ManagerRead, info: Info) -> list["OrganisationUnit"]:
        loader: DataLoader = info.context["org_unit_loader"]
        return (await loader.load(root.org_unit_uuid)).objects


# Organisation
# ------------


MUNICIPALITY_CODE_PATTERN = re.compile(r"urn:dk:kommune:(\d+)")


@strawberry.experimental.pydantic.type(
    model=OrganisationRead,
    all_fields=True,
    description="Root organisation - one and only one of these can exist",
)
class Organisation:
    @strawberry.field(description="The municipality code for the organisation unit")
    async def municipality_code(
        self, root: OrganisationUnitRead, info: Info
    ) -> Optional[int]:
        """Get The municipality code for the organisation unit (if any).

        Returns:
            The municipality code, if any is found.
        """
        org = await common.get_connector().organisation.get(root.uuid)

        authorities = org.get("relationer", {}).get("myndighed", [])
        for authority in authorities:
            m = MUNICIPALITY_CODE_PATTERN.fullmatch(authority.get("urn"))
            if m:
                return int(m.group(1))
        return None


# Organisation Unit
# -----------------


@strawberry.experimental.pydantic.type(
    model=OrganisationUnitRead,
    all_fields=True,
    description="Hierarchical unit within the organisation tree",
)
class OrganisationUnit:
    @strawberry.field(description="The immediate ancestor in the organisation tree")
    async def parent(
        self, root: OrganisationUnitRead, info: Info
    ) -> Optional[list["OrganisationUnit"]]:
        """Get the immediate ancestor in the organisation tree.

        Returns:
            Optional[list[OrganisationUnit]]: The ancestor(s), if any.
        """
        loader: DataLoader = info.context["org_unit_loader"]
        if root.parent_uuid is None:
            return None
        return (await loader.load(root.parent_uuid)).objects

    @strawberry.field(description="The immediate descendants in the organisation tree")
    async def children(
        self, root: OrganisationUnitRead, info: Info
    ) -> list["OrganisationUnit"]:
        """Get the immediate descendants of the organistion unit.

        Returns:
            list[OrganisationUnit]: list of descendants, if any.
        """
        loader: DataLoader = info.context["org_unit_children_loader"]
        return await loader.load(root.uuid)

    @strawberry.field(description="Children count of the organisation unit.")
    async def child_count(self, root: OrganisationUnitRead, info: Info) -> int:
        loader: DataLoader = info.context["org_unit_children_loader"]
        return len(await loader.load(root.uuid))

    # TODO: Add UUID to RAModel and remove model prefix here
    @strawberry.field(description="Organisation unit hierarchy")
    async def org_unit_hierarchy_model(
        self, root: OrganisationUnitRead, info: Info
    ) -> Optional["Class"]:
        loader: DataLoader = info.context["class_loader"]
        if root.org_unit_hierarchy is None:
            return None
        return await loader.load(root.org_unit_hierarchy)

    @strawberry.field(description="Organisation unit type")
    async def unit_type(
        self, root: OrganisationUnitRead, info: Info
    ) -> Optional["Class"]:
        loader: DataLoader = info.context["class_loader"]
        if root.unit_type_uuid is None:
            return None
        return await loader.load(root.unit_type_uuid)

    # TODO: Remove org prefix from RAModel and remove it here too
    @strawberry.field(description="Organisation unit level")
    async def org_unit_level(
        self, root: OrganisationUnitRead, info: Info
    ) -> Optional["Class"]:
        loader: DataLoader = info.context["class_loader"]
        if root.org_unit_level_uuid is None:
            return None
        return await loader.load(root.org_unit_level_uuid)

    @strawberry.field(description="Time planning strategy")
    async def time_planning(
        self, root: OrganisationUnitRead, info: Info
    ) -> Optional["Class"]:
        loader: DataLoader = info.context["class_loader"]
        if root.time_planning_uuid is None:
            return None
        return await loader.load(root.time_planning_uuid)

    @strawberry.field(description="Related engagements")
    async def engagements(
        self, root: OrganisationUnitRead, info: Info
    ) -> list["Engagement"]:
        loader: DataLoader = info.context["org_unit_engagement_loader"]
        return await loader.load(root.uuid)

    @strawberry.field(description="Managers of the organisation unit")
    async def managers(
        self, root: OrganisationUnitRead, info: Info, inherit: bool = False
    ) -> list["Manager"]:
        loader: DataLoader = info.context["org_unit_manager_loader"]
        ou_loader: DataLoader = info.context["org_unit_loader"]
        result = await loader.load(root.uuid)
        if inherit:
            parent = root
            while not result:
                parent_uuid = parent.parent_uuid
                tasks = [loader.load(parent_uuid), ou_loader.load(parent_uuid)]
                result, response = await asyncio.gather(*tasks)
                potential_parent = only(response.objects, default=None)
                if potential_parent is None:
                    break
                parent = potential_parent
        return result

    @strawberry.field(description="Related addresses")
    async def addresses(
        self,
        root: OrganisationUnitRead,
        info: Info,
        address_types: Optional[list[UUID]] = None,
    ) -> list["Address"]:
        loader: DataLoader = info.context["org_unit_address_loader"]
        result = await loader.load(root.uuid)
        address_reads = await filter_address_types(result, address_types)
        return list(map(Address.from_pydantic, address_reads))

    @strawberry.field(description="Related leaves")
    async def leaves(self, root: OrganisationUnitRead, info: Info) -> list["Leave"]:
        loader: DataLoader = info.context["org_unit_leave_loader"]
        return await loader.load(root.uuid)

    @strawberry.field(description="Related associations")
    async def associations(
        self, root: OrganisationUnitRead, info: Info
    ) -> list["Association"]:
        loader: DataLoader = info.context["org_unit_association_loader"]
        return await loader.load(root.uuid)

    @strawberry.field(description="Related roles")
    async def roles(self, root: OrganisationUnitRead, info: Info) -> list["Role"]:
        loader: DataLoader = info.context["org_unit_role_loader"]
        return await loader.load(root.uuid)

    @strawberry.field(description="Related IT users")
    async def itusers(self, root: OrganisationUnitRead, info: Info) -> list["ITUser"]:
        loader: DataLoader = info.context["org_unit_ituser_loader"]
        return await loader.load(root.uuid)

    @strawberry.field(description="KLE responsibilites for the organisation unit")
    async def kles(self, root: OrganisationUnitRead, info: Info) -> list["KLE"]:
        loader: DataLoader = info.context["org_unit_kle_loader"]
        return await loader.load(root.uuid)

    @strawberry.field(description="Related units for the organisational unit")
    async def related_units(
        self, root: OrganisationUnitRead, info: Info
    ) -> list["RelatedUnit"]:
        loader: DataLoader = info.context["org_unit_related_unit_loader"]
        return await loader.load(root.uuid)

    @strawberry.field(description="Engagement associations for the organisational unit")
    async def engagement_associations(
        self, root: OrganisationUnitRead, info: Info
    ) -> list["EngagementAssociation"]:
        loader: DataLoader = info.context["org_unit_engagement_association_loader"]
        return await loader.load(root.uuid)


# Related Unit
# ------------


@strawberry.experimental.pydantic.type(
    model=RelatedUnitRead,
    all_fields=True,
    description="list of related organisation units",
)
class RelatedUnit:
    @strawberry.field(description="Related organisation units")
    async def org_units(
        self, root: RelatedUnitRead, info: Info
    ) -> list["OrganisationUnit"]:
        loader: DataLoader = info.context["org_unit_loader"]
        results = await loader.load_many(root.org_unit_uuids)
        return [one(result.objects) for result in results]


# Role
# ----
@strawberry.experimental.pydantic.type(
    model=RoleRead,
    all_fields=True,
    description="Role an employee has within an organisation unit",
)
class Role:
    @strawberry.field(description="Role type")
    async def role_type(self, root: RoleRead, info: Info) -> "Class":
        loader: DataLoader = info.context["class_loader"]
        return await loader.load(root.role_type_uuid)

    @strawberry.field(description="Connected employee")
    async def employee(self, root: RoleRead, info: Info) -> list["Employee"]:
        loader: DataLoader = info.context["employee_loader"]
        return (await loader.load(root.employee_uuid)).objects

    @strawberry.field(description="Connected organisation unit")
    async def org_unit(self, root: RoleRead, info: Info) -> list["OrganisationUnit"]:
        loader: DataLoader = info.context["org_unit_loader"]
        return (await loader.load(root.org_unit_uuid)).objects


# Health & version
# ----------------
@strawberry.type(description="MO & LoRa versions")
class Version:
    @strawberry.field(description="OS2mo Version")
    async def mo_version(self) -> Optional[str]:
        """Get the mo version.

        Returns:
            The version.
        """
        return config.get_settings().commit_tag

    @strawberry.field(description="OS2mo commit hash")
    async def mo_hash(self) -> Optional[str]:
        """Get the mo commit hash.

        Returns:
            The commit hash.
        """
        return config.get_settings().commit_sha

    @strawberry.field(description="LoRa version")
    async def lora_version(self) -> Optional[str]:
        """Get the lora version.

        Returns:
            The version.
        """
        return await lora.get_version()


@strawberry.experimental.pydantic.type(
    model=HealthRead,
    all_fields=True,
    description="Checks whether a specific subsystem is working",
)
class Health:
    @strawberry.field(description="Healthcheck status")
    async def status(self, root: HealthRead) -> Optional[bool]:
        return await health_map[root.identifier]()


# File
# ----
@strawberry.experimental.pydantic.type(
    model=FileRead,
    all_fields=True,
    description="Checks whether a specific subsystem is working",
)
class File:
    @strawberry.field(description="Text contents")
    def text_contents(self, root: FileRead) -> str:
        return cast(str, load_file(root.file_store, root.file_name))

    @strawberry.field(description="Base64 encoded contents")
    def base64_contents(self, root: FileRead) -> str:
        data = cast(bytes, load_file(root.file_store, root.file_name, binary=True))
        data = b64encode(data)
        return data.decode("ascii")


# Organisation Unit Refresh
# -------------------------
@strawberry.experimental.pydantic.type(
    model=OrganisationUnitRefreshRead,
    all_fields=True,
    description="Response model for Organisation Unit refresh event.",
)
class OrganisationUnitRefresh:
    pass


# Configuration
# -------------
def get_settings_value(key: str) -> Any:
    """Get the settings value.

    Args:
        key: The settings key.

    Returns:
        The settings value.
    """
    return getattr(config.get_settings(), key)


@strawberry.experimental.pydantic.type(
    model=ConfigurationRead,
    all_fields=True,
    description="A configuration setting",
)
class Configuration:
    @strawberry.field(description="JSONified value")
    def jsonified_value(self, root: ConfigurationRead) -> str:
        """Get the jsonified value.

        Returns:
            The value.
        """
        return json.dumps(jsonable_encoder(get_settings_value(root.key)))

    @strawberry.field(description="Stringified value")
    def stringified_value(self, root: ConfigurationRead) -> str:
        """Get the stringified value.

        Returns:
            The value.
        """
        return str(get_settings_value(root.key))