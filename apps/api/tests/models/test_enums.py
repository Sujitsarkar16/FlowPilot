from app.models.enums import (
    ActionStatus,
    ApprovalDecision,
    ConnectionProvider,
    EventSource,
    JobStatus,
    LifeEventType,
    PlanStatus,
    RawEventStatus,
    RiskLevel,
)


def test_domain_enums_serialize_as_lowercase_values() -> None:
    enums = (
        EventSource.GMAIL,
        RawEventStatus.RECEIVED,
        LifeEventType.TRAVEL_BOOKED,
        PlanStatus.POLICY_CHECKED,
        ActionStatus.WAITING_APPROVAL,
        RiskLevel.RED,
        ApprovalDecision.APPROVED,
        ConnectionProvider.MOCK_BANK,
        JobStatus.DEAD_LETTER,
    )
    assert [item.value for item in enums] == [str(item) for item in enums]
    assert all(value == value.lower() for value in (item.value for item in enums))
