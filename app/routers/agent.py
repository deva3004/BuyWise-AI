from fastapi import APIRouter, Depends

from app.agent import run_agent
from app.auth import get_current_user_id
from app.rate_limit import agent_limiter, limit_by_user
from app.schemas import AgentRequest, AgentResponse

router = APIRouter(tags=["agent"])


@router.post(
    "/agent",
    response_model=AgentResponse,
    dependencies=[Depends(limit_by_user(agent_limiter))],
)
def ask_agent(
    request: AgentRequest,
    user_id: int = Depends(get_current_user_id),
):
    decision = run_agent(request.message, user_id=user_id)
    return AgentResponse(decision=decision.decision, reasoning=decision.reasoning)
