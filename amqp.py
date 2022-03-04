# SPDX-FileCopyrightText: 2019-2020 Magenta ApS
#
# SPDX-License-Identifier: MPL-2.0
import asyncio
from asyncio import TimerHandle
from datetime import datetime
from functools import wraps
from typing import Awaitable
from typing import Callable
from typing import Dict
from typing import List
from typing import Optional
from typing import Set
from uuid import UUID

import structlog
from aio_pika import connect
from aio_pika import ExchangeType
from aio_pika import IncomingMessage
from os2mo_http_trigger_protocol import RequestType
from prometheus_client import Counter
from prometheus_client import Gauge
from prometheus_client import Histogram
from pydantic import AmqpDsn  # type: ignore
from pydantic import BaseModel
from pydantic import BaseSettings
from pydantic import validator


event_counter = Counter(
    "amqp_events", "AMQP Events", ["role_type", "object_type", "request_type"]
)
exception_routing_key_counter = Counter(
    "amqp_exceptions_routing_key", "Exception counter", ["routing_key"]
)
exception_parse_counter = Counter(
    "amqp_exceptions_parse",
    "Exception counter",
    ["role_type", "object_type", "request_type"],
)
exception_callback_counter = Counter(
    "amqp_exceptions_callback",
    "Exception counter",
    ["role_type", "object_type", "request_type", "function"],
)
processing_time = Histogram(
    "amqp_processing_seconds",
    "Time spent running callback",
    ["role_type", "object_type", "request_type", "function"],
)
processing_inprogress = Gauge(
    "amqp_inprogress",
    "Number of callbacks currently running",
    ["role_type", "object_type", "request_type", "function"],
)
last_on_message = Gauge("amqp_last_on_message", "Timestamp of the last on_message call")
last_message_time = Gauge("amqp_last_message", "Timestamp from last message")
last_periodic = Gauge("amqp_last_periodic", "Timestamp of the last periodic call")
last_heartbeat = Gauge("amqp_last_heartbeat", "Time of the last connection heartbeat")
backlog_count = Gauge(
    "amqp_backlog", "Number of messages waiting for processing in the backlog"
)


logger = structlog.get_logger()


class PayloadType(BaseModel):
    uuid: UUID
    object_uuid: UUID
    time: datetime

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
        }

    @validator("time", pre=True)
    def time_validate(cls, v):
        return datetime.fromisoformat(v)


CallbackType = Callable[[str, str, str, PayloadType], Awaitable]


class Batch:
    def __init__(
        self,
        callback,
        batch_refresh_time: int = 5,
        batch_max_time: int = 60,
        batch_max_size: int = 10,
    ):
        self.callback = callback

        self.batch_refresh_time = batch_refresh_time
        self.batch_max_time = batch_max_time
        self.batch_max_size = batch_max_size

        self.refresh_dispatch: Optional[TimerHandle] = None
        self.max_time_dispatch: Optional[TimerHandle] = None
        self.payloads: List[PayloadType] = []

    def append(self, payload: PayloadType) -> None:
        loop = asyncio.get_running_loop()

        if self.refresh_dispatch:
            self.refresh_dispatch.cancel()
        self.refresh_dispatch = loop.call_later(self.batch_refresh_time, self.dispatch)

        if self.max_time_dispatch is None:
            self.max_time_dispatched = loop.call_at(
                loop.time() + self.batch_max_time, self.dispatch
            )

        self.payloads.append(payload)
        if len(self.payloads) == self.batch_max_size:
            self.dispatch()

    def clear(self) -> None:
        if self.refresh_dispatch:
            self.refresh_dispatch.cancel()
        self.refresh_dispatch = None

        if self.max_time_dispatch:
            self.max_time_dispatch.cancel()
        self.max_time_dispatch = None

        self.payloads = []

    def dispatch(self):
        payloads = self.payloads
        self.clear()
        return self.callback(payloads)


def bulk_messages(*args, **kwargs):
    """Bulk messages before calling wrapped function."""

    def decorator(function):
        batches: Dict[str, Batch] = {}

        @wraps(function)
        async def wrapper(
            role_type: str,
            object_type: str,
            request_type: str,
            payload: PayloadType,
        ) -> None:
            key = ".".join([role_type, object_type, request_type])
            batch = batches.setdefault(key, Batch(function, *args, **kwargs))
            batch.append(payload)

        return wrapper

    return decorator


def strip_routing(function):
    """Remove routing parameters from callback function."""

    @wraps(function)
    async def wrapper(
        role_type: str,
        object_type: str,
        request_type: str,
        *args,
        **kwargs,
    ) -> None:
        await function(*args, **kwargs)

    return wrapper


