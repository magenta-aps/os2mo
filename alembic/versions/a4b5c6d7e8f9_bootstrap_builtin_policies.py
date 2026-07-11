# SPDX-FileCopyrightText: Magenta ApS <https://magenta.dk>
# SPDX-License-Identifier: MPL-2.0
"""Bootstrap the built-in policies

Seed the built-in policies on top of the policy-engine schema: the protected
"Policy Administrator", the removable "Administrator"/"Reader" convenience
policies, the "Legacy" policy reproducing role-based RBAC (one explicit rule per
permission-gated field), and the "Owner" policy. Squashed from the incremental
development migrations.
"""

import json
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "a4b5c6d7e8f9"
down_revision: str | Sequence[str] | None = "9f8e7d6c5b4a"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Well-known UUIDs (the policy name encoded in the tail).
POLICYADMIN_UUID = "ded1ca7e-9bac-5eed-706f-6c61646d696e"
ADMINISTRATOR_UUID = "e5ca1a7e-9bac-5eed-0000-0061646d696e"
READER_UUID = "acce5500-9bac-5eed-0000-726561646572"
LEGACY_UUID = "0b50137e-9bac-5eed-0000-6c6567616379"
OWNER_UUID = "6f776e65-9bac-5eed-0000-006f776e6572"

policy = sa.table(
    "policy",
    sa.column("id", sa.Uuid),
    sa.column("name", sa.String),
    sa.column("description", sa.String),
    sa.column("start", sa.DateTime),
    sa.column("end", sa.DateTime),
)
policy_actor = sa.table(
    "policy_actor",
    sa.column("kind", sa.String),
    sa.column("value", sa.String),
    sa.column("policy_fk", sa.Uuid),
)
policy_rule = sa.table(
    "policy_rule",
    sa.column("type", sa.String),
    sa.column("field", sa.String),
    sa.column("condition", sa.String),
    sa.column("filter", sa.String),
    sa.column("policy_fk", sa.Uuid),
)

# Policy Administrator: the (type, field) resources it grants.
POLICYADMIN_RULES = [
    ("Query", "policies"),
    ("Mutation", "policy_declare"),
    ("Mutation", "policy_delete"),
    ("Mutation", "policy_actor_declare"),
    ("Mutation", "policy_actors_declare"),
    ("Mutation", "policy_actor_delete"),
    ("Mutation", "policy_rule_declare"),
    ("Mutation", "policy_rules_declare"),
    ("Mutation", "policy_rule_delete"),
]

