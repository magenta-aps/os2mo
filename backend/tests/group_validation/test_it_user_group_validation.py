# SPDX-FileCopyrightText: 2022 Magenta ApS <https://magenta.dk>
# SPDX-License-Identifier: MPL-2.0
import pytest

from mora.exceptions import HTTPException
from mora.service.itsystem import ITUserPrimaryGroupValidation
from mora.service.itsystem import ITUserUniqueGroupValidation


class TestITUserUniqueGroupValidation:
    def test_validate_additional_object(self):
        obj = {
            "employee_uuid": "uuid",
            "it_system_uuid": "uuid",
            "it_user_username": "uuid",
        }
        validation = ITUserUniqueGroupValidation([obj])
        with pytest.raises(HTTPException):
            validation.add_validation_item(obj).validate()


class TestITAssociationPrimaryGroupValidation:
    def test_validate_additional_object(self):
        obj = {"it_system_uuid": "uuid", "is_primary": True}
        validation = ITUserPrimaryGroupValidation([obj])
        with pytest.raises(HTTPException):
            validation.add_validation_item(obj).validate()