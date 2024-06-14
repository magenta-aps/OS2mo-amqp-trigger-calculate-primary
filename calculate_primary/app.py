# SPDX-FileCopyrightText: Magenta ApS <https://magenta.dk>
# SPDX-License-Identifier: MPL-2.0
from typing import Any

from calculate_primary.main import _setup_updater
from fastapi import FastAPI
from fastramqpi.main import FastRAMQPI
from calculate_primary.config import _Settings

def create_app(**kwargs: Any) -> FastAPI:
    settings = _Settings(**kwargs)
    fastramqpi = FastRAMQPI(
        application_name="calculate_primary",
        settings=settings.fastramqpi,
        graphql_version=22,
    )
    updater = _setup_updater(settings.integration, settings.dry_run, settings.mo_url, settings.opus_eng_types_primary_order)
    fastramqpi.add_context(settings=settings, updater=updater)
    
    # MO AMQP
    mo_amqp_system = fastramqpi.get_amqpsystem()
    mo_amqp_system.router.registry.update(events.router.registry)

    return app
