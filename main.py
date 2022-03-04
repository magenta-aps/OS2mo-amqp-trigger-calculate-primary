# SPDX-FileCopyrightText: 2019-2020 Magenta ApS
#
# SPDX-License-Identifier: MPL-2.0
import asyncio
from pathlib import Path

import click
import structlog
from integrations.calculate_primary.calculate_primary import get_engagement_updater
from integrations.calculate_primary.calculate_primary import setup_logging
from prometheus_client import Counter
from prometheus_client import Gauge
from prometheus_client import Info
from prometheus_client import start_http_server

from amqp import AMQPSystem
from amqp import PayloadType
from amqp import strip_routing

version_info = Info("recalculate_build_version", "Version information")

poetry_version = Path("VERSION").read_text().strip()
commit_hash = Path("HASH").read_text().strip()

version_info.info(
    {
        "version": poetry_version,
        "commit_hash": commit_hash,
    }
)

last_processing = Gauge(
    "recalculate_last_processing", "Timestamp of the last processing"
)
edit_counter = Counter("recalculate_edit", "Number of edits made")
no_edit_counter = Counter("recalculate_no_edit", "Number of noops made")


logger = structlog.get_logger()


@click.command()
@click.option(
    "--integration",
    type=click.Choice(["DEFAULT", "SD", "OPUS"], case_sensitive=False),
    required=True,
    help="Integration to use",
)
@click.option("--dry-run", is_flag=True, type=click.BOOL, help="Make no changes")
@click.option(
    "--mo-url",
    help="OS2mo URL",
    required=True,
    envvar="MO_URL",
)
def cli(
    integration: str,
    dry_run: bool,
    mo_url: str,
) -> None:
    amqpsystem = AMQPSystem(queue_name="test")

    setup_logging()

    logger.info("Acquiring updater", integration=integration)
    updater_class = get_engagement_updater(integration)
    logger.debug("Updater class", updater_class=updater_class)
    updater = updater_class(
        settings={
            "mora.base": mo_url,
        },
        dry_run=dry_run,
    )
    logger.debug("Updater object", updater_object=updater)

    @amqpsystem.register("employee", "employee", "CREATE")
    @amqpsystem.register("employee", "employee", "EDIT")
    @amqpsystem.register("employee", "employee", "TERMINATE")
    @amqpsystem.register("employee", "engagement", "CREATE")
    @amqpsystem.register("employee", "engagement", "EDIT")
    @amqpsystem.register("employee", "engagement", "TERMINATE")
    @strip_routing
    async def calculate_user(
        payload: PayloadType,
    ) -> None:
        uuid = payload.uuid
        print(f"Recalculating user: {uuid}")
        last_processing.set_to_current_time()
        # TODO: This should probably be async
        updates = updater.recalculate_user(uuid)  # type: ignore
        # Update edit metrics
        for number_of_edits in updates.values():
            if number_of_edits == 0:
                no_edit_counter.inc()
            edit_counter.inc(number_of_edits)

    # TODO: Consider ASGI server and make_asgi_app
    start_http_server(8000)

    loop = asyncio.get_event_loop()
    # Setup everything
    loop.run_until_complete(amqpsystem.run())
    # Run forever listening to messages
    loop.run_forever()
    loop.close()


if __name__ == "__main__":
    cli(auto_envvar_prefix="AMQP")
