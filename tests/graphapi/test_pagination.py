# SPDX-FileCopyrightText: Magenta ApS <https://magenta.dk>
# SPDX-License-Identifier: MPL-2.0
from collections.abc import Callable
from typing import Any
from uuid import UUID

import pytest

from mora.graphapi.types import Cursor
from mora.util import now
from tests.conftest import GraphAPIPost

serialize_cursor = Cursor._scalar_definition.serialize


@pytest.mark.integration_test
@pytest.mark.usefixtures("fixture_db")
@pytest.mark.parametrize(
    "resolver,limit,expected_length",
    [
        # Addresses
        ("addresses", None, 11),
        ("addresses", 0, 0),
        ("addresses", 8, 8),
        ("addresses", 4, 4),
        # Associations
        ("associations", None, 2),
        ("associations", 0, 0),
        ("associations", 1, 1),
        # Classes
        ("classes", None, 39),
        ("classes", 0, 0),
        ("classes", 38, 38),
        ("classes", 10, 10),
        # Employees
        ("employees", None, 5),
        ("employees", 0, 0),
        ("employees", 4, 4),
        ("employees", 2, 2),
        # Engagements
        ("engagements", None, 3),
        ("engagements", 0, 0),
        ("engagements", 3, 3),
        ("engagements", 2, 2),
        # Facets
        ("facets", None, 18),
        ("facets", 0, 0),
        ("facets", 18, 18),
        ("facets", 10, 10),
        # It Systems
        ("itsystems", None, 3),
        ("itsystems", 0, 0),
        ("itsystems", 3, 3),
        ("itsystems", 2, 2),
        # It Users
        ("itusers", None, 2),
        ("itusers", 0, 0),
        ("itusers", 1, 1),
        # KLEs
        ("kles", None, 1),
        ("kles", 0, 0),
        ("kles", 1, 1),
        # Leaves
        ("leaves", None, 2),
        ("leaves", 0, 0),
        ("leaves", 1, 1),
        # Managers
        ("managers", None, 1),
        ("managers", 0, 0),
        ("managers", 1, 1),
        # Org Units
        ("org_units", None, 10),
        ("org_units", 0, 0),
        # While LIMITing is done in LoRa/SQL, further filtering is sometimes applied
        # in MO. Confusingly, this means that receiving a list shorter than the
        # requested limit does not imply that we are at the end.
        ("org_units", 9, 9),
        ("org_units", 11, 10),
        # Owners
        ("owners", None, 2),
        ("owners", 0, 0),
        ("owners", 1, 1),
        # Related Units
        ("related_units", None, 1),
        ("related_units", 0, 0),
        ("related_units", 1, 1),
        # Rolebindings
        ("rolebindings", None, 1),
        ("rolebindings", 0, 0),
        ("rolebindings", 1, 1),
    ],
)
async def test_pagination(
    graphapi_post: GraphAPIPost,
    resolver: str,
    limit: int,
    expected_length: int,
) -> None:
    """Test that the first page honours the limit."""
    query = f"""
        query PaginationTestQuery($limit: int, $cursor: Cursor) {{
          {resolver}(limit: $limit, cursor: $cursor) {{
            objects {{
                uuid
            }}
            page_info {{
                next_cursor
            }}
          }}
        }}
    """
    variables = dict(limit=limit, cursor=None)
    response = graphapi_post(query, variables)
    assert response.errors is None
    assert len(response.data[resolver]["objects"]) == expected_length


@pytest.mark.integration_test
@pytest.mark.usefixtures("fixture_db")
@pytest.mark.parametrize(
    "resolver",
    [
        "addresses",
        "associations",
        "classes",
        "employees",
        "engagements",
        "facets",
        "itsystems",
        "itusers",
        "kles",
        "leaves",
        "managers",
        "org_units",
        "owners",
        "related_units",
        "rolebindings",
    ],
)
async def test_pagination_out_of_range(
    graphapi_post: GraphAPIPost, resolver: str
) -> None:
    """Test that a cursor past the last element returns nothing and terminates.

    Keyset pagination keys on the entity UUID, so a cursor whose `last` is the
    maximum possible UUID sorts after every real row: `id > last` matches nothing.
    """
    exhausted_cursor = serialize_cursor(
        Cursor(last=UUID(int=(1 << 128) - 1), registration_time=now())
    )
    query = f"""
        query PaginationTestQuery($limit: int, $cursor: Cursor) {{
          {resolver}(limit: $limit, cursor: $cursor) {{
            objects {{
                uuid
            }}
            page_info {{
                next_cursor
            }}
          }}
        }}
    """
    variables = dict(limit=10, cursor=exhausted_cursor)
    response = graphapi_post(query, variables)
    assert response.errors is None
    assert response.data[resolver]["objects"] == []
    assert response.data[resolver]["page_info"]["next_cursor"] is None


