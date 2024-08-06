# SPDX-FileCopyrightText: 2019-2020 Magenta ApS
#
# SPDX-License-Identifier: MPL-2.0
"""Event-driven recalculate primary program."""
import asyncio
from functools import partial
from uuid import UUID

import click
from prometheus_client import Counter
from prometheus_client import Gauge
from prometheus_client import start_http_server
from ramqp.moqp import MOAMQPSystem
from ramqp.moqp import ObjectType
from ramqp.moqp import PayloadType
from ramqp.moqp import RequestType
from ramqp.moqp import ServiceType

from calculate_primary.calculate_primary import get_engagement_updater
from calculate_primary.common import MOPrimaryEngagementUpdater
from calculate_primary.config import Settings

edit_counter = Counter("recalculate_edit", "Number of edits made")
no_edit_counter = Counter("recalculate_no_edit", "Number of noops made")
last_processing = Gauge(
    "recalculate_last_processing", "Timestamp of the last processing"
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


def _setup_updater(settings: Settings) -> MOPrimaryEngagementUpdater:
    """Exchange integration to updater.

    Args:
        settings

    Returns:
        The constructed updater.
    """
    print("Configuring calculate-primary logging")

    print(f"Acquiring updater: {settings.amqp_integration}")
    updater_class = get_engagement_updater(settings.amqp_integration)
    print(f"Got class: {updater_class}")
    updater: MOPrimaryEngagementUpdater = updater_class(settings)
    print(f"Got object: {updater}")
    return updater


def _setup_metrics() -> None:
    """Serve metrics on port 8000.

    Called for the side-effect of starting a seperate thread to serve metrics.

    Returns:
        None
    """
    print("Start metrics server")
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
# pylint: disable=too-many-arguments
def cli(
    host: str,
    port: int,
    username: str,
    password: str,
    exchange: str,
) -> None:
    """Click entrypoint."""
    _setup_metrics()

    settings = Settings()
    updater = _setup_updater(settings=settings)
    amqp_url = f"amqp://{username}:{password}@{host}:{port}"
    _run_amqp(updater, amqp_url, exchange)


if __name__ == "__main__":
    cli(auto_envvar_prefix="AMQP")  # pylint: disable=no-value-for-parameter
