# SPDX-FileCopyrightText: Magenta ApS <https://magenta.dk>
# SPDX-License-Identifier: MPL-2.0
import asyncio

import structlog
from fastramqpi.ramqp.depends import RateLimit
from fastramqpi.ramqp.mo import MORouter
from fastramqpi.ramqp.mo import PayloadUUID
from more_itertools import only

from calculate_primary import depends
from calculate_primary.main import calculate_user

router = MORouter()

logger = structlog.stdlib.get_logger()


@router.register("engagement")
async def calculate_engagement(
    engagement_uuid: PayloadUUID,
    mo: depends.GraphQLClient,
    updater: depends.Updater,
    settings: depends.Settings,
    _: RateLimit,
) -> None:
    logger.info(
        "Registered event for engagement",
        engagement_uuid=engagement_uuid,
        delay=settings.delay_amqp,
    )

    await asyncio.sleep(settings.delay_amqp)

    result = await mo.get_engagement_person(engagement_uuid)
    result = only(result.objects)
    if result is None:
        logger.info("No related person found.", engagement_uuid=engagement_uuid)
        return
    uuids = {e.uuid for o in result.validities for e in o.person}

    logger.info("Found related person(s)", person_uuids=uuids)
    # An engagement can be associated with multiple employees across its lifespan, although it typically isn't done.
    for person_uuid in uuids:
        calculate_user(updater, person_uuid)
