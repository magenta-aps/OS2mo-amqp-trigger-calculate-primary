# SPDX-FileCopyrightText: Magenta ApS <https://magenta.dk>
# SPDX-License-Identifier: MPL-2.0

from fastapi import FastAPI
from fastramqpi.main import FastRAMQPI

from calculate_primary import events
from calculate_primary.config import Settings
from calculate_primary.main import _setup_updater


def create_app() -> FastAPI:
    settings = Settings()
    fastramqpi = FastRAMQPI(
        application_name="calculate_primary",
        settings=settings.fastramqpi,
        graphql_version=22,
    )
    updater = _setup_updater(
        settings,
    )
    fastramqpi.add_context(settings=settings, updater=updater)

    # MO AMQP
    mo_amqp_system = fastramqpi.get_amqpsystem()
    mo_amqp_system.router.registry.update(events.router.registry)

    return fastramqpi.get_app()
