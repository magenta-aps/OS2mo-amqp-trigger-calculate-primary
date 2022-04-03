# SPDX-FileCopyrightText: 2019-2020 Magenta ApS
#
# SPDX-License-Identifier: MPL-2.0
from more_itertools import one

from .common import callback_func
from ramqp.lowlevel import callbacks_registered
from ramqp.lowlevel import processing_calls


async def test_register_metrics(amqp_system):
    """Test that reigster() metrics behave as expected."""
    # Check that our processing_metric is empty
    assert set(callbacks_registered._metrics.keys()) == set()
    assert set(processing_calls._metrics.keys()) == set()

    # Register callback
    decorated_func = amqp_system.register("test.routing.key")(callback_func)
    callback = one(amqp_system._registry["test.routing.key"])

    # Test that callback counter has gone up
    assert set(callbacks_registered._metrics.keys()) == {("test.routing.key",)}
    register_metric = callbacks_registered._metrics[("test.routing.key",)]
    assert register_metric._value.get() == 1.0
    # But that our processing metric has not
    assert set(processing_calls._metrics.keys()) == set()

    # Test that first call registers callback metric
    await callback("test.routing.key", {})
    assert set(processing_calls._metrics.keys()) == {
        ("test.routing.key", "callback_func")
    }
    metric = processing_calls._metrics[("test.routing.key", "callback_func")]
    assert metric._value.get() == 1.0

    # Test that subsequent calls count up the callback metric
    await callback("test.routing.key", {})
    assert set(processing_calls._metrics.keys()) == {
        ("test.routing.key", "callback_func")
    }
    assert metric._value.get() == 2.0

    await callback("test.routing.key", {})
    assert set(processing_calls._metrics.keys()) == {
        ("test.routing.key", "callback_func")
    }
    assert metric._value.get() == 3.0

    # But our register metric stays the same
    assert register_metric._value.get() == 1.0
