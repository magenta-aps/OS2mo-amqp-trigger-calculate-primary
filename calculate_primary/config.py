# SPDX-FileCopyrightText: Magenta ApS <https://magenta.dk>
# SPDX-License-Identifier: MPL-2.0
from typing import Literal
from uuid import UUID

from pydantic import BaseSettings


class Settings(BaseSettings):
    class Config:
        frozen = True
        env_nested_delimiter = "__"

    mo_url: str

    amqp_integration: Literal["DEFAULT", "OPUS", "SD"]
    dry_run: bool = False
    eng_types_primary_order: list[UUID] = []
