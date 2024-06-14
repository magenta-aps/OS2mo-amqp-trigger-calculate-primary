# SPDX-FileCopyrightText: 2019-2020 Magenta ApS
#
# SPDX-License-Identifier: MPL-2.0
"""Event-driven recalculate primary program."""
from pathlib import Path
from typing import List
from uuid import UUID

from prometheus_client import Counter
from prometheus_client import Gauge
from prometheus_client import Info

from calculate_primary.calculate_primary import get_engagement_updater
from calculate_primary.calculate_primary import setup_logging
from calculate_primary.common import MOPrimaryEngagementUpdater
from calculate_primary.config import Settings


edit_counter = Counter("recalculate_edit", "Number of edits made")
no_edit_counter = Counter("recalculate_no_edit", "Number of noops made")
last_processing = Gauge(
    "recalculate_last_processing", "Timestamp of the last processing"
)
version_info = Info("recalculate_build_version", "Version information")


def export_version_metric() -> None:
    """Read local files and update version_info metric.

    Called for the side-effect of updating the metrics.

    Returns:
        None
    """
    poetry_version = Path("VERSION").read_text("utf-8").strip()
    commit_hash = Path("HASH").read_text("utf-8").strip()

    version_info.info(
        {
            "version": poetry_version,
            "commit_hash": commit_hash,
        }
    )


def calculate_user(updater: MOPrimaryEngagementUpdater, uuid: UUID) -> None:
    """Recalculate the user given by uuid.

    Called for the side-effect of making calls against MO using the updater.

    Args:
        updater: The calculate primary updater instance.
        uuid: UUID for the user to recalculate.

    Returns:
        None
    """
    print(f"Recalculating user: {uuid}")
    last_processing.set_to_current_time()
    # TODO: An async version would be desireable
    updates = updater.recalculate_user(uuid)
    # Update edit metrics
    for number_of_edits in updates.values():
        if number_of_edits == 0:
            no_edit_counter.inc()
        edit_counter.inc(number_of_edits)


def _setup_updater(
    settings: Settings,
) -> MOPrimaryEngagementUpdater:
    """Exchange integration to updater.

    Args:
        integration: The integration to construct.
        dry_run: Whether to dry-run the updater.
        mo_url: URL for OS2mo.

    Returns:
        The constructed updater.
    """
    print("Configuring calculate-primary logging")
    setup_logging()

    print(f"Acquiring updater: {settings.integration}")
    updater_class = get_engagement_updater(settings.integration)
    print(f"Got class: {updater_class}")
    updater: MOPrimaryEngagementUpdater = updater_class(settings)
    print(f"Got object: {updater}")
    return updater