# Legacy: one rule per permission-gated (type, field), gated on the field's
# required RBAC role via `"<role>" in token.roles`.
LEGACY_RULES: list[tuple[str, str, str]] = [
    ("Actor", "event_listeners", '"read_event_listener" in token.roles'),
    ("Actor", "event_namespaces", '"read_event_namespace" in token.roles'),
    ("Address", "address_type", '"read_class" in token.roles'),
    ("Address", "address_type_response", '"read_class" in token.roles'),
    ("Address", "employee", '"read_employee" in token.roles'),
    ("Address", "engagement", '"read_engagement" in token.roles'),
    ("Address", "engagement_response", '"read_engagement" in token.roles'),
    ("Address", "ituser", '"read_ituser" in token.roles'),
    ("Address", "ituser_response", '"read_ituser" in token.roles'),
    ("Address", "org_unit", '"read_org_unit" in token.roles'),
    ("Address", "org_unit_response", '"read_org_unit" in token.roles'),
    ("Address", "person", '"read_employee" in token.roles'),
    ("Address", "person_response", '"read_employee" in token.roles'),
    ("Address", "visibility", '"read_class" in token.roles'),
    ("Address", "visibility_response", '"read_class" in token.roles'),
    ("Association", "association_type", '"read_class" in token.roles'),
    ("Association", "association_type_response", '"read_class" in token.roles'),
    ("Association", "dynamic_class", '"read_class" in token.roles'),
    ("Association", "dynamic_class_response", '"read_class" in token.roles'),
    ("Association", "employee", '"read_employee" in token.roles'),
    ("Association", "it_user", '"read_ituser" in token.roles'),
    ("Association", "it_user_response", '"read_ituser" in token.roles'),
    ("Association", "job_function", '"read_class" in token.roles'),
    ("Association", "job_function_response", '"read_class" in token.roles'),
    ("Association", "org_unit", '"read_org_unit" in token.roles'),
    ("Association", "org_unit_response", '"read_org_unit" in token.roles'),
    ("Association", "person", '"read_employee" in token.roles'),
    ("Association", "person_response", '"read_employee" in token.roles'),
    ("Association", "primary", '"read_class" in token.roles'),
    ("Association", "primary_response", '"read_class" in token.roles'),
    ("Association", "substitute", '"read_employee" in token.roles'),
    ("Association", "substitute_response", '"read_employee" in token.roles'),
    ("Association", "trade_union", '"read_class" in token.roles'),
    ("Association", "trade_union_response", '"read_class" in token.roles'),
    ("Class", "children", '"read_class" in token.roles'),
    ("Class", "children_response", '"read_class" in token.roles'),
    ("Class", "facet", '"read_facet" in token.roles'),
    ("Class", "facet_response", '"read_facet" in token.roles'),
    ("Class", "it_system", '"read_itsystem" in token.roles'),
    ("Class", "it_system_response", '"read_itsystem" in token.roles'),
    ("Class", "parent", '"read_class" in token.roles'),
    ("Class", "parent_response", '"read_class" in token.roles'),
    ("Class", "top_level_facet", '"read_facet" in token.roles'),
    ("Employee", "addresses", '"read_address" in token.roles'),
    ("Employee", "addresses_response", '"read_address" in token.roles'),
    ("Employee", "associations", '"read_association" in token.roles'),
    ("Employee", "associations_response", '"read_association" in token.roles'),
    ("Employee", "engagements", '"read_engagement" in token.roles'),
    ("Employee", "engagements_response", '"read_engagement" in token.roles'),
    ("Employee", "itusers", '"read_ituser" in token.roles'),
    ("Employee", "itusers_response", '"read_ituser" in token.roles'),
    ("Employee", "leaves", '"read_leave" in token.roles'),
    ("Employee", "leaves_response", '"read_leave" in token.roles'),
    ("Employee", "manager_roles", '"read_manager" in token.roles'),
    ("Employee", "manager_roles_response", '"read_manager" in token.roles'),
    ("Engagement", "addresses_response", '"read_address" in token.roles'),
    ("Engagement", "employee", '"read_employee" in token.roles'),
    ("Engagement", "engagement_type", '"read_class" in token.roles'),
    ("Engagement", "engagement_type_response", '"read_class" in token.roles'),
    ("Engagement", "itusers", '"read_ituser" in token.roles'),
    ("Engagement", "itusers_response", '"read_ituser" in token.roles'),
    ("Engagement", "job_function", '"read_class" in token.roles'),
    ("Engagement", "job_function_response", '"read_class" in token.roles'),
    ("Engagement", "leave", '"read_leave" in token.roles'),
    ("Engagement", "leave_response", '"read_leave" in token.roles'),
    ("Engagement", "managers", '"read_manager" in token.roles'),
    ("Engagement", "org_unit", '"read_org_unit" in token.roles'),
    ("Engagement", "org_unit_response", '"read_org_unit" in token.roles'),
    ("Engagement", "person", '"read_employee" in token.roles'),
    ("Engagement", "person_response", '"read_employee" in token.roles'),
    ("Engagement", "primary", '"read_class" in token.roles'),
    ("Engagement", "primary_response", '"read_class" in token.roles'),
    ("Facet", "children", '"read_facet" in token.roles'),
    ("Facet", "children_response", '"read_facet" in token.roles'),
    ("Facet", "classes", '"read_class" in token.roles'),
    ("Facet", "classes_responses", '"read_class" in token.roles'),
    ("Facet", "parent", '"read_facet" in token.roles'),
    ("Facet", "parent_response", '"read_facet" in token.roles'),
    ("FullEvent", "listener", '"read_event_listener" in token.roles'),
    ("ITSystem", "roles", '"read_class" in token.roles'),
    ("ITSystem", "roles_response", '"read_class" in token.roles'),
    ("ITUser", "addresses", '"read_address" in token.roles'),
    ("ITUser", "addresses_response", '"read_address" in token.roles'),
    ("ITUser", "employee", '"read_employee" in token.roles'),
    ("ITUser", "engagement", '"read_engagement" in token.roles'),
    ("ITUser", "engagement_response", '"read_engagement" in token.roles'),
    ("ITUser", "engagements", '"read_engagement" in token.roles'),
    ("ITUser", "engagements_responses", '"read_engagement" in token.roles'),
    ("ITUser", "itsystem", '"read_itsystem" in token.roles'),
    ("ITUser", "itsystem_response", '"read_itsystem" in token.roles'),
    ("ITUser", "org_unit", '"read_org_unit" in token.roles'),
    ("ITUser", "org_unit_response", '"read_org_unit" in token.roles'),
    ("ITUser", "person", '"read_employee" in token.roles'),
    ("ITUser", "person_response", '"read_employee" in token.roles'),
    ("ITUser", "primary", '"read_class" in token.roles'),
    ("ITUser", "primary_response", '"read_class" in token.roles'),
    ("ITUser", "rolebindings", '"read_rolebinding" in token.roles'),
    ("ITUser", "rolebindings_response", '"read_rolebinding" in token.roles'),
    ("KLE", "kle_aspects", '"read_class" in token.roles'),
    ("KLE", "kle_aspects_response", '"read_class" in token.roles'),
    ("KLE", "kle_number", '"read_class" in token.roles'),
    ("KLE", "kle_number_response", '"read_class" in token.roles'),
    ("KLE", "org_unit", '"read_org_unit" in token.roles'),
    ("KLE", "org_unit_response", '"read_org_unit" in token.roles'),
    ("Leave", "employee", '"read_employee" in token.roles'),
    ("Leave", "engagement", '"read_engagement" in token.roles'),
    ("Leave", "engagement_response", '"read_engagement" in token.roles'),
    ("Leave", "leave_type", '"read_class" in token.roles'),
    ("Leave", "leave_type_response", '"read_class" in token.roles'),
    ("Leave", "person", '"read_employee" in token.roles'),
    ("Leave", "person_response", '"read_employee" in token.roles'),
    ("Listener", "events", '"read_event" in token.roles'),
    ("Listener", "namespace", '"read_event_namespace" in token.roles'),
    ("Manager", "employee", '"read_employee" in token.roles'),
    ("Manager", "engagement_response", '"read_engagement" in token.roles'),
    ("Manager", "manager_level", '"read_class" in token.roles'),
    ("Manager", "manager_level_response", '"read_class" in token.roles'),
    ("Manager", "manager_type", '"read_class" in token.roles'),
    ("Manager", "manager_type_response", '"read_class" in token.roles'),
    ("Manager", "org_unit", '"read_org_unit" in token.roles'),
    ("Manager", "org_unit_response", '"read_org_unit" in token.roles'),
    ("Manager", "person", '"read_employee" in token.roles'),
    ("Manager", "person_response", '"read_employee" in token.roles'),
    ("Manager", "responsibilities", '"read_class" in token.roles'),
    ("Manager", "responsibilities_response", '"read_class" in token.roles'),
    ("Mutation", "address_create", '"create_address" in token.roles'),
    ("Mutation", "address_delete", '"delete_address" in token.roles'),
    ("Mutation", "address_refresh", '"refresh_address" in token.roles'),
    ("Mutation", "address_terminate", '"terminate_address" in token.roles'),
    ("Mutation", "address_update", '"update_address" in token.roles'),
    ("Mutation", "addresses_create", '"create_address" in token.roles'),
    ("Mutation", "association_create", '"create_association" in token.roles'),
    ("Mutation", "association_refresh", '"refresh_association" in token.roles'),
    ("Mutation", "association_terminate", '"terminate_association" in token.roles'),
    ("Mutation", "association_update", '"update_association" in token.roles'),
    ("Mutation", "class_create", '"create_class" in token.roles'),
    ("Mutation", "class_delete", '"delete_class" in token.roles'),
    ("Mutation", "class_refresh", '"refresh_class" in token.roles'),
    ("Mutation", "class_terminate", '"terminate_class" in token.roles'),
    ("Mutation", "class_update", '"update_class" in token.roles'),
    ("Mutation", "employee_create", '"create_employee" in token.roles'),
    ("Mutation", "employee_delete", '"delete_employee" in token.roles'),
    ("Mutation", "employee_refresh", '"refresh_employee" in token.roles'),
    ("Mutation", "employee_terminate", '"terminate_employee" in token.roles'),
    ("Mutation", "employee_update", '"update_employee" in token.roles'),
    ("Mutation", "engagement_create", '"create_engagement" in token.roles'),
    ("Mutation", "engagement_delete", '"delete_engagement" in token.roles'),
    ("Mutation", "engagement_refresh", '"refresh_engagement" in token.roles'),
    ("Mutation", "engagement_terminate", '"terminate_engagement" in token.roles'),
    ("Mutation", "engagement_update", '"update_engagement" in token.roles'),
    ("Mutation", "engagements_create", '"create_engagement" in token.roles'),
    ("Mutation", "engagements_update", '"update_engagement" in token.roles'),
    ("Mutation", "event_acknowledge", '"acknowledge_event" in token.roles'),
    ("Mutation", "event_listener_declare", '"create_event_listener" in token.roles'),
    ("Mutation", "event_listener_delete", '"delete_event_listener" in token.roles'),
    ("Mutation", "event_namespace_declare", '"create_event_namespace" in token.roles'),
    ("Mutation", "event_namespace_delete", '"delete_event_namespace" in token.roles'),
    ("Mutation", "event_rerun", '"rerun_event" in token.roles'),
    ("Mutation", "event_send", '"send_event" in token.roles'),
    ("Mutation", "event_silence", '"silence_event" in token.roles'),
    ("Mutation", "event_unsilence", '"unsilence_event" in token.roles'),
    ("Mutation", "facet_create", '"create_facet" in token.roles'),
    ("Mutation", "facet_delete", '"delete_facet" in token.roles'),
    ("Mutation", "facet_refresh", '"refresh_facet" in token.roles'),
    ("Mutation", "facet_terminate", '"terminate_facet" in token.roles'),
    ("Mutation", "facet_update", '"update_facet" in token.roles'),
    ("Mutation", "itassociation_create", '"create_association" in token.roles'),
    ("Mutation", "itassociation_terminate", '"terminate_association" in token.roles'),
    ("Mutation", "itassociation_update", '"update_association" in token.roles'),
    ("Mutation", "itsystem_create", '"create_itsystem" in token.roles'),
    ("Mutation", "itsystem_delete", '"delete_itsystem" in token.roles'),
    ("Mutation", "itsystem_refresh", '"refresh_itsystem" in token.roles'),
    ("Mutation", "itsystem_terminate", '"terminate_itsystem" in token.roles'),
    ("Mutation", "itsystem_update", '"update_itsystem" in token.roles'),
    ("Mutation", "ituser_create", '"create_ituser" in token.roles'),
    ("Mutation", "ituser_delete", '"delete_ituser" in token.roles'),
    ("Mutation", "ituser_refresh", '"refresh_ituser" in token.roles'),
    ("Mutation", "ituser_terminate", '"terminate_ituser" in token.roles'),
    ("Mutation", "ituser_update", '"update_ituser" in token.roles'),
    ("Mutation", "itusers_create", '"create_ituser" in token.roles'),
    ("Mutation", "kle_create", '"create_kle" in token.roles'),
    ("Mutation", "kle_refresh", '"refresh_kle" in token.roles'),
    ("Mutation", "kle_terminate", '"terminate_kle" in token.roles'),
    ("Mutation", "kle_update", '"update_kle" in token.roles'),
    ("Mutation", "leave_create", '"create_leave" in token.roles'),
    ("Mutation", "leave_refresh", '"refresh_leave" in token.roles'),
    ("Mutation", "leave_terminate", '"terminate_leave" in token.roles'),
    ("Mutation", "leave_update", '"update_leave" in token.roles'),
    ("Mutation", "manager_create", '"create_manager" in token.roles'),
    ("Mutation", "manager_delete", '"delete_manager" in token.roles'),
    ("Mutation", "manager_refresh", '"refresh_manager" in token.roles'),
    ("Mutation", "manager_terminate", '"terminate_manager" in token.roles'),
    ("Mutation", "manager_update", '"update_manager" in token.roles'),
    ("Mutation", "managers_create", '"create_manager" in token.roles'),
    ("Mutation", "org_create", '"create_org" in token.roles'),
    ("Mutation", "org_unit_create", '"create_org_unit" in token.roles'),
    ("Mutation", "org_unit_delete", '"delete_org_unit" in token.roles'),
    ("Mutation", "org_unit_refresh", '"refresh_org_unit" in token.roles'),
    ("Mutation", "org_unit_terminate", '"terminate_org_unit" in token.roles'),
    ("Mutation", "org_unit_update", '"update_org_unit" in token.roles'),
    ("Mutation", "owner_create", '"create_owner" in token.roles'),
    ("Mutation", "owner_refresh", '"refresh_owner" in token.roles'),
    ("Mutation", "owner_terminate", '"terminate_owner" in token.roles'),
    ("Mutation", "owner_update", '"update_owner" in token.roles'),
    ("Mutation", "policy_actor_declare", '"create_policy" in token.roles'),
    ("Mutation", "policy_actor_delete", '"delete_policy" in token.roles'),
    ("Mutation", "policy_actors_declare", '"create_policy" in token.roles'),
    ("Mutation", "policy_declare", '"create_policy" in token.roles'),
    ("Mutation", "policy_delete", '"delete_policy" in token.roles'),
    ("Mutation", "policy_rule_declare", '"create_policy" in token.roles'),
    ("Mutation", "policy_rule_delete", '"delete_policy" in token.roles'),
    ("Mutation", "policy_rules_declare", '"create_policy" in token.roles'),
    ("Mutation", "related_unit_refresh", '"refresh_related_unit" in token.roles'),
    ("Mutation", "related_units_update", '"update_related_unit" in token.roles'),
    ("Mutation", "rolebinding_create", '"create_rolebinding" in token.roles'),
    ("Mutation", "rolebinding_delete", '"delete_rolebinding" in token.roles'),
    ("Mutation", "rolebinding_refresh", '"refresh_rolebinding" in token.roles'),
    ("Mutation", "rolebinding_terminate", '"terminate_rolebinding" in token.roles'),
    ("Mutation", "rolebinding_update", '"update_rolebinding" in token.roles'),
    ("Mutation", "rolebindings_create", '"create_rolebinding" in token.roles'),
    ("Mutation", "upload_file", '"upload_files" in token.roles'),
    ("Myself", "policies", '"read_policy" in token.roles'),
    ("Namespace", "listeners", '"read_event_namespace" in token.roles'),
    ("OrganisationUnit", "addresses", '"read_address" in token.roles'),
    ("OrganisationUnit", "addresses_response", '"read_address" in token.roles'),
    ("OrganisationUnit", "ancestors", '"read_org_unit" in token.roles'),
    ("OrganisationUnit", "associations", '"read_association" in token.roles'),
    ("OrganisationUnit", "associations_response", '"read_association" in token.roles'),
    ("OrganisationUnit", "child_count", '"read_org_unit" in token.roles'),
    ("OrganisationUnit", "children", '"read_org_unit" in token.roles'),
    ("OrganisationUnit", "children_response", '"read_org_unit" in token.roles'),
    ("OrganisationUnit", "engagements", '"read_engagement" in token.roles'),
    ("OrganisationUnit", "engagements_response", '"read_engagement" in token.roles'),
    ("OrganisationUnit", "has_children", '"read_org_unit" in token.roles'),
    ("OrganisationUnit", "itusers", '"read_ituser" in token.roles'),
    ("OrganisationUnit", "itusers_response", '"read_ituser" in token.roles'),
    ("OrganisationUnit", "kles", '"read_kle" in token.roles'),
    ("OrganisationUnit", "kles_response", '"read_kle" in token.roles'),
    ("OrganisationUnit", "leaves", '"read_leave" in token.roles'),
    ("OrganisationUnit", "leaves_response", '"read_leave" in token.roles'),
    ("OrganisationUnit", "managers", '"read_manager" in token.roles'),
    ("OrganisationUnit", "managers_response", '"read_manager" in token.roles'),
    ("OrganisationUnit", "org_unit_hierarchy_model", '"read_class" in token.roles'),
    ("OrganisationUnit", "org_unit_level", '"read_class" in token.roles'),
    ("OrganisationUnit", "owners", '"read_owner" in token.roles'),
    ("OrganisationUnit", "parent", '"read_org_unit" in token.roles'),
    ("OrganisationUnit", "parent_response", '"read_org_unit" in token.roles'),
    ("OrganisationUnit", "related_units", '"read_related_unit" in token.roles'),
    (
        "OrganisationUnit",
        "related_units_response",
        '"read_related_unit" in token.roles',
    ),
    ("OrganisationUnit", "root", '"read_org_unit" in token.roles'),
    ("OrganisationUnit", "root_response", '"read_org_unit" in token.roles'),
    ("OrganisationUnit", "time_planning", '"read_class" in token.roles'),
    ("OrganisationUnit", "time_planning_response", '"read_class" in token.roles'),
    ("OrganisationUnit", "unit_hierarchy_response", '"read_class" in token.roles'),
    ("OrganisationUnit", "unit_level_response", '"read_class" in token.roles'),
    ("OrganisationUnit", "unit_type", '"read_class" in token.roles'),
    ("OrganisationUnit", "unit_type_response", '"read_class" in token.roles'),
    ("Owner", "org_unit", '"read_org_unit" in token.roles'),
    ("Owner", "org_unit_response", '"read_org_unit" in token.roles'),
    ("Owner", "owner", '"read_owner" in token.roles'),
    ("Owner", "owner_response", '"read_owner" in token.roles'),
    ("Owner", "person", '"read_employee" in token.roles'),
    ("Owner", "person_response", '"read_employee" in token.roles'),
    ("Query", "access_log", '"read_accesslog" in token.roles'),
    ("Query", "addresses", '"read_address" in token.roles'),
    ("Query", "associations", '"read_association" in token.roles'),
    ("Query", "classes", '"read_class" in token.roles'),
    ("Query", "employees", '"read_employee" in token.roles'),
    ("Query", "engagements", '"read_engagement" in token.roles'),
    ("Query", "event_fetch", '"fetch_event" in token.roles'),
    ("Query", "event_listeners", '"read_event_listener" in token.roles'),
    ("Query", "event_namespaces", '"read_event_namespace" in token.roles'),
    ("Query", "events", '"read_event" in token.roles'),
    ("Query", "facets", '"read_facet" in token.roles'),
    ("Query", "files", '"read_file" in token.roles'),
    ("Query", "itsystems", '"read_itsystem" in token.roles'),
    ("Query", "itusers", '"read_ituser" in token.roles'),
    ("Query", "kles", '"read_kle" in token.roles'),
    ("Query", "leaves", '"read_leave" in token.roles'),
    ("Query", "managers", '"read_manager" in token.roles'),
    ("Query", "org", '"read_org" in token.roles'),
    ("Query", "org_units", '"read_org_unit" in token.roles'),
    ("Query", "owners", '"read_owner" in token.roles'),
    ("Query", "persons", '"read_employee" in token.roles'),
    ("Query", "policies", '"read_policy" in token.roles'),
    ("Query", "registrations", '"read_registration" in token.roles'),
    ("Query", "related_units", '"read_related_unit" in token.roles'),
    ("Query", "rolebindings", '"read_rolebinding" in token.roles'),
    ("RelatedUnit", "org_units", '"read_org_unit" in token.roles'),
    ("RelatedUnit", "org_units_response", '"read_org_unit" in token.roles'),
    ("RoleBinding", "ituser", '"read_ituser" in token.roles'),
    ("RoleBinding", "ituser_response", '"read_ituser" in token.roles'),
    ("RoleBinding", "org_unit", '"read_org_unit" in token.roles'),
    ("RoleBinding", "org_unit_response", '"read_org_unit" in token.roles'),
    ("RoleBinding", "role", '"read_class" in token.roles'),
    ("RoleBinding", "role_response", '"read_class" in token.roles'),
    ("SpecialActor", "event_listeners", '"read_event_listener" in token.roles'),
    ("SpecialActor", "event_namespaces", '"read_event_namespace" in token.roles'),
    ("UnknownActor", "event_listeners", '"read_event_listener" in token.roles'),
    ("UnknownActor", "event_namespaces", '"read_event_namespace" in token.roles'),
]


