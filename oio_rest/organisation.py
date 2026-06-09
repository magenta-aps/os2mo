# SPDX-FileCopyrightText: Magenta ApS <https://magenta.dk>
# SPDX-License-Identifier: MPL-2.0
from .oio_base import OIORestObject
from .oio_base import OIOStandardHierarchy


# MARK: cannot delete (referenced outside of LoRa)
class Bruger(OIORestObject):
    """
    Implement a Bruger  - manage access to database layer from the API.
    """

    pass


# MARK: cannot delete (transitively through mora/lora.py::BaseScope)
class ItSystem(OIORestObject):
    """
    Implement an ItSystem  - manage access to database from the API.
    """

    pass


# MARK: cannot delete (referenced outside of LoRa)
class Organisation(OIORestObject):
    """
    Implement an Organisation  - manage access to database from the API.
    """

    pass


# MARK: cannot delete (referenced outside of LoRa)
class OrganisationEnhed(OIORestObject):
    """
    Implement an OrganisationEnhed - manage access to database from the API.
    """

    pass


# MARK: cannot delete (transitively through mora/lora.py::BaseScope)
class OrganisationFunktion(OIORestObject):
    """
    Implement an OrganisationFunktion.
    """

    pass


# MARK: can delete
class OrganisationsHierarki(OIOStandardHierarchy):
    """Implement the Organisation Standard."""

    _name = "Organisation"
    _classes = [
        Bruger,
        ItSystem,
        Organisation,
        OrganisationEnhed,
        OrganisationFunktion,
    ]
