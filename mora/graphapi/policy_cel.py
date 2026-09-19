# SPDX-FileCopyrightText: Magenta ApS <https://magenta.dk>
# SPDX-License-Identifier: MPL-2.0
"""The conditions a read rule narrows its objects by, written in CEL."""

import json
from functools import lru_cache
from operator import methodcaller
from typing import Any

from cel_expr_python import cel  # type: ignore[import-untyped]

from mora.auth.keycloak.models import Token

# A condition is written against the caller alone, so the token is all it names
_ENV = cel.NewEnv(variables={"token": cel.Type.Map(cel.Type.STRING, cel.Type.DYN)})


@lru_cache(maxsize=2048)
def _compile(condition: str) -> Any:
    """Compile a condition into a program, the same one being run every request."""
    return _ENV.compile(condition)


def evaluate(condition: str, token: Token) -> dict[str, Any]:
    """The filter a condition names for the caller, as the filter map it yields."""
    activation = _ENV.Activation(
        {
            "token": {
                "uuid": str(token.uuid) if token.uuid is not None else None,
                "preferred_username": token.preferred_username,
                # A list rather than a set: CEL has no set type
                "roles": list(token.realm_access.roles),
            }
        }
    )
    result = _compile(condition).eval(activation)
    if result.type() == cel.Type.ERROR:
        raise ValueError(f"condition {condition!r} failed: {result.value()}")
    # A CEL value serialises no further than its own type, so each is unwrapped
    # as it is reached
    return json.loads(json.dumps(result, default=methodcaller("value")))