# Check-specs are built as structured data and serialized. They are *almost*
# JSON, but a few values -- `actor` (the caller's employee uuid, resolved lazily
# by the engine) and the pinned `field` -- are bare CEL variable references, so
# they are wrapped in `_Cel` and emitted unquoted. The doubled `owner` is
# deliberate: the outer selects an owner org-function, the inner (an
# EmployeeFilter) is its owning *person*.
class _Cel(str):
    """A raw, unquoted CEL expression embedded in a check-spec (e.g. `actor`)."""


def _cel_json(value: object) -> str:
    """Serialize a check-spec to a CEL map literal: JSON, with bare `_Cel`."""
    if isinstance(value, _Cel):
        return str(value)
    if isinstance(value, dict):
        items = ", ".join(f"{json.dumps(k)}: {_cel_json(v)}" for k, v in value.items())
        return "{" + items + "}"
    if isinstance(value, list):
        return "[" + ", ".join(_cel_json(v) for v in value) + "]"
    return json.dumps(value)


_ACTOR = _Cel("actor")
# The owned entity, filtered by its owning person (`actor`).
_OWN_PERSON = {"owner": {"owner": {"uuids": [_ACTOR]}}}
# ... extended up the org-unit tree (self-or-ancestor).
_OWN_UNIT = {"ancestor": _OWN_PERSON}


