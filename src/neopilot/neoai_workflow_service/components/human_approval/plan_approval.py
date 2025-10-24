from __future__ import annotations

from typing import Literal

from lib import result
from neoai_workflow_service.components.human_approval.component import \
    HumanApprovalComponent
from neoai_workflow_service.entities.state import (WorkflowState,
                                                   WorkflowStatusEnum)


class PlanApprovalComponent(HumanApprovalComponent):
    """Component for requesting human approval for workflow plans."""

    _approval_req_workflow_state: Literal[WorkflowStatusEnum.PLAN_APPROVAL_REQUIRED] = (
        WorkflowStatusEnum.PLAN_APPROVAL_REQUIRED
    )
    _node_prefix: Literal["plan_approval"] = "plan_approval"

    def _build_approval_request(self, state: WorkflowState) -> result.Result[str, RuntimeError]:
        return result.Ok(
            "Review the proposed plan. Then ask questions or request changes. "
            "To execute the plan, select Approve plan."
        )
