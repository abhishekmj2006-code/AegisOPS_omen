"""Tests for Autonomous Ops Safe Remediation Lifecycle (Direct Invocation)."""

import pytest
from storage.database import init_db, SessionLocal
from api.scenarios import inject_scenario, InjectScenarioRequest
from api.remediation import (
    list_remediations,
    simulate_action,
    approve_action,
    execute_action,
    rollback_action,
    ApprovalPayload,
)


@pytest.fixture(scope="module")
def db_session():
    init_db()
    session = SessionLocal()
    yield session
    session.close()


def test_autonomous_ops_lifecycle(db_session):
    # 1. Trigger an incident by injecting an anomaly
    req = InjectScenarioRequest(
        scenario="network_spike",
        tenant_id="TENANT_001",
        device_id="DEVICE_AUTO_TEST",
    )
    res_inj = inject_scenario(payload=req, db=db_session)
    assert res_inj["status"] == "success"
    assert res_inj["is_anomaly"] is True

    # 2. Query remediation actions
    res_actions = list_remediations(tenant_id="TENANT_001", db=db_session)
    actions = res_actions["actions"]
    assert len(actions) > 0
    target_action = actions[0]
    action_id = target_action["id"]
    assert target_action["status"] in ["pending_approval", "simulated"]

    # 3. Simulate (Dry-run)
    res_sim = simulate_action(action_id=action_id, db=db_session)
    assert res_sim["status"] == "simulated"
    assert "PASSED" in res_sim["policy_check"]

    # 4. Human Approval
    res_app = approve_action(
        action_id=action_id,
        payload=ApprovalPayload(operator="Security Lead (Auditor)"),
        db=db_session,
    )
    assert res_app["status"] == "approved"

    # 5. Execution
    res_exec = execute_action(
        action_id=action_id,
        payload=ApprovalPayload(operator="Automation Controller"),
        db=db_session,
    )
    assert res_exec["status"] == "executed"

    # 6. Rollback
    res_rb = rollback_action(
        action_id=action_id,
        payload=ApprovalPayload(operator="Operator"),
        db=db_session,
    )
    assert res_rb["status"] == "rolled_back"
