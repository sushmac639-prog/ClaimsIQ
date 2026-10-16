from pydantic import BaseModel 
class AnalyticsBucket(BaseModel): 
    name: str 
    count: int 
 
 
class AdjusterWorkload(BaseModel): 
    user_id: int 
    full_name: str 
    claim_count: int 
 
 
class ClaimAnalyticsResponse(BaseModel): 
    total_claims: int 
    approval_rate: float 
    rejection_rate: float 
    average_turnaround_days: float | None 
    sla_breached_claims: int 
    ai_query_count: int 
    claims_by_month: list[AnalyticsBucket] 
    claims_by_region: list[AnalyticsBucket] 
    claims_by_type: list[AnalyticsBucket] 
    adjuster_workload: list[AdjusterWorkload] 