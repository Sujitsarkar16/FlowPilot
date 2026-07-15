import pytest

from app.models.enums import ActionStatus
from app.services.rollback import RollbackError, RollbackService
from tests.execution_helpers import action_state


@pytest.mark.asyncio
async def test_completed_reversible_action_rolls_back_once(session) -> None:
    user, _, action = await action_state(session, status=ActionStatus.COMPLETED)
    rolled_back = await RollbackService(session).rollback(user, action.id)

    assert rolled_back.status is ActionStatus.ROLLED_BACK
    with pytest.raises(RollbackError, match="already been rolled back"):
        await RollbackService(session).rollback(user, action.id)
