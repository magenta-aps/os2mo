#!/usr/bin/env python3
# --------------------------------------------------------------------------------------
# SPDX-FileCopyrightText: 2021 Magenta ApS <https://magenta.dk>
# SPDX-License-Identifier: MPL-2.0
# --------------------------------------------------------------------------------------
# --------------------------------------------------------------------------------------
# Imports
# --------------------------------------------------------------------------------------
from typing import Literal
from typing import Optional
from uuid import UUID

from pydantic import Field

from .._shared import EmployeeRef
from .._shared import ITSystemRef
from .._shared import MOBase
from .._shared import OrgUnitRef
from .._shared import PersonRef
from .._shared import Validity
from ._shared import Details

# --------------------------------------------------------------------------------------
# IT Systems
# --------------------------------------------------------------------------------------


class ITSystemRead(MOBase):
    """Payload model for IT systems."""

    type_: str = Field("itsystem", alias="type", description="The object type")
    name: str = Field(description="Name/titel of the itsystem.")
    user_key: str = Field(description="Short, unique key.")
    system_type: Optional[str] = Field(description="The ITSystem type.")


# --------------------------------------------------------------------------------------
# IT Users
# --------------------------------------------------------------------------------------


class ITUserBase(MOBase):
    """A MO IT user object."""

    type_: str = Field("it", alias="type", description="The object type.")
    validity: Validity = Field(description="Validity of the IT user object.")


class ITUserRead(ITUserBase):
    """A MO IT user read object."""

    itsystem_uuid: UUID = Field(description="UUID of the ITSystem related to the user.")
    employee_uuid: Optional[UUID] = Field(
        description="UUID of the employee related to the user."
    )
    org_unit_uuid: Optional[UUID] = Field(
        description="UUID organisation unit related to the user."
    )
    primary_uuid: Optional[UUID] = Field(
        description="UUID of an associated `primary_type` class."
    )


class ITUserWrite(ITUserBase):
    """A MO IT user write object."""

    itsystem: ITSystemRef = Field(
        description="Reference to the IT system for the IT user."
    )
    employee: Optional[EmployeeRef] = Field(
        description="Reference to the employee for the IT user."
    )
    org_unit: Optional[OrgUnitRef] = Field(
        description="Reference to the organisation unit for the IT user."
    )


class ITUserDetail(ITUserWrite, Details):
    pass


class ITUser(MOBase):
    type_: Literal["it"] = Field("it", alias="type", description="The object type.")
    user_key: str = Field(description="The IT user account name.")
    itsystem: ITSystemRef = Field(
        description="Reference to the IT system for the IT user."
    )
    person: Optional[PersonRef] = Field(
        description="Reference to the person for the IT user."
    )
    org_unit: Optional[OrgUnitRef] = Field(
        description="Reference to the organisation unit for the IT user."
    )
    validity: Validity = Field(description="Validity of the created IT user object.")

    @classmethod
    def from_simplified_fields(
        cls,
        user_key: str,
        itsystem_uuid: UUID,
        from_date: str,
        uuid: Optional[UUID] = None,
        to_date: Optional[str] = None,
        person_uuid: Optional[UUID] = None,
        org_unit_uuid: Optional[UUID] = None,
    ) -> "ITUser":
        """Create an IT User from simplified fields."""
        it_system = ITSystemRef(uuid=itsystem_uuid)
        person = PersonRef(uuid=person_uuid) if person_uuid else None
        org_unit = OrgUnitRef(uuid=org_unit_uuid) if org_unit_uuid else None
        validity = Validity(from_date=from_date, to_date=to_date)

        return cls(
            uuid=uuid,
            user_key=user_key,
            itsystem=it_system,
            person=person,
            org_unit=org_unit,
            validity=validity,
        )