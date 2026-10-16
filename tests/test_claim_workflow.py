from app.api.routes.claims import VALID_TRANSITIONS
from app.db.models import ClaimStatus


def test_claim_workflow_allows_expected_transitions():
    assert ClaimStatus.UNDER_REVIEW in VALID_TRANSITIONS[ClaimStatus.SUBMITTED]
    assert ClaimStatus.APPROVED in VALID_TRANSITIONS[ClaimStatus.UNDER_REVIEW]
    assert ClaimStatus.REJECTED in VALID_TRANSITIONS[ClaimStatus.UNDER_REVIEW]
    assert ClaimStatus.CLOSED in VALID_TRANSITIONS[ClaimStatus.APPROVED]
    assert ClaimStatus.CLOSED in VALID_TRANSITIONS[ClaimStatus.REJECTED]


def test_closed_claim_has_no_normal_forward_transition():
    assert VALID_TRANSITIONS[ClaimStatus.CLOSED] == set()
