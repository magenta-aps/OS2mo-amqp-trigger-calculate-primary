# SPDX-FileCopyrightText: 2019-2020 Magenta ApS
#
# SPDX-License-Identifier: MPL-2.0
import asyncio
import json
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any
from typing import List
from typing import Optional
from uuid import UUID
from uuid import uuid4

import click
from aio_pika import connect
from aio_pika import ExchangeType
from aio_pika import IncomingMessage
from integrations.calculate_primary.calculate_primary import get_engagement_updater
from integrations.calculate_primary.calculate_primary import setup_logging
from integrations.calculate_primary.common import MOPrimaryEngagementUpdater
from prometheus_client import Counter
from prometheus_client import Gauge
from prometheus_client import Histogram
from prometheus_client import Info
from prometheus_client import start_http_server


routing_keys: List[str] = [
    "employee.employee.create",
    "employee.employee.edit",
    "employee.employee.terminate",
    "employee.engagement.create",
    "employee.engagement.edit",
    "employee.engagement.terminate",
]

# TODO: Tracing of AMQP messages
event_counter = Counter(
    "recalculate_events", "AMQP Events", ["service", "object_type", "action"]
)
edit_counter = Counter("recalculate_edit", "Number of edits made")
no_edit_counter = Counter("recalculate_no_edit", "Number of noops made")
exception_counter = Counter("recalculate_exceptions", "Exception counter")
processing_time = Histogram(
    "recalculate_processing_seconds", "Time spent running recalculate_user"
)
processing_inprogress = Gauge(
    "recalculate_inprogress", "Number of recalculate_user currently running"
)
last_processing = Gauge(
    "recalculate_last_processing", "Timestamp of the last processing"
)
last_periodic = Gauge(
    "recalculate_last_periodic", "Timestamp of the last periodic call"
)
last_message_time = Gauge("recalculate_last_message", "Timestamp from last message")
last_heartbeat = Gauge(
    "recalculate_last_heartbeat", "Time of the last connection heartbeat"
)
backlog_count = Gauge(
    "recalculate_backlog", "Number of messages waiting for processing in the backlog"
)

version_info = Info("recalculate_build_version", "Version information")

poetry_version = Path("VERSION").read_text().strip()
commit_hash = Path("HASH").read_text().strip()

version_info.info(
    {
        "version": poetry_version,
        "commit_hash": commit_hash,
    }
)


updater: Optional[MOPrimaryEngagementUpdater] = None


@processing_inprogress.track_inprogress()
@processing_time.time()
def calculate_user(uuid: UUID) -> None:
    print(f"Recalculating user: {uuid}")
    last_processing.set_to_current_time()
    # TODO: This should probably be async
    updates = updater.recalculate_user(uuid)  # type: ignore
    # Update edit metrics
    for number_of_edits in updates.values():
        if number_of_edits == 0:
            no_edit_counter.inc()
        edit_counter.inc(number_of_edits)


def on_message(message: IncomingMessage) -> None:
    try:
        with exception_counter.count_exceptions(), message.process():
            service, object_type, action = message.routing_key.split(".")
            event_counter.labels(service, object_type, action).inc()

            payload = json.loads(message.body)
            print(
                json.dumps(
                    {"routing-key": message.routing_key, "body": payload}, indent=4
                )
            )

            message_time = datetime.fromisoformat(payload["time"])
            last_message_time.set(message_time.timestamp())

            employee_uuid = payload["uuid"]
            calculate_user(employee_uuid)
    except Exception:
        print(traceback.format_exc())


async def main(
    integration: str,
    dry_run: bool,
    host: str,
    port: int,
    username: str,
    password: str,
    exchange: str,
    mo_url: str,
) -> None:
    print("Configuring calculate-primary logging")
    setup_logging()

    print(f"Acquiring updater: {integration}")
    updater_class = get_engagement_updater(integration)
    print(f"Got class: {updater_class}")
    global updater
    updater = updater_class(
        settings={
            "mora.base": mo_url,
        },
        dry_run=dry_run,
    )
    print(f"Got object: {updater}")

    print(f"Establishing AMQP connection to amqp://{username}:xxxxx@{host}:{port}/")
    connection = await connect(f"amqp://{username}:{password}@{host}:{port}/")

    print("Creating AMQP channel")
    channel = await connection.channel()
    await channel.set_qos(prefetch_count=1)

    print("Attaching AMQP exchange to channel")
    topic_logs_exchange = await channel.declare_exchange(exchange, ExchangeType.TOPIC)

    # Declaring queue
    queue_name = "os2mo-consumer-" + str(uuid4())
    print(f"Declaring unique message queue: {queue_name}")
    queue = await channel.declare_queue(queue_name, durable=False)

    for key in routing_keys:
        print(f"Binding routing-key: {key}")
        await queue.bind(topic_logs_exchange, routing_key=key)

    print("Listening for messages")
    await queue.consume(on_message)

    # Setup metrics
    async def periodic_metrics() -> None:
        while True:
            last_periodic.set_to_current_time()
            last_heartbeat.set(connection.heartbeat_last)
            backlog_count.set(queue.declaration_result.message_count)
            await asyncio.sleep(5)

    asyncio.create_task(periodic_metrics())


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
def cli(**kwargs: Any) -> None:
    # TODO: Consider ASGI server and make_asgi_app
    start_http_server(8000)

    loop = asyncio.get_event_loop()
    # Setup everything
    loop.create_task(main(**kwargs))
    # Run forever listening to messages
    loop.run_forever()
    loop.close()


if __name__ == "__main__":
    cli(auto_envvar_prefix="AMQP")
