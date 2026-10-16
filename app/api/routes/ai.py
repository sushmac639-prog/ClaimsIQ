from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.models import Policy, User
from app.db.session import get_db
from app.rag.service import answer_question
from app.schemas.ai import AIQueryRequest, AIQueryResponse

router = APIRouter(prefix="/ai", tags=["AI / RAG Chat"])


@router.post("/query", response_model=AIQueryResponse)
def query_policy_knowledge(
    body: AIQueryRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if body.policy_id is not None:
        policy = db.get(Policy, body.policy_id)
        if policy is None:
            raise HTTPException(status_code=404, detail="Policy not found")
        if user.role.value not in {"admin", "claims_manager"} and policy.region not in {user.region, "GLOBAL"}:
            raise HTTPException(status_code=403, detail="You cannot query documents for this policy region")

    try:
        print(f"Policy Id - {body.policy_id}")
        return answer_question(db, user, body.question.strip(), body.top_k, body.policy_id)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"debug error : {str(exc)}") from exc