def _unit(field: str) -> str:
    """Require ownership of the org-unit identified by ``field`` (hierarchical)."""
    return _cel_json(
        {
            "collection": "org_unit",
            "check": "IN",
            "field": _Cel(field),
            "filter": _OWN_UNIT,
        }
    )


def _person(field: str) -> str:
    """Require ownership of the person identified by ``field``."""
    return _cel_json(
        {
            "collection": "employee",
            "check": "IN",
            "field": _Cel(field),
            "filter": _OWN_PERSON,
        }
    )


def _obj_unit(collection: str, field: str) -> str:
    """Require the object (``field``) to link an org-unit the caller owns."""
    return _cel_json(
        {
            "collection": collection,
            "check": "IN",
            "field": _Cel(field),
            "filter": {"org_unit": _OWN_UNIT},
        }
    )


def _obj_person(collection: str, field: str) -> str:
    """Require the object (``field``) to link a person the caller owns."""
    return _cel_json(
        {
            "collection": collection,
            "check": "IN",
            "field": _Cel(field),
            "filter": {"employee": _OWN_PERSON},
        }
    )


# Detail-create branch: own the linked org-unit if present, else the person.
def _create_branch(item: str) -> str:
    return (
        f"{item}.org_unit != null ? {_unit(item + '.org_unit')} "
        f": {_person(item + '.person')}"
    )