@pytest.mark.integration_test
@pytest.mark.usefixtures("fixture_db")
@pytest.mark.parametrize("limit", [1, 5, 10, 100])
@pytest.mark.parametrize(
    "resolver,expected",
    [
        ("addresses", 11),
        ("associations", 2),
        ("classes", 39),
        ("employees", 5),
        ("engagements", 3),
        ("facets", 18),
        ("itsystems", 3),
        ("itusers", 2),
        ("kles", 1),
        ("leaves", 2),
        ("managers", 1),
        ("org_units", 10),
        ("owners", 2),
        ("related_units", 1),
        ("rolebindings", 1),
    ],
)
async def test_cursor_based_pagination(
    graphapi_post: GraphAPIPost,
    limit: int,
    resolver: str,
    expected: int,
) -> None:
    """Test that out of range pagination returns None."""
    query = f"""
        query PaginationTestQuery($limit: int, $cursor: Cursor) {{
          {resolver}(limit: $limit, cursor: $cursor) {{
            objects {{
                uuid
            }}
            page_info {{
                next_cursor
            }}
          }}
        }}
    """
    elements = []

    cursor = None
    while True:
        variables = dict(limit=limit, cursor=cursor)
        response = graphapi_post(query, variables)
        assert response.errors is None
        elements.extend(response.data[resolver]["objects"])
        cursor = response.data[resolver]["page_info"]["next_cursor"]
        if cursor is None:
            break

    assert len(elements) == expected


@pytest.mark.integration_test
@pytest.mark.usefixtures("fixture_db")
async def test_cursor_stable_registration(
    graphapi_post: GraphAPIPost,
) -> None:
    """Test that pagination results in a consistent view."""
    query = """
        query PaginationTestQuery($limit: int, $cursor: Cursor) {
          facets(limit: $limit, cursor: $cursor) {
            objects {
                uuid
            }
            page_info {
                next_cursor
            }
          }
        }
    """
    create_facet_query = """
        mutation CreateFacet($input: FacetCreateInput!) {
          facet_create(input: $input) {
            uuid
          }
        }
    """

    def fetch(cursor):
        variables = dict(limit=5, cursor=cursor)
        response = graphapi_post(query, variables)
        assert response.errors is None
        uuids = {obj["uuid"] for obj in response.data["facets"]["objects"]}
        cursor = response.data["facets"]["page_info"]["next_cursor"]
        return uuids, cursor

    # First, get all facet uuids and store them in original
    original = set()
    cursor = None
    while True:
        uuids, cursor = fetch(cursor)
        original |= uuids
        if cursor is None:
            break

    # Start new pagination, but don't finish
    stable_pagination_result, stable_pagination_cursor = fetch(cursor)
    assert stable_pagination_cursor is not None

    # Add new facet
    response = graphapi_post(
        create_facet_query,
        {
            "input": {
                "user_key": "TestFacet",
                "validity": {
                    "from": now().date().isoformat(),
                    "to": None,
                },
            }
        },
    )
    assert response.errors is None
    new_uuid = response.data["facet_create"]["uuid"]

    # Do yet another fresh pagination, this time we expect the "original" uuids
    # _and_ the `new_uuid`
    final_facets = set()
    cursor = None
    while True:
        uuids, cursor = fetch(cursor)
        final_facets |= uuids
        if cursor is None:
            break
    assert final_facets - original == {
        new_uuid,
    }

    # Finish the "stable" pagination, where we do not expect the new facet
    while True:
        uuids, stable_pagination_cursor = fetch(stable_pagination_cursor)
        stable_pagination_result |= uuids
        if stable_pagination_cursor is None:
            break
    assert original == stable_pagination_result


@pytest.mark.integration_test
@pytest.mark.usefixtures("empty_db")
async def test_pagination_includes_nil_uuid(
    graphapi_post: GraphAPIPost,
    create_facet: Callable[[dict[str, Any]], UUID],
) -> None:
    """Keyset pagination must not skip an entity with the all-zeroes UUID.

    The first page imposes no lower bound, so the nil UUID is returned even though
    it would be excluded by the `column > UUID(int=0)` boundary used on subsequent
    pages.
    """
    nil_uuid = str(UUID(int=0))
    create_facet(
        {
            "uuid": nil_uuid,
            "user_key": "nil-facet",
            "validity": {"from": "1970-01-01", "to": None},
        }
    )
    query = """
        query PaginationTestQuery($limit: int, $cursor: Cursor) {
          facets(limit: $limit, cursor: $cursor) {
            objects {
                uuid
            }
            page_info {
                next_cursor
            }
          }
        }
    """
    # Paginate to completion (limit=1 to exercise the cursor boundary too) and
    # ensure the nil-UUID facet is among the returned objects.
    seen = []
    cursor = None
    while True:
        response = graphapi_post(query, {"limit": 1, "cursor": cursor})
        assert response.errors is None
        seen.extend(obj["uuid"] for obj in response.data["facets"]["objects"])
        cursor = response.data["facets"]["page_info"]["next_cursor"]
        if cursor is None:
            break
    assert nil_uuid in seen
