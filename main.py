# SPDX-FileCopyrightText: 2019-2020 Magenta ApS
#
# SPDX-License-Identifier: MPL-2.0
import asyncio
import json
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


routing_keys: List[str] = [
    "employee.employee.create",
    "employee.employee.edit",
    "employee.employee.terminate",
    "employee.engagement.create",
    "employee.engagement.edit",
    "employee.engagement.terminate",
]


updater: Optional[MOPrimaryEngagementUpdater] = None


def calculate_user(uuid: UUID) -> None:
    print(f"Recalculating user: {uuid}")
    try:
        updater.recalculate_user(uuid)  # type: ignore
    except Exception as exp:
        print(exp)


def on_message(message: IncomingMessage) -> None:
    with message.process():
        payload = json.loads(message.body)
        employee_uuid = payload["uuid"]

        print(
            json.dumps({"routing-key": message.routing_key, "body": payload}, indent=4)
        )
        calculate_user(employee_uuid)


async def main(
    integration: str,
    dry_run: bool,
    host: str,
    port: int,
    username: str,
    password: str,
    exchange: str,
    os2mo_url: str,
) -> None:
    print("Configuring calculate-primary logging")
    setup_logging()

    print(f"Acquiring updater: {integration}")
    updater_class = get_engagement_updater(integration)
    print(f"Got class: {updater_class}")
    global updater
    updater = updater_class(
        settings={
            "mora.base": os2mo_url,
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
)
def cli(**kwargs: Any) -> None:
    loop = asyncio.get_event_loop()
    # Setup everything
    loop.run_until_complete(main(**kwargs))
    # Run forever listening to messages
    loop.run_forever()
    loop.close()


if __name__ == "__main__":
    cli(auto_envvar_prefix="AMQP")
