# SPDX-FileCopyrightText: Magenta ApS <https://magenta.dk>
# SPDX-License-Identifier: MPL-2.0
"""The fields of access log entries are guarded by read policies."""

import json
from datetime import UTC
from datetime import datetime
from unittest.mock import ANY
from uuid import UUID
from uuid import uuid4

import pytest
from more_itertools import one

from mora.db import AccessLogOperation
from mora.db import AccessLogRead
from mora.db import AsyncSession
from mora.db import Collection
from tests.conftest import BRUCE_UUID
from tests.conftest import GraphAPIPost
from tests.conftest import SetAuth
from tests.conftest import SetRules


@pytest.mark.integration_test
@pytest.mark.envvar({"ACCESS_LOG_ENABLE": "True"})
@pytest.mark.usefixtures("empty_db")
async def test_a_reader_reads_the_fields_of_an_access_log_entry(
    set_auth: SetAuth, graphapi_post: GraphAPIPost
) -> None:
    """A reader reads every field of an access log entry."""
    reader = uuid4()
    set_auth({"reader"}, reader)
    query = """
        query {
          access_log {
            objects { id time actor actor_object { uuid } model uuids }
          }
        }
    """
    # The second read reads the entry logged by the first
    response = graphapi_post(query)
    assert response.errors is None
    assert response.data == {"access_log": {"objects": []}}

    response = graphapi_post(query)

    assert response.errors is None
    assert response.data == {
        "access_log": {
            "objects": [
                {
                    "id": ANY,
                    "time": ANY,
                    "actor": str(reader),
                    "actor_object": {"uuid": str(reader)},
                    "model": "ACCESS_LOG",
                    "uuids": [],
                }
            ]
        }
    }


@pytest.mark.integration_test
@pytest.mark.envvar({"ACCESS_LOG_ENABLE": "True"})
@pytest.mark.usefixtures("empty_db")
async def test_an_access_log_field_no_rule_grants_is_denied(
    set_auth: SetAuth, graphapi_post: GraphAPIPost, set_rules: SetRules
) -> None:
    """A field of an access log entry no rule grants is denied where it is read."""
    await set_rules("policy_reader", Collection.AccessLog, {"model"})
    set_auth({"policy_reader"}, uuid4())
    query = "query { access_log { objects { model actor } } }"
    # The second read reads the entry logged by the first
    response = graphapi_post(query)
    assert response.errors is None
    assert response.data == {"access_log": {"objects": []}}

    response = graphapi_post(query)

    assert response.data is None
    error = one(response.errors)
    assert error["message"] == "No policy approved the access"
    assert error["path"] == ["access_log", "objects", 0, "actor"]


# The access log entry the conditions below single out, and an object it read
SINGLED_OUT = UUID("1f0c2a8e-6a51-4d8e-9b0f-3c7d2e4a5b61")
READ_BY_IT = UUID("7b3e9d24-0c6f-4a1b-8e52-d9f4a6c3b210")


@pytest.mark.integration_test
@pytest.mark.parametrize(
    "condition",
    [
        json.dumps({"ids": [str(SINGLED_OUT)]}),
        json.dumps({"uuids": [str(READ_BY_IT)]}),
        '{"actors": [token.uuid]}',
        '{"models": ["PERSON"]}',
        json.dumps(
            {"start": "2000-01-01T00:00:00+00:00", "end": "2001-01-01T00:00:00+00:00"}
        ),
    ],
)
async def test_an_access_log_entry_gets_the_fields_of_the_rules_matching_it(
    condition: str,
    empty_db: AsyncSession,
    set_auth: SetAuth,
    graphapi_post: GraphAPIPost,
) -> None:
    """An access log entry is matched by its filter, through any field of it."""
    earlier, later = uuid4(), uuid4()
    # GraphQL reads log entries, but cannot choose their id or time
    empty_db.add_all(
        [
            AccessLogOperation(
                id=SINGLED_OUT,
                time=datetime(2000, 6, 1, tzinfo=UTC),
                actor=BRUCE_UUID,
                model="Bruger",
                operation="resolve_employees",
                arguments={},
                uuids=[AccessLogRead(uuid=READ_BY_IT)],
            ),
            # Entries on either side of the window of time
            *(
                AccessLogOperation(
                    id=entry,
                    time=datetime(year, 6, 1, tzinfo=UTC),
                    actor=uuid4(),
                    model="OrganisationEnhed",
                    operation="resolve_org_units",
                    arguments={},
                    uuids=[AccessLogRead(uuid=uuid4())],
                )
                for entry, year in ((earlier, 1990), (later, 2010))
            ),
        ]
    )
    # A request opens its own session, so the rows must be committed to it
    await empty_db.commit()
    response = graphapi_post(
        """
        mutation Declare($uuid: UUID!, $state: PolicyStateInput) {
          policy_declare(uuid: $uuid, state: $state) { uuid }
        }
        """,
        variables={
            "uuid": str(uuid4()),
            "state": {
                "name": "Access Log Auditor",
                "selectors": [{"kind": "role", "value": "access_log_auditor"}],
                "read_rules": [
                    {
                        "collection": "AccessLog",
                        "fields": ["model"],
                        "condition": condition,
                        "graphql_version": "VERSION_30",
                    }
                ],
            },
        },
    )
    assert response.errors is None
    set_auth({"access_log_auditor"}, BRUCE_UUID)

    query = """
        query ReadModel($id: UUID!) {
          access_log(filter: { ids: [$id] }) { objects { model } }
        }
    """
    response = graphapi_post(query, {"id": str(SINGLED_OUT)})
    assert response.errors is None
    assert response.data == {"access_log": {"objects": [{"model": "PERSON"}]}}

    for entry in (earlier, later):
        response = graphapi_post(query, {"id": str(entry)})
        assert response.data is None
        error = one(response.errors)
        assert error["message"] == "No policy approved the access"
        assert error["path"] == ["access_log", "objects", 0, "model"]