# (field, filter-CEL) rules. A collection with two entries for one field is an
# OR (the object may link either an org-unit or a person).
OWNER_RULES: list[tuple[str, str]] = []


def _rule(field: str, filter_cel: str) -> None:
    OWNER_RULES.append((field, filter_cel))


# -- Detail collections -------------------------------------------------------
# Org-unit-mandatory (create -> own the org-unit; upd/term/del -> own the
# object's org-unit). `association` also covers the `itassociation_*` mutators.
for collection, fields in {
    "engagement": ["engagement"],
    "association": ["association", "itassociation"],
    "kle": ["kle"],
    "manager": ["manager"],
}.items():
    for prefix in fields:
        _rule(f"{prefix}_create", _unit("input.org_unit"))
        _rule(f"{prefix}_update", _obj_unit(collection, "input.uuid"))
        _rule(f"{prefix}_terminate", _obj_unit(collection, "input.uuid"))

# engagement has delete + bulk create/update.
_rule("engagement_delete", _obj_unit("engagement", "input.uuid"))
_rule("engagements_create", f"input.map(i, {_unit('i.org_unit')})")
_rule("engagements_update", f"input.map(i, {_obj_unit('engagement', 'i.uuid')})")
# manager has a bulk create.
_rule("managers_create", f"input.map(i, {_unit('i.org_unit')})")

