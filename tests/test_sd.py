from datetime import datetime
from unittest.mock import MagicMock
from uuid import uuid4

from calculate_primary.config import Settings

from .test_primary import MOPrimaryEngagementUpdaterTest
from calculate_primary.sd import SDPrimaryEngagementUpdater

class SDPrimaryEngagementUpdaterTest(SDPrimaryEngagementUpdater):
    # copied from test_primary but without overwriting _find_primary
    
    def _get_mora_helper(self, mora_base):
        morahelper_mock = MagicMock()
        morahelper_mock.read_organisation.return_value = "org_uuid"
        return morahelper_mock

    def _find_primary_types(self):
        primary_dict = {
            "fixed_primary": "fixed_primary_uuid",
            "primary": "primary_uuid",
            "non_primary": "non_primary_uuid",
            "special_primary": "special_primary_uuid",
        }
        primary_list = [
            primary_dict["fixed_primary"],
            primary_dict["primary"],
            primary_dict["special_primary"],
        ]
        return primary_dict, primary_list


class ResponseOK:
    status_code = 200


def test_sd_non_integer_user_key(dummy_settings):
    # Arrange
    updater = SDPrimaryEngagementUpdaterTest(dummy_settings)
    updater.helper = MagicMock()
    updater.helper._mo_post.return_value = ResponseOK()
    uuid_primary_engagement = str(uuid4())
    mo_engagements = [
        {
            "uuid": uuid_primary_engagement,
            "user_key": "123",
            "primary": {"uuid": "non_primary_uuid"},
        },
        {
            "uuid": str(uuid4()),
            "user_key": "EAAYT",
            "primary": {"uuid": "non_primary_uuid"},
        },
    ]

    updater._read_engagement = MagicMock(return_value=mo_engagements)
    updater.helper.find_cut_dates = MagicMock(
        return_value=(
            datetime.fromisoformat("2024-01-14"),
            datetime.max,
        )
    )

    # Act
    updater.recalculate_user("User_uuid")

    # Assert
    updater.helper._mo_post.assert_called_once_with(
        "details/edit",
        {
            "type": "engagement",
            "uuid": uuid_primary_engagement,
            "data": {
                "primary": {"uuid": "primary_uuid"},
                "validity": {"from": "2024-01-14", "to": None},
            },
        },
    )


def test_sd_non_integer_user_key_only_engagement(dummy_settings):
    # Arrange
    updater = SDPrimaryEngagementUpdaterTest(dummy_settings)
    updater.helper = MagicMock()
    updater.helper._mo_post.return_value = ResponseOK()
    uuid_primary_engagement = str(uuid4())
    mo_engagements = [
        {
            "uuid": uuid_primary_engagement,
            "user_key": "EAAYT",
            "primary": {"uuid": "non_primary_uuid"},
        },
    ]

    updater._read_engagement = MagicMock(return_value=mo_engagements)
    updater.helper.find_cut_dates = MagicMock(
        return_value=(
            datetime.fromisoformat("2024-01-14"),
            datetime.max,
        )
    )

    # Act
    updater.recalculate_user("User_uuid")

    updater.helper._mo_post.assert_called_once_with(
        "details/edit",
        {
            "type": "engagement",
            "uuid": uuid_primary_engagement,
            "data": {
                "primary": {"uuid": "primary_uuid"},
                "validity": {"from": "2024-01-14", "to": None},
            },
        },
    )


def test_sd_by_fraction(dummy_settings):
    # Arrange
    updater = SDPrimaryEngagementUpdaterTest(dummy_settings)
    updater.helper = MagicMock()
    updater.helper._mo_post.return_value = ResponseOK()
    uuid_primary_engagement = str(uuid4())
    mo_engagements = [
        {
            "uuid": uuid_primary_engagement,
            "user_key": "10",
            "fraction": "100",
            "primary": {"uuid": "non_primary_uuid"},
        },
        {
            "uuid": str(uuid4()),
            "user_key": "100",
            "fraction": "10",
            "primary": {"uuid": "non_primary_uuid"},
        },
    ]

    updater._read_engagement = MagicMock(return_value=mo_engagements)
    updater.helper.find_cut_dates = MagicMock(
        return_value=(
            datetime.fromisoformat("2024-01-14"),
            datetime.max,
        )
    )

    # Act
    updater.recalculate_user("User_uuid")

    # Assert
    updater.helper._mo_post.assert_called_once_with(
        "details/edit",
        {
            "type": "engagement",
            "uuid": uuid_primary_engagement,
            "data": {
                "primary": {"uuid": "primary_uuid"},
                "validity": {"from": "2024-01-14", "to": None},
            },
        },
    )


def test_sd_by_user_key(dummy_settings):
    # Arrange
    updater = SDPrimaryEngagementUpdaterTest(dummy_settings)
    updater.helper = MagicMock()
    updater.helper._mo_post.return_value = ResponseOK()
    uuid_primary_engagement = str(uuid4())
    mo_engagements = [
        {
            "uuid": uuid_primary_engagement,
            "user_key": "10",
            "fraction": "1",
            "primary": {"uuid": "non_primary_uuid"},
        },
        {
            "uuid": str(uuid4()),
            "user_key": "100",
            "fraction": "1",
            "primary": {"uuid": "non_primary_uuid"},
        },
    ]

    updater._read_engagement = MagicMock(return_value=mo_engagements)
    updater.helper.find_cut_dates = MagicMock(
        return_value=(
            datetime.fromisoformat("2024-01-14"),
            datetime.max,
        )
    )

    # Act
    updater.recalculate_user("User_uuid")

    # Assert
    updater.helper._mo_post.assert_called_once_with(
        "details/edit",
        {
            "type": "engagement",
            "uuid": uuid_primary_engagement,
            "data": {
                "primary": {"uuid": "primary_uuid"},
                "validity": {"from": "2024-01-14", "to": None},
            },
        },
    )
