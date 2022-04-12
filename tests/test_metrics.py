# SPDX-FileCopyrightText: 2019-2020 Magenta ApS
#
# SPDX-License-Identifier: MPL-2.0
"""This module tests that metrics are updated as expected."""
from typing import Any
from typing import cast
from typing import Dict
from unittest.mock import mock_open
from unittest.mock import patch
from uuid import UUID
from uuid import uuid4

import pytest
from ra_utils.attrdict import attrdict

from calculate_primary.main import calculate_user
from calculate_primary.main import edit_counter
from calculate_primary.main import export_version_metric
from calculate_primary.main import last_processing
from calculate_primary.main import no_edit_counter
from calculate_primary.main import version_info


def get_metric_value(metric: Any) -> float:
    """Get the value of a given metric.

    Args:
        metric: The metric to query.

    Returns:
        The metric value.
    """
    # pylint: disable=protected-access
    metric = metric._value
    return cast(float, metric.get())


def clear_metric_value(metric: Any) -> None:
    """Clear the value of a given metric.

    Args:
        metric: The metric to query.

    Returns:
        None
    """
    # pylint: disable=protected-access
    metric = metric._value
    metric.set(0.0)


def test_calculate_user_metrics() -> None:
    """Test that calculate_user sets metrics as expected."""
    clear_metric_value(last_processing)
    clear_metric_value(edit_counter)
    clear_metric_value(no_edit_counter)

    def recalculate_user(_: UUID) -> dict:
        return {}

    updater = attrdict({"recalculate_user": recalculate_user})

    assert get_metric_value(last_processing) == 0.0
    assert get_metric_value(edit_counter) == 0.0
    assert get_metric_value(no_edit_counter) == 0.0

    last_call_time = get_metric_value(last_processing)
    calculate_user(updater, uuid4())

    assert last_call_time < get_metric_value(last_processing)
    assert get_metric_value(last_processing) != 0.0
    assert get_metric_value(edit_counter) == 0.0
    assert get_metric_value(no_edit_counter) == 0.0

    last_call_time = get_metric_value(last_processing)
    calculate_user(updater, uuid4())

    assert last_call_time < get_metric_value(last_processing)
    assert get_metric_value(last_processing) != 0.0
    assert get_metric_value(edit_counter) == 0.0
    assert get_metric_value(no_edit_counter) == 0.0


def test_calculate_user_metrics_edits() -> None:
    """Test that calculate_user sets metrics as expected."""
    clear_metric_value(last_processing)
    clear_metric_value(edit_counter)
    clear_metric_value(no_edit_counter)

    increment = 1

    def recalculate_user(uuid: UUID) -> dict:
        return {uuid: increment}

    updater = attrdict({"recalculate_user": recalculate_user})

    calculate_user(updater, uuid4())

    assert get_metric_value(edit_counter) == 1.0
    assert get_metric_value(no_edit_counter) == 0.0

    calculate_user(updater, uuid4())

    assert get_metric_value(edit_counter) == 2.0
    assert get_metric_value(no_edit_counter) == 0.0

    increment = 0
    calculate_user(updater, uuid4())

    assert get_metric_value(edit_counter) == 2.0
    assert get_metric_value(no_edit_counter) == 1.0

    calculate_user(updater, uuid4())

    assert get_metric_value(edit_counter) == 2.0
    assert get_metric_value(no_edit_counter) == 2.0

    increment = 40
    calculate_user(updater, uuid4())

    assert get_metric_value(edit_counter) == 42.0
    assert get_metric_value(no_edit_counter) == 2.0

    increment = 6900
    calculate_user(updater, uuid4())

    assert get_metric_value(edit_counter) == 6942.0
    assert get_metric_value(no_edit_counter) == 2.0

    increment = 0
    calculate_user(updater, uuid4())

    assert get_metric_value(edit_counter) == 6942.0
    assert get_metric_value(no_edit_counter) == 3.0


def test_version_metric() -> None:
    """Test that the version metric works as expected."""

    def fetch_version_info() -> Dict[str, str]:
        # pylint: disable=protected-access
        return version_info._value

    assert fetch_version_info() == {}

    with pytest.raises(FileNotFoundError):
        export_version_metric()

    with patch("pathlib.Path.open", mock_open(read_data="dummy")):
        export_version_metric()

    assert fetch_version_info() == {"version": "dummy", "commit_hash": "dummy"}

    def files_for_test(path: str, **_: Dict[str, Any]) -> Any:
        contents = {
            "VERSION": "1.2.3",
            "HASH": "39e444a4e58e425ca64cc76604e81a14e4a42b6b",
        }
        data = contents[str(path)]
        mock = mock_open(read_data=data)
        return mock.return_value

    with patch("pathlib.Path.open", files_for_test):
        export_version_metric()

    assert fetch_version_info() == {
        "version": "1.2.3",
        "commit_hash": "39e444a4e58e425ca64cc76604e81a14e4a42b6b",
    }
