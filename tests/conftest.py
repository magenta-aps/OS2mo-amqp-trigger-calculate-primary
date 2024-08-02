# SPDX-FileCopyrightText: 2019-2020 Magenta ApS
#
# SPDX-License-Identifier: MPL-2.0
# pylint: disable=redefined-outer-name,protected-access
"""This module contains pytest specific code, fixtures and helpers."""
from unittest.mock import AsyncMock
from uuid import UUID

from calculate_primary.config import Settings
import pytest
from aio_pika import DeliveryMode
from aio_pika import IncomingMessage
from aio_pika import Message
from aiormq.abc import DeliveredMessage
from pamqp.commands import Basic
from pydantic import parse_obj_as
from ra_utils.attrdict import attrdict
from ramqp.moqp import PayloadType
from tests.test_primary import MOPrimaryEngagementUpdaterTest


@pytest.fixture
def mo_payload() -> PayloadType:
    """Pytest fixture to construct a MO PayloadType."""
    return parse_obj_as(
        PayloadType,
        {
            "uuid": UUID("00000000-0000-0000-0000-000000000000"),
            "object_uuid": UUID("ffffffff-ffff-ffff-ffff-ffffffffffff"),
            "time": "2000-01-01T00:00:00.000000",
        },
    )


@pytest.fixture
def aio_pika_message(mo_payload: PayloadType) -> Message:
    """Pytest fixture to construct a aio_pika Message."""
    return Message(body=mo_payload.json().encode("utf-8"))


@pytest.fixture
def aio_pika_delivered_message(aio_pika_message: Message) -> DeliveredMessage:
    """Pytest fixture to construct a aiormq DeliveredMessage."""
    return DeliveredMessage(
        # channel should be an AbstractChannel
        channel=AsyncMock(),  # type: ignore
        header=attrdict(
            {
                "properties": attrdict(
                    {
                        "expiration": None,
                        "content_type": None,
                        "content_encoding": None,
                        "delivery_mode": DeliveryMode.NOT_PERSISTENT,
                        "headers": {},
                        "priority": 0,
                        "correlation_id": None,
                        "reply_to": None,
                        "message_id": "6800cb934bf94cc68009fe04ac91c972",
                        "timestamp": None,
                        "message_type": None,
                        "user_id": None,
                        "app_id": None,
                        "cluster_id": "",
                    }
                )
            }
        ),
        body=aio_pika_message.body,
        delivery=Basic.GetOk(
            delivery_tag=1,
            redelivered=False,
            exchange="9t6wzzmlBcaopTLF1aOPgnnd8szMSU",
            routing_key="employee.employee.create",
            message_count=None,
        ),
    )


@pytest.fixture
def aio_pika_incoming_message(
    aio_pika_delivered_message: DeliveredMessage,
) -> IncomingMessage:
    """Pytest fixture to construct a aio_pika IncomingMessage."""
    return IncomingMessage(aio_pika_delivered_message)

@pytest.fixture
def dummy_settings():
    yield Settings(mo_url="", amqp_integration="DEFAULT")
