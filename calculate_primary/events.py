# SPDX-FileCopyrightText: Magenta ApS <https://magenta.dk>
# SPDX-License-Identifier: MPL-2.0
import structlog
from fastramqpi.ramqp.mo import MORouter
from fastramqpi.ramqp.mo import PayloadUUID
from os2mo_rollekatalog import depends

from calculate_primary.main import calculate_user


router = MORouter()
logger = structlog.get_logger(__name__)

# TODO: This has to be changed to listen to events on engagements,
# lookup the user attached to the engagement and then run calculate user.
@router.register("person")
async def calculate_engagement(
    person_uuid: PayloadUUID,
    updater: depends.Updater,
) -> None:
    calculate_user(updater, person_uuid)
