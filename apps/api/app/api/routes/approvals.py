"""Human decisions for actions paused by deterministic policy."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import get_current_user
from app.db.session import get_session
from app.models.approval import Approval
from app.models.enums import ApprovalDecision
from app.models.user import User
from app.schemas.approval import ApprovalRead
from app.services.approvals import ApprovalConflictError, ApprovalNotFoundError, ApprovalService

router = APIRouter(prefix="/api/v1/approvals", tags=["approvals"])


def get_approval_service(session: AsyncSession = Depends(get_session)) -> ApprovalService:
    return ApprovalService(session)


@router.get("", response_model=list[ApprovalRead])
async def list_approvals(
    current_user: User = Depends(get_current_user),
    service: ApprovalService = Depends(get_approval_service),
) -> list[Approval]:
    return await service.list_pending(current_user.id)


async def _decide(
    approval_id: UUID,
    decision: ApprovalDecision,
    current_user: User,
    service: ApprovalService,
) -> Approval:
    try:
        return await service.decide(current_user, approval_id, decision)
    except ApprovalNotFoundError:
        raise HTTPException(status_code=404, detail="Approval not found") from None
    except ApprovalConflictError as error:
        raise HTTPException(status_code=409, detail=str(error)) from None


@router.post("/{approval_id}/approve", response_model=ApprovalRead)
async def approve(
    approval_id: UUID,
    current_user: User = Depends(get_current_user),
    service: ApprovalService = Depends(get_approval_service),
) -> Approval:
    return await _decide(approval_id, ApprovalDecision.APPROVED, current_user, service)


@router.post("/{approval_id}/reject", response_model=ApprovalRead)
async def reject(
    approval_id: UUID,
    current_user: User = Depends(get_current_user),
    service: ApprovalService = Depends(get_approval_service),
) -> Approval:
    return await _decide(approval_id, ApprovalDecision.REJECTED, current_user, service)
