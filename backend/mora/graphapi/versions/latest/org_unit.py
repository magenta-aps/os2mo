# SPDX-FileCopyrightText: 2021 Magenta ApS <https://magenta.dk>
# SPDX-License-Identifier: MPL-2.0
"""GraphQL org-unit related helper functions."""
import datetime
import logging
from typing import cast
from uuid import UUID

from strawberry.dataloader import DataLoader

from .dataloaders import get_loaders
from .models import MoraTriggerRequest
from .models import OrganisationUnitTerminate
from .models import OrgUnitTrigger
from .models import Validity
from .schema import Response
from .types import OrganizationUnit
from mora import common
from mora import exceptions
from mora import lora
from mora import mapping
from mora import util
from mora.service.orgunit import OrgUnitRequestHandler
from mora.service.validation import validator
from mora.triggers import Trigger
from mora.util import ONE_DAY
from mora.util import POSITIVE_INFINITY

logger = logging.getLogger(__name__)


async def load_org_unit(uuid: UUID) -> Response:
    """Call the org_unit_loader on the given UUID.

    Args:
        uuid: The UUID to load from LoRa.

    Returns:
        The return from LoRa.
    """
    loaders = await get_loaders()
    org_unit_loader = cast(DataLoader, loaders["org_unit_loader"])
    return await org_unit_loader.load(uuid)


async def trigger_org_unit_refresh(uuid: UUID) -> dict[str, str]:
    """Trigger external integration for a given org unit UUID.

    Args:
        uuid: UUID of the org unit to trigger refresh for.

    Returns:
        The submit result.
    """
    response = await load_org_unit(uuid)
    if not response.objects:
        exceptions.ErrorCodes.E_ORG_UNIT_NOT_FOUND(org_unit_uuid=str(uuid))

    request = {mapping.UUID: str(uuid)}
    handler = await OrgUnitRequestHandler.construct(
        request, mapping.RequestType.REFRESH
    )
    result = await handler.submit()
    return result


async def terminate_org_unit_validation(
    ou_terminate: OrganisationUnitTerminate,
) -> None:
    uuid_str = str(ou_terminate.uuid)

    # Get & verify basic date
    if ou_terminate.from_date and ou_terminate.to_date:
        date = ou_terminate.get_terminate_effect_from_date()
    else:
        date = ou_terminate.get_terminate_effect_to_date()

    # Verify date against OrgUnit range
    await validator.is_date_range_in_org_unit_range(
        {"uuid": uuid_str},
        date - util.MINIMAL_INTERVAL,
        date,
    )

    # Find children, roles and addresses, and verify constraints

    # Find & verify there is no children
    c = lora.Connector(effective_date=util.to_iso_date(date))
    children = set(
        await c.organisationenhed.load_uuids(
            overordnet=uuid_str,
            gyldighed="Aktiv",
        )
    )

    roles = set(
        await c.organisationfunktion.load_uuids(
            tilknyttedeenheder=uuid_str,
            gyldighed="Aktiv",
        )
    )

    addresses = set(
        await c.organisationfunktion.load_uuids(
            tilknyttedeenheder=uuid_str,
            funktionsnavn=mapping.ADDRESS_KEY,
            gyldighed="Aktiv",
        )
    )

    active_roles = roles - addresses
    role_counts = set()
    if active_roles:
        role_counts = set(
            mapping.ORG_FUNK_EGENSKABER_FIELD.get(obj)[0]["funktionsnavn"]
            for objid, obj in await c.organisationfunktion.get_all_by_uuid(
                uuids=active_roles
            )
        )

    if children and role_counts:
        exceptions.ErrorCodes.V_TERMINATE_UNIT_WITH_CHILDREN_AND_ROLES(
            child_count=len(children),
            roles=", ".join(sorted(role_counts)),
        )
    elif children:
        exceptions.ErrorCodes.V_TERMINATE_UNIT_WITH_CHILDREN(
            child_count=len(children),
        )
    elif role_counts:
        exceptions.ErrorCodes.V_TERMINATE_UNIT_WITH_ROLES(
            roles=", ".join(sorted(role_counts)),
        )


