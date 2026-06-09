# SPDX-FileCopyrightText: Magenta ApS <https://magenta.dk>
# SPDX-License-Identifier: MPL-2.0
from .oio_base import OIORestObject
from .oio_base import OIOStandardHierarchy


# MARK: cannot delete (transitively through mora/lora.py::BaseScope)
class Facet(OIORestObject):
    """
    Implement a Facet  - manage access to database layer from the API.
    """

    pass


# MARK: cannot delete (transitively through mora/lora.py::BaseScope)
class Klasse(OIORestObject):
    """
    Implement a Klasse  - manage access to database layer from the API.
    """

    pass


# MARK: can delete
class Klassifikation(OIORestObject):
    """
    Implement a Klassifikation  - manage access to database from the API.
    """

    pass


# MARK: can delete
class KlassifikationsHierarki(OIOStandardHierarchy):
    """Implement the Klassifikation Standard."""

    _name = "Klassifikation"
    _classes = [
        Facet,
        Klasse,
        Klassifikation,
    ]
