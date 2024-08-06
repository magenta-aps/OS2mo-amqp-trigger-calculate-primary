# SPDX-FileCopyrightText: Magenta ApS <https://magenta.dk>
# SPDX-License-Identifier: MPL-2.0
from fastramqpi.ramqp.mo import MORouter
from fastramqpi.ramqp.mo import PayloadUUID
from more_itertools import only

from calculate_primary import depends
from calculate_primary.common import logger
from calculate_primary.main import calculate_user

router = MORouter()


@router.register("engagement")
async def calculate_engagement(
    engagement_uuid: PayloadUUID,
    mo: depends.GraphQLClient,
    updater: depends.Updater,
) -> None:
    logger.info("Registered event for engagement", engagement_uuid=engagement_uuid)
    result = await mo.get_engagement_person(engagement_uuid)
    result = only(result.objects)
    uuids = {e.uuid for o in result.validities for e in o.person}

    logger.info("Found related person(s)", person_uuids=uuids)
    # An engagement can be associated with multiple employees across its lifespan, although it typically isn't done.
    for person_uuid in uuids:
        calculate_user(updater, person_uuid)
