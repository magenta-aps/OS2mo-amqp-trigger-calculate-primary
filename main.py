# SPDX-FileCopyrightText: 2019-2020 Magenta ApS
#
# SPDX-License-Identifier: MPL-2.0
import asyncio
import json
from typing import Any
from typing import List
from uuid import uuid4

import click
from aio_pika import connect
from aio_pika import ExchangeType
from aio_pika import IncomingMessage


def on_message(message: IncomingMessage) -> None:
    with message.process():
        print(
            json.dumps(
                {"routing-key": message.routing_key, "body": json.loads(message.body)},
                indent=4,
            )
        )


async def main(
    host: str,
    port: int,
    username: str,
    password: str,
    exchange: str,
    routing_key: List[str],
) -> None:
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

    for key in routing_key:
        print(f"Binding routing-key: {key}")
        await queue.bind(topic_logs_exchange, routing_key=key)

    print("Listening for messages")
    await queue.consume(on_message)


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
@click.option(
    "--routing-key",
    help="AMQP routing keys",
    multiple=True,
)
def cli(**kwargs: Any) -> None:
    loop = asyncio.get_event_loop()
    loop.create_task(main(**kwargs))
    loop.run_forever()


if __name__ == "__main__":
    cli(auto_envvar_prefix="AMQP")