# Person-only (leave).
_rule("leave_create", _person("input.person"))
_rule("leave_update", _obj_person("leave", "input.uuid"))
_rule("leave_terminate", _obj_person("leave", "input.uuid"))

# Rolebinding: org-unit (nullable, no person) + delete + bulk create.
for field in ("rolebinding_update", "rolebinding_terminate", "rolebinding_delete"):
    _rule(field, _obj_unit("rolebinding", "input.uuid"))
_rule("rolebinding_create", _unit("input.org_unit"))
_rule("rolebindings_create", f"input.map(i, {_unit('i.org_unit')})")

# Either org-unit or person (address, ituser, owner): two rules for
# upd/term/del, a branch for create.
for collection, ops in {
    "address": ("update", "terminate", "delete"),
    "ituser": ("update", "terminate", "delete"),
    "owner": ("update", "terminate"),
}.items():
    for op_name in ops:
        _rule(f"{collection}_{op_name}", _obj_unit(collection, "input.uuid"))
        _rule(f"{collection}_{op_name}", _obj_person(collection, "input.uuid"))
    _rule(f"{collection}_create", _create_branch("input"))
# address / ituser bulk create.
_rule("addresses_create", f"input.map(i, {_create_branch('i')})")
_rule("itusers_create", f"input.map(i, {_create_branch('i')})")

