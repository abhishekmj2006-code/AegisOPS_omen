"""Autonomous Ops Safe Remediation API."""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
import json

from storage.database import get_db
from storage.repository import CentralRepository
from aiops.autonomous_ops import AutonomousOpsEngine

router = APIRouter(prefix="/api/v1/remediation", tags=["Autonomous Ops Remediation"])


class ApprovalPayload(BaseModel):
    operator: Optional[str] = "Human Operator"


@router.get("/actions")
def list_remediations(
    tenant_id: str = Query("TENANT_001", description="Tenant isolation boundary"),
    db: Session = Depends(get_db),
):
    """List pending and historical autonomous remediation actions with audit trails."""
    repo = CentralRepository(db)
    actions = repo.get_remediations_by_tenant(tenant_id)

    return {
        "tenant_id": tenant_id,
        "total_actions": len(actions),
        "actions": [
            {
                "id": a.id,
                "incident_id": a.incident_id,
                "action_type": a.action_type,
                "title": a.title,
                "description": a.description,
                "status": a.status,
                "policy_check": a.policy_check,
                "rollback_plan": a.rollback_plan,
                "operator": a.operator,
                "created_at": a.created_at.isoformat() if a.created_at else None,
                "executed_at": a.executed_at.isoformat() if a.executed_at else None,
                "audit_trail": json.loads(a.audit_trail_json or "[]"),
            }
            for a in actions
        ],
    }


@router.post("/actions/{action_id}/simulate")
def simulate_action(action_id: str, db: Session = Depends(get_db)):
    """Dry-run simulation of remediation action without making state changes."""
    repo = CentralRepository(db)
    action = repo.get_remediation_by_id(action_id)
    if not action:
        raise HTTPException(status_code=404, detail="Remediation action not found")

    result = AutonomousOpsEngine.simulate(db, action)
    return result


@router.post("/actions/{action_id}/approve")
def approve_action(
    action_id: str,
    payload: ApprovalPayload,
    db: Session = Depends(get_db),
):
    """Grant formal human operator approval for remediation execution."""
    repo = CentralRepository(db)
    action = repo.get_remediation_by_id(action_id)
    if not action:
        raise HTTPException(status_code=404, detail="Remediation action not found")

    result = AutonomousOpsEngine.approve(db, action, operator=payload.operator or "Human Operator")
    return result


@router.post("/actions/{action_id}/execute")
def execute_action(
    action_id: str,
    payload: ApprovalPayload,
    db: Session = Depends(get_db),
):
    """Execute the approved remediation action."""
    repo = CentralRepository(db)
    action = repo.get_remediation_by_id(action_id)
    if not action:
        raise HTTPException(status_code=404, detail="Remediation action not found")

    result = AutonomousOpsEngine.execute(db, action, operator=payload.operator or "Human Operator")
    return result


@router.post("/actions/{action_id}/rollback")
def rollback_action(
    action_id: str,
    payload: ApprovalPayload,
    db: Session = Depends(get_db),
):
    """Trigger verified rollback of executed remediation action."""
    repo = CentralRepository(db)
    action = repo.get_remediation_by_id(action_id)
    if not action:
        raise HTTPException(status_code=404, detail="Remediation action not found")

    result = AutonomousOpsEngine.rollback(db, action, operator=payload.operator or "Human Operator")
    return result
