# SPDX-FileCopyrightText: 2019-2020 Magenta ApS
#
# SPDX-License-Identifier: MPL-2.0
"""Test run_amqp codepath."""
from typing import Any
from typing import Dict
from typing import List
from unittest.mock import patch
from uuid import UUID

from aio_pika import IncomingMessage
from more_itertools import one
from ra_utils.attrdict import attrdict
from ramqp.abstract_amqpsystem import _on_message
from ramqp.moqp import MOAMQPSystem

from calculate_primary.main import _run_amqp


async def test_on_message(aio_pika_incoming_message: IncomingMessage) -> None:
    """Test _on_message mock call reaches callback."""
    params = {}

    async def callback_function(message: IncomingMessage) -> None:
        params["message"] = message

    # Fake a message delivery, as it would happen from the AMQPSystem
    await _on_message(callback_function, aio_pika_incoming_message)

    # Assert that the callback was actually triggered with our message
    assert params["message"] == aio_pika_incoming_message


@patch("calculate_primary.main.MOAMQPSystem")
async def test_run_amqp(
    moamqpsystem_class: Any, aio_pika_incoming_message: IncomingMessage
) -> None:
    """Test _on_message mock call on _run_amqp callback."""

    # pylint: disable=too-few-public-methods
    class TestMOAMQPSystem(MOAMQPSystem):
        """Test MOAMQPSystem with noop run_forever method."""

        def run_forever(self, *_1: List[Any], **_2: Dict[str, Any]) -> None:
            """Noop run_forever method."""

    params = {}

    def recalculate_user(uuid: UUID) -> dict:
        params["uuid"] = uuid
        return {}

    updater = attrdict({"recalculate_user": recalculate_user})

    moamqp_system = TestMOAMQPSystem()
    moamqpsystem_class.return_value = moamqp_system

    # Run _run_amqp, this registers our callback with the MOAMQPSystem
    _run_amqp(updater, "amqp://invalid/", "invalid")

    callback = one(moamqp_system._registry.keys())  # pylint: disable=protected-access

    # Fake a message delivery, as it would happen from the AMQPSystem
    await _on_message(callback, aio_pika_incoming_message)

    # Assert that recalculate_user was called from the MOAMQPSystem adapter
    assert params["uuid"] == UUID("00000000-0000-0000-0000-000000000000")
