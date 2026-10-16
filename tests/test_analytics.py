from datetime import datetime, timedelta, timezone 
 
from app.api.routes.analytics import _build_claim_dataframe, _calculate_claim_metrics 
from app.db.models import Claim, ClaimStatus 
 
 
def make_claim( 
    claim_id: int, 
    status: ClaimStatus, 
    submitted_at: datetime, 
    closed_at: datetime | None = None, 
) -> Claim: 
    return Claim( 
        id=claim_id, 
        claim_number=f"CLM-{claim_id:03d}", 
        policy_id=1, 
        claimant_name="Test Claimant", 
        claim_type="health", 
        claim_amount=1000, 
        region="South", 
        status=status, 
        submitted_at=submitted_at, 
        closed_at=closed_at, 
    ) 
 
 
def test_analytics_dataframe_removes_duplicate_rows(): 
    now = datetime.now(timezone.utc) 
    frame = _build_claim_dataframe( 
        [ 
            make_claim(1, ClaimStatus.SUBMITTED, now), 
            make_claim(1, ClaimStatus.SUBMITTED, now), 
        ] 
    ) 
 
    assert len(frame) == 1 
 
 
def test_approval_and_rejection_rates(): 
    now = datetime.now(timezone.utc) 
    frame = _build_claim_dataframe( 
        [ 
            make_claim(1, ClaimStatus.APPROVED, now), 
            make_claim(2, ClaimStatus.REJECTED, now), 
        ] 
    ) 
 
    approval, rejection, turnaround, sla = _calculate_claim_metrics( 
        frame, now 
    ) 
 
    assert approval == 50.0 
    assert rejection == 50.0 
    assert turnaround is None 
    assert sla == 0 
 
 
def test_average_turnaround_and_sla_breach(): 
    now = datetime.now(timezone.utc) 
    submitted = now - timedelta(days=10) 
    closed = submitted + timedelta(days=4) 
 
    frame = _build_claim_dataframe( 
        [ 
            make_claim(1, ClaimStatus.CLOSED, submitted, closed), 
            make_claim(2, ClaimStatus.UNDER_REVIEW, submitted), 
        ] 
    ) 
 
    approval, rejection, turnaround, sla = _calculate_claim_metrics( 
        frame, now 
    ) 
 
    assert approval == 0.0 
    assert rejection == 0.0 
    assert turnaround == 4.0 
    assert sla == 1 