# SPDX-FileCopyrightText: 2019-2020 Magenta ApS
#
# SPDX-License-Identifier: MPL-2.0
"""Event-driven recalculate primary program."""
import asyncio
from functools import partial
from pathlib import Path
from uuid import UUID

import click
from integrations.calculate_primary.calculate_primary import get_engagement_updater
from integrations.calculate_primary.calculate_primary import setup_logging
from integrations.calculate_primary.common import MOPrimaryEngagementUpdater
from prometheus_client import Counter
from prometheus_client import Gauge
from prometheus_client import Info
from prometheus_client import start_http_server
from ramqp.moqp import MOAMQPSystem
from ramqp.moqp import ObjectType
from ramqp.moqp import PayloadType
from ramqp.moqp import RequestType
from ramqp.moqp import ServiceType


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
    integration: str, dry_run: bool, mo_url: str
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

    print(f"Acquiring updater: {integration}")
    updater_class = get_engagement_updater(integration)
    print(f"Got class: {updater_class}")
    updater: MOPrimaryEngagementUpdater = updater_class(
        settings={
            "mora.base": mo_url,
        },
        dry_run=dry_run,
    )
    print(f"Got object: {updater}")
    return updater


def _setup_metrics() -> None:
    """Serve metrics on port 8000.

    Called for the side-effect of starting a seperate thread to serve metrics.

    Returns:
        None
    """
    print("Start metrics server")
    export_version_metric()
    # TODO: Consider ASGI server and make_asgi_app
    start_http_server(8000)


def _run_amqp(
    updater: MOPrimaryEngagementUpdater,
    amqp_url: str,
    exchange: str,
) -> None:
    """Start listening and processing AMQP messages.

    Called for the side-effect of consuming messages and making callbacks.

    Args:
        updater: The updater to provide to calculate_user.
        amqp_url: The AMQP to connect to.
        exchange: The AMQP exchange to connect to.

    Returns:
        None
    """
    amqp_system = MOAMQPSystem()

    @amqp_system.register(ServiceType.EMPLOYEE, ObjectType.EMPLOYEE, RequestType.CREATE)
    @amqp_system.register(ServiceType.EMPLOYEE, ObjectType.EMPLOYEE, RequestType.EDIT)
    @amqp_system.register(
        ServiceType.EMPLOYEE, ObjectType.EMPLOYEE, RequestType.TERMINATE
    )
    @amqp_system.register(
        ServiceType.EMPLOYEE, ObjectType.ENGAGEMENT, RequestType.CREATE
    )
    @amqp_system.register(ServiceType.EMPLOYEE, ObjectType.ENGAGEMENT, RequestType.EDIT)
    @amqp_system.register(
        ServiceType.EMPLOYEE, ObjectType.ENGAGEMENT, RequestType.TERMINATE
    )
    async def callback_function(
        _1: ServiceType,
        _2: ObjectType,
        _3: RequestType,
        payload: PayloadType,
    ) -> None:
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, partial(calculate_user, updater, payload.uuid))

    print("Start AMQP system")
    amqp_system.run_forever(
        queue_prefix="calculate-primary",
        amqp_url=amqp_url,
        amqp_exchange=exchange,
    )


@click.command()
@click.option(
    "--integration",
    type=click.Choice(["DEFAULT", "SD", "OPUS"], case_sensitive=False),
    required=True,
    help="Integration to use",
)
@click.option("--dry-run", is_flag=True, type=click.BOOL, help="Make no changes")
@click.option(
    "--host",
    default="localhost",
    help="AMQP host",
    show_default=True,
)
@click.option(
    "--port",
    type=click.INT,
    default=5672,
    help="AMQP port",
    show_default=True,
)
@click.option(
    "--username",
    default="guest",
    help="AMQP username",
    show_default=True,
)
@click.option(
    "--password",
    prompt=True,
    hide_input=True,
    required=True,
    help="AMQP password",
)
@click.option(
    "--exchange",
    default="os2mo",
    help="AMQP exchange",
    show_default=True,
)
@click.option(
    "--mo-url",
    help="OS2mo URL",
    required=True,
    envvar="MO_URL",
)
# pylint: disable=too-many-arguments
def cli(
    integration: str,
    dry_run: bool,
    host: str,
    port: int,
    username: str,
    password: str,
    exchange: str,
    mo_url: str,
) -> None:
    """Click entrypoint."""
    _setup_metrics()

    updater = _setup_updater(integration, dry_run, mo_url)
    amqp_url = f"amqp://{username}:{password}@{host}:{port}"
    _run_amqp(updater, amqp_url, exchange)


if __name__ == "__main__":
    cli(auto_envvar_prefix="AMQP")  # pylint: disable=no-value-for-parameter