async def terminate_org_unit(
    ou_terminate: OrganisationUnitTerminate,
) -> OrganizationUnit:
    try:
        await terminate_org_unit_validation(ou_terminate)
    except Exception as e:
        logger.exception("ERROR validating termination request.")
        raise e

    # Create payload to LoRa
    org_unit_trigger = OrgUnitTrigger(
        employee_id=None,
        org_unit_uuid=ou_terminate.uuid,
        request_type=mapping.RequestType.TERMINATE,
        request=MoraTriggerRequest(
            type=mapping.ORG_UNIT,
            uuid=ou_terminate.uuid,
            validity=Validity(
                from_date=ou_terminate.from_date,
                to_date=ou_terminate.to_date,
            ),
        ),
        role_type=mapping.ORG_UNIT,
        event_type=mapping.EventType.ON_BEFORE,
        uuid=ou_terminate.uuid,
    )

    trigger_dict = org_unit_trigger.to_trigger_dict()

    # ON_BEFORE
    if not ou_terminate.triggerless:
        _ = await Trigger.run(trigger_dict)

    # Do LoRa update
    lora_conn = lora.Connector()
    lora_result = await lora_conn.organisationenhed.update(
        ou_terminate.get_lora_payload(), ou_terminate.uuid
    )

    # ON_AFTER
    trigger_dict.update(
        {
            Trigger.RESULT: lora_result,
            Trigger.EVENT_TYPE: mapping.EventType.ON_AFTER,
        }
    )

    # ON_AFTER
    if not ou_terminate.triggerless:
        _ = await Trigger.run(trigger_dict)

    # Return the unit as the final thing
    return OrganizationUnit(uuid=lora_result)


def _get_terminate_effect(unit: OrganisationUnitTerminate) -> dict:
    if unit.from_date and unit.to_date:
        return common._create_virkning(
            _get_terminate_effect_from_date(unit), _get_terminate_effect_to_date(unit)
        )

    if not unit.from_date and unit.to_date:
        logger.warning(
            'terminate org unit called without "from" in "validity"',
        )

        return common._create_virkning(_get_terminate_effect_to_date(unit), "infinity")

    raise exceptions.ErrorCodes.V_MISSING_REQUIRED_VALUE(
        key="Organization Unit must be set with either 'to' or both 'from' " "and 'to'",
        unit={
            "from": unit.from_date.isoformat() if unit.from_date else None,
            "to": unit.to_date.isoformat() if unit.to_date else None,
        },
    )


def _get_terminate_effect_from_date(
    unit: OrganisationUnitTerminate,
) -> datetime.datetime:
    if not unit.from_date or not isinstance(unit.from_date, datetime.datetime):
        raise exceptions.ErrorCodes.V_MISSING_START_DATE()

    if unit.from_date.time() != datetime.time.min:
        exceptions.ErrorCodes.E_INVALID_INPUT(
            "{!r} is not at midnight!".format(unit.from_date.isoformat()),
        )

    return unit.from_date


def _get_terminate_effect_to_date(
    unit: OrganisationUnitTerminate,
) -> datetime.datetime:
    if not unit.to_date:
        return POSITIVE_INFINITY

    if unit.to_date.time() != datetime.time.min:
        exceptions.ErrorCodes.E_INVALID_INPUT(
            "{!r} is not at midnight!".format(unit.to_date.isoformat()),
        )

    return unit.to_date + ONE_DAY


def _create_trigger_dict_from_org_unit_input(
    unit: OrganisationUnitTerminate,
) -> dict:
    uuid_str = str(unit.uuid)

    # create trigger dict request
    validity = {}
    if unit.from_date:
        validity[mapping.FROM] = unit.from_date.isoformat()
    if unit.to_date:
        validity[mapping.TO] = unit.to_date.isoformat()

    trigger_request = {
        mapping.TYPE: mapping.ORG_UNIT,
        mapping.UUID: uuid_str,
        mapping.VALIDITY: validity,
    }

    # Create the return dict
    trigger_dict = {
        Trigger.REQUEST_TYPE: mapping.RequestType.TERMINATE,
        Trigger.REQUEST: trigger_request,
        Trigger.ROLE_TYPE: mapping.ORG_UNIT,
        Trigger.ORG_UNIT_UUID: uuid_str,
        Trigger.EVENT_TYPE: mapping.EventType.ON_BEFORE,
        Trigger.UUID: uuid_str,
        Trigger.RESULT: None,
    }

    return trigger_dict