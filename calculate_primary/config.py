# SPDX-FileCopyrightText: Magenta ApS <https://magenta.dk>
# SPDX-License-Identifier: MPL-2.0

from typing import Literal
from uuid import UUID

from fastramqpi.config import Settings as _FastRAMQPISettings
from fastramqpi.ramqp.config import AMQPConnectionSettings as _AMQPConnectionSettings
from pydantic import BaseSettings


# https://git.magenta.dk/rammearkitektur/FastRAMQPI#multilayer-exchanges
class AMQPConnectionSettings(_AMQPConnectionSettings):
    upstream_exchange = "os2mo"
    exchange = "os2mo_calculate_primary"
    queue_prefix = "os2mo_calculate_primary"


class FastRAMQPISettings(_FastRAMQPISettings):
    amqp: AMQPConnectionSettings


class Settings(BaseSettings):
    class Config:
        frozen = True
        env_nested_delimiter = "__"

    fastramqpi: FastRAMQPISettings

    integration: Literal["DEFAULT", "OPUS", "SD"]
    dry_run: bool = False
    eng_types_primary_order: list[UUID] = []
