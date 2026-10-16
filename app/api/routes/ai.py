import logging
from collections import defaultdict, deque
from threading import Lock
from time import monotonic

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.models import Policy, User, UserRole
from app.db.session import get_db
from app.rag.service import answer_question
from app.schemas.ai import AIQueryRequest, AIQueryResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/ai", tags=["AI / RAG Chat"])
# Lightweight per-process limit for the MVP. Use Redis/API Management for multi-worker deployments.
_RATE_LIMIT = 20
_RATE_WINDOW_SECONDS = 60
_requests_by_user: dict[int, deque[float]] = defaultdict(deque)
_rate_limit_lock = Lock()


def _enforce_rate_limit(user_id: int) -> None:
    now = monotonic()
    with _rate_limit_lock:
        recent = _requests_by_user[user_id]
        while recent and now - recent[0] >= _RATE_WINDOW_SECONDS:
            recent.popleft()
        if len(recent) >= _RATE_LIMIT:
            raise HTTPException(status_code=429, detail="AI query rate limit exceeded. Try again shortly.", headers={"Retry-After": str(_RATE_WINDOW_SECONDS)})
        recent.append(now)


@router.post("/query", response_model=AIQueryResponse)
def query_policy_knowledge(
    body: AIQueryRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    _enforce_rate_limit(user.id)
    if body.policy_id is not None:
        policy = db.get(Policy, body.policy_id)
        if policy is None:
            raise HTTPException(status_code=404, detail="Policy not found")
        if user.role not in {UserRole.ADMIN, UserRole.CLAIMS_MANAGER} and policy.region.casefold() not in {(user.region or "").casefold(), "global"}:
            raise HTTPException(status_code=403, detail="You cannot query documents for this policy region")

    try:
        return answer_question(db, user, body.question.strip(), body.top_k, body.policy_id)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail="AI chat service is unavailable") from exc
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Unexpected AI query failure for user_id=%s", user.id)
        db.rollback()
        raise HTTPException(status_code=503, detail="AI chat service is temporarily unavailable") from exc
