from datetime import UTC

from app.models.user import User


def test_uuid_and_timestamp_mixins_supply_expected_columns() -> None:
    columns = User.__table__.c
    assert columns.id.primary_key
    assert columns.created_at.type.timezone is True
    assert columns.updated_at.type.timezone is True
    assert User.utcnow().tzinfo is UTC