# related_unit: only a (single-input) update, keyed on the origin unit.
_rule("related_units_update", _unit("input.origin"))

# -- Employee -----------------------------------------------------------------
# Own the person to mutate it. A brand-new uuid has no owners -> create denied.
for op_name in ("create", "update", "terminate", "delete"):
    _rule(f"employee_{op_name}", _person("input.uuid"))

# -- Org-unit -----------------------------------------------------------------
_rule("org_unit_create", _unit("input.parent"))
_rule("org_unit_terminate", _unit("input.uuid"))
_rule("org_unit_delete", _unit("input.uuid"))
# Move: always own the unit; additionally own the *new* parent, but only when the
# parent actually changed (mirrors check_owner's `if parent := ...` guard).
_rule(
    "org_unit_update",
    f"[{_unit('input.uuid')}] + "
    f"(input.parent != null && input.parent != current.parent "
    f"? [{_unit('input.parent')}] : [])",
)


def upgrade() -> None:
    op.bulk_insert(
        policy,
        [
            {
                "id": POLICYADMIN_UUID,
                "name": "Policy Administrator",
                "description": "Bootstrap policy for administering policies.",
                "start": "1900-01-01T00:00:00+00:00",
                "end": None,
            },
            {
                "id": ADMINISTRATOR_UUID,
                "name": "Administrator",
                "description": "Grants access to all queries and mutators.",
                "start": "1900-01-01T00:00:00+00:00",
                "end": None,
            },
            {
                "id": READER_UUID,
                "name": "Reader",
                "description": "Grants read access to all queries.",
                "start": "1900-01-01T00:00:00+00:00",
                "end": None,
            },
            {
                "id": LEGACY_UUID,
                "name": "Legacy",
                "description": "Reproduces legacy RBAC: grants any field whose required role is on the token.",
                "start": "1900-01-01T00:00:00+00:00",
                "end": None,
            },
            {
                "id": OWNER_UUID,
                "name": "Owner",
                "description": "Grants owners access to the entities they own. A default starter policy; customize or remove it as needed.",
                "start": "1900-01-01T00:00:00+00:00",
                "end": None,
            },
        ],
    )
    op.bulk_insert(
        policy_actor,
        [
            {"kind": "role", "value": "admin", "policy_fk": POLICYADMIN_UUID},
            {"kind": "role", "value": "admin", "policy_fk": ADMINISTRATOR_UUID},
            {"kind": "role", "value": "reader", "policy_fk": READER_UUID},
            {"kind": "all", "value": "", "policy_fk": LEGACY_UUID},
            {"kind": "role", "value": "owner", "policy_fk": OWNER_UUID},
        ],
    )
    op.bulk_insert(
        policy_rule,
        [
            *[
                {
                    "type": t,
                    "field": f,
                    "condition": None,
                    "filter": None,
                    "policy_fk": POLICYADMIN_UUID,
                }
                for t, f in POLICYADMIN_RULES
            ],
            {
                "type": "Query",
                "field": "*",
                "condition": None,
                "filter": None,
                "policy_fk": ADMINISTRATOR_UUID,
            },
            {
                "type": "Mutation",
                "field": "*",
                "condition": None,
                "filter": None,
                "policy_fk": ADMINISTRATOR_UUID,
            },
            {
                "type": "Query",
                "field": "*",
                "condition": None,
                "filter": None,
                "policy_fk": READER_UUID,
            },
            *[
                {
                    "type": t,
                    "field": f,
                    "condition": c,
                    "filter": None,
                    "policy_fk": LEGACY_UUID,
                }
                for t, f, c in LEGACY_RULES
            ],
            *[
                {
                    "type": "Mutation",
                    "field": field,
                    "condition": None,
                    "filter": flt,
                    "policy_fk": OWNER_UUID,
                }
                for field, flt in OWNER_RULES
            ],
        ],
    )


def downgrade() -> None:
    ids = f"'{POLICYADMIN_UUID}', '{ADMINISTRATOR_UUID}', '{READER_UUID}', '{LEGACY_UUID}', '{OWNER_UUID}'"
    op.execute(f"DELETE FROM policy_rule WHERE policy_fk IN ({ids})")
    op.execute(f"DELETE FROM policy_actor WHERE policy_fk IN ({ids})")
    op.execute(f"DELETE FROM policy WHERE id IN ({ids})")
