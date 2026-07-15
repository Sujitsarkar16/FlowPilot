import pytest
from sqlalchemy import text

from app.db.health import check_database
from app.models.user import User


@pytest.mark.asyncio
async def test_database_health_query_succeeds(session: object) -> None:
    assert await check_database(session) is True  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_failed_transaction_rolls_back(session: object) -> None:
    with pytest.raises(RuntimeError):
        async with session.begin():  # type: ignore[attr-defined]
            session.add(User(auth_subject="rollback-subject"))  # type: ignore[attr-defined]
            raise RuntimeError("fail")
    result = await session.execute(
        text("SELECT auth_subject FROM users WHERE auth_subject = 'rollback-subject'")
    )  # type: ignore[attr-defined]
    assert result.scalar_one_or_none() is None