class Settings(BaseSettings):
    queue_name: str
    amqp_url: AmqpDsn = "amqp://guest:guest@localhost:5672"
    amqp_exchange: str = "os2mo"


class AMQPSystem:
    def __init__(self, *args, **kwargs):
        self.settings = Settings(*args, **kwargs)

        self.started = False
        self.registry: Dict[str, Dict[str, Dict[RequestType, Set[CallbackType]]]] = {}

    def register(self, role_type: str, object_type: str, request_type: str):
        request_type = RequestType(request_type)

        registry = (
            self.registry.setdefault(role_type, {})
            .setdefault(object_type, {})
            .setdefault(request_type, set())
        )

        def decorator(function):
            if self.started:
                message = "Cannot register callback after run() has been called!"
                logger.error(
                    message,
                    role_type=role_type,
                    object_type=object_type,
                    request_type=request_type,
                    function=function.__name__,
                )
                raise ValueError(message)

            function_name = function.__name__

            @wraps(function)
            async def wrapper(
                role_type: str,
                object_type: str,
                request_type: str,
                payload: PayloadType,
            ) -> None:
                wrapped_function = processing_inprogress.labels(
                    role_type, object_type, request_type, function_name
                ).track_inprogress()(function)
                wrapped_function = processing_time.labels(
                    role_type, object_type, request_type, function_name
                ).time()(wrapped_function)
                await wrapped_function(role_type, object_type, request_type, payload)

            registry.add(wrapper)
            return function

        return decorator

    async def run(self) -> None:
        logger.info(
            "Establishing AMQP connection",
            url=self.settings.amqp_url.replace(
                ":" + self.settings.amqp_url.password, ":xxxxx"
            ),
        )
        connection = await connect(self.settings.amqp_url)

        logger.info("Creating AMQP channel")
        channel = await connection.channel()
        await channel.set_qos(prefetch_count=1)

        logger.info("Attaching AMQP exchange to channel")
        topic_logs_exchange = await channel.declare_exchange(
            self.settings.amqp_exchange, ExchangeType.TOPIC
        )

        logger.info(
            "Declaring unique message queue", queue_name=self.settings.queue_name
        )
        queue = await channel.declare_queue(self.settings.queue_name, durable=True)

        logger.info("Starting message listener")
        await queue.consume(self.on_message)

        logger.info("Binding routing keys")
        for role_type, role_registry in self.registry.items():
            for request_type, request_registry in role_registry.items():
                for event_type in request_registry.keys():
                    key = ".".join([role_type, request_type, event_type]).lower()
                    logger.info(
                        "Binding routing-key",
                        role_type=role_type,
                        request_type=request_type,
                        event_type=event_type,
                        key=key,
                    )
                    # TODO: Bind in parallel
                    await queue.bind(topic_logs_exchange, routing_key=key)

        # Setup metrics
        async def periodic_metrics() -> None:
            while True:
                last_periodic.set_to_current_time()
                last_heartbeat.set(connection.heartbeat_last)
                backlog_count.set(queue.declaration_result.message_count)
                await asyncio.sleep(1)

        asyncio.create_task(periodic_metrics())

    async def on_message(self, message: IncomingMessage) -> None:
        last_on_message.set_to_current_time()
        routing_key = message.routing_key
        logger.debug("Recieved message", routing_key=routing_key)
        try:
            with exception_routing_key_counter.labels(routing_key).count_exceptions():
                role_type, object_type, request_type = routing_key.split(".")
                request_type = RequestType(request_type.upper())
                event_counter.labels(role_type, object_type, request_type).inc()
            logger.debug(
                "Parsed routing-key",
                routing_key=routing_key,
                role_type=role_type,
                object_type=object_type,
                request_type=request_type,
            )

            with exception_parse_counter.labels(
                role_type, object_type, request_type
            ).count_exceptions(), message.process():
                payload = PayloadType.parse_raw(message.body)
                logger.debug(
                    "Parsed message",
                    role_type=role_type,
                    object_type=object_type,
                    request_type=request_type,
                    payload=payload,
                )

                last_message_time.set(payload.time.timestamp())

            callbacks = (
                self.registry.get(role_type, {})
                .get(object_type, {})
                .get(request_type, set())
            )
            for callback in callbacks:
                try:
                    with exception_callback_counter.labels(
                        role_type,
                        object_type,
                        request_type,
                        callback.__name__,
                    ).count_exceptions():
                        # TODO: Execute in parallel
                        await callback(role_type, object_type, request_type, payload)
                except Exception:
                    logger.exception(
                        "Exception during callback",
                        routing_key=routing_key,
                        function=callback.__name__,
                    )
        except Exception:
            logger.exception("Exception during on_message()", routing_key=routing_key)
