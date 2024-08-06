# SPDX-FileCopyrightText: 2019-2020 Magenta ApS
#
# SPDX-License-Identifier: MPL-2.0
# pylint: disable=redefined-outer-name,protected-access
"""This module contains pytest specific code, fixtures and helpers."""
import os
from typing import Iterator

import pytest

from calculate_primary.config import Settings


@pytest.fixture
def settings_overrides() -> Iterator[dict[str, str]]:
    """Fixture to construct dictionary of minimal overrides for valid settings.

    Yields:
        Minimal set of overrides.
    """
    overrides = {
        "amqp_integration": "DEFAULT",
        "CLIENT_ID": "Foo",
        "CLIENT_SECRET": "bar",
        "FASTRAMQPI__AMQP__URL": "amqp://guest:guest@msg-broker:5672/",
    }
    yield overrides


@pytest.fixture
def load_settings_overrides(
    monkeypatch: pytest.MonkeyPatch,
    settings_overrides: dict[str, str],
) -> Iterator[dict[str, str]]:
    """Fixture to set happy-path settings overrides as environmental variables.

    Note:
        Only loads environmental variables, if variables are not already set.

    Args:
        settings_overrides: The list of settings to load in.
        monkeypatch: Pytest MonkeyPatch instance to set environmental variables.

    Yields:
        Minimal set of overrides.
    """
    for key, value in settings_overrides.items():
        if os.environ.get(key) is None:
            monkeypatch.setenv(key, value)
    yield settings_overrides


@pytest.fixture
def dummy_settings(load_settings_overrides) -> Iterator[dict[str, str]]:
    yield Settings()
