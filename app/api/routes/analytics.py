from datetime import date, datetime, time, timedelta, timezone 
 
import pandas as pd 
from fastapi import APIRouter, Depends, HTTPException, Query 
from sqlalchemy import select 
from sqlalchemy.orm import Session 
 
from app.api.deps import require_roles 
from app.core.config import settings 
from app.db.models import ChatQueryLog, Claim, ClaimStatus, User, UserRole 
from app.db.session import get_db 
from app.schemas.analytics import ( 
    AdjusterWorkload, 
    AnalyticsBucket, 
    ClaimAnalyticsResponse, 
) 
 
router = APIRouter(prefix="/analytics", tags=["Analytics"]) 
manager_or_admin = require_roles(UserRole.ADMIN, UserRole.CLAIMS_MANAGER) 
 
 
def _build_claim_dataframe(claims: list[Claim]) -> pd.DataFrame: 
    records = [ 
        { 
            "id": claim.id, 
            "assigned_user_id": claim.assigned_user_id, 
            "claim_type": claim.claim_type, 
            "region": claim.region, 
            "status": claim.status.value, 
            "submitted_at": claim.submitted_at, 
            "closed_at": claim.closed_at, 
        } 
        for claim in claims 
    ] 
 
    columns = [ 
        "id", 
        "assigned_user_id", 
        "claim_type", 
        "region", 
        "status", 
        "submitted_at", 
        "closed_at", 
    ] 
    frame = pd.DataFrame.from_records(records, columns=columns) 
 
    if frame.empty: 
        return frame 
 
    # Demonstrate duplicate/missing-value handling required by the SRS. 
    frame = frame.drop_duplicates(subset=["id"], keep="last") 
    frame = frame.dropna( 
        subset=["id", "claim_type", "region", "status", "submitted_at"] 
    ) 
    frame["submitted_at"] = pd.to_datetime( 
        frame["submitted_at"], utc=True 
    ) 
    frame["closed_at"] = pd.to_datetime( 
        frame["closed_at"], utc=True 
    ) 
    frame["claim_type"] = frame["claim_type"].astype(str).str.strip() 
    frame["region"] = frame["region"].astype(str).str.strip() 
    frame["status"] = frame["status"].astype(str).str.strip() 
    return frame 
 
 
def _bucket_rows(series: pd.Series) -> list[AnalyticsBucket]: 
    return [ 
        AnalyticsBucket(name=str(name), count=int(count)) 
        for name, count in series.items() 
    ] 
 
 
def _calculate_claim_metrics( 
    frame: pd.DataFrame, 
    now: datetime, 
) -> tuple[float, float, float | None, int]: 
    if frame.empty: 
        return 0.0, 0.0, None, 0 
 
    approved = int( 
        (frame["status"] == ClaimStatus.APPROVED.value).sum() 
    ) 
    rejected = int( 
        (frame["status"] == ClaimStatus.REJECTED.value).sum() 
    ) 
    resolved = approved + rejected 
 
    approval_rate = round(approved / resolved * 100, 2) if resolved else 0.0 
    rejection_rate = round(rejected / resolved * 100, 2) if resolved else 0.0 
 
    closed = frame["closed_at"].notna() 
    if closed.any(): 
        turnaround = ( 
            frame.loc[closed, "closed_at"] 
            - frame.loc[closed, "submitted_at"] 
        ).dt.total_seconds() / 86400 
        turnaround = turnaround[turnaround >= 0] 
        average_turnaround = ( 
            round(float(turnaround.mean()), 2) 
            if not turnaround.empty 
            else None 
        ) 
    else: 
        average_turnaround = None 
 
    pending = frame["status"].isin( 
        [ 
            ClaimStatus.SUBMITTED.value, 
            ClaimStatus.UNDER_REVIEW.value, 
        ] 
    ) 
    cutoff = pd.Timestamp(now) - pd.Timedelta( 
        days=settings.claim_sla_days 
    ) 
    sla_breached = int( 
        (pending & (frame["submitted_at"] <= cutoff)).sum() 
    ) 
 
    return approval_rate, rejection_rate, average_turnaround, sla_breached 
 
 
@router.get( 
    "/claims", 
    response_model=ClaimAnalyticsResponse, 
) 
def get_claim_analytics( 
    start_date: date | None = Query(default=None), 
    end_date: date | None = Query(default=None), 
    region: str | None = Query(default=None, max_length=100), 
    claim_type: str | None = Query(default=None, max_length=80), 
    db: Session = Depends(get_db), 
    _: User = Depends(manager_or_admin), 
): 
    if start_date and end_date and end_date < start_date: 
        raise HTTPException( 
            status_code=422, 
            detail="end_date must be greater than or equal to start_date", 
        ) 
 
    claims = list( 
        db.scalars(select(Claim).order_by(Claim.submitted_at)).all() 
    ) 
    frame = _build_claim_dataframe(claims) 
 
    if not frame.empty: 
        if start_date: 
            start_timestamp = pd.Timestamp( 
                datetime.combine( 
                    start_date, 
                    time.min, 
                    tzinfo=timezone.utc, 
                ) 
            ) 
            frame = frame[frame["submitted_at"] >= start_timestamp] 
 
        if end_date: 
            end_timestamp = pd.Timestamp( 
                datetime.combine( 
                    end_date + timedelta(days=1), 
                    time.min, 
                    tzinfo=timezone.utc, 
                ) 
            ) 
            frame = frame[frame["submitted_at"] < end_timestamp] 
 
        if region: 
            frame = frame[ 
                frame["region"].str.casefold() 
                == region.strip().casefold() 
            ] 
 
        if claim_type: 
            frame = frame[ 
                frame["claim_type"].str.casefold() 
                == claim_type.strip().casefold() 
            ] 
 
    now = datetime.now(timezone.utc) 
    approval_rate, rejection_rate, average_turnaround, sla_breached = ( 
        _calculate_claim_metrics(frame, now) 
    ) 
 
    if frame.empty: 
        month_counts = pd.Series(dtype="int64") 
        region_counts = pd.Series(dtype="int64") 
        type_counts = pd.Series(dtype="int64") 
        workload_counts = pd.Series(dtype="int64") 
    else: 
        frame["submitted_month"] = frame["submitted_at"].dt.strftime("%Y-%m") 
        month_counts = frame["submitted_month"].value_counts().sort_index() 
        region_counts = frame["region"].value_counts() 
        type_counts = frame["claim_type"].value_counts() 
        workload_counts = ( 
            frame.dropna(subset=["assigned_user_id"])["assigned_user_id"] 
            .astype(int) 
            .value_counts() 
        ) 
 
    adjuster_ids = [int(user_id) for user_id in workload_counts.index] 
    adjusters = {} 
    if adjuster_ids: 
        adjusters = { 
            user.id: user 
            for user in db.scalars( 
                select(User).where(User.id.in_(adjuster_ids)) 
            ).all() 
        } 
 
    ai_query_stmt = select(ChatQueryLog).order_by(ChatQueryLog.created_at) 
    ai_logs = list(db.scalars(ai_query_stmt).all()) 
 
    if start_date or end_date: 
        ai_frame = pd.DataFrame.from_records( 
            [ 
                {"created_at": log.created_at} 
                for log in ai_logs 
            ], 
            columns=["created_at"], 
        ) 
        if ai_frame.empty: 
            ai_query_count = 0 
        else: 
            ai_frame["created_at"] = pd.to_datetime( 
                ai_frame["created_at"], utc=True 
            ) 
            if start_date: 
                ai_frame = ai_frame[ 
                    ai_frame["created_at"] 
                    >= pd.Timestamp( 
                        datetime.combine( 
                            start_date, 
                            time.min, 
                            tzinfo=timezone.utc, 
                        ) 
                    ) 
                ] 
            if end_date: 
                ai_frame = ai_frame[ 
                    ai_frame["created_at"] 
                    < pd.Timestamp( 
                        datetime.combine( 
                            end_date + timedelta(days=1), 
                            time.min, 
                            tzinfo=timezone.utc, 
                        ) 
                    ) 
                ] 
            ai_query_count = len(ai_frame) 
    else: 
        ai_query_count = len(ai_logs) 
 
    return ClaimAnalyticsResponse( 
        total_claims=int(len(frame)), 
        approval_rate=approval_rate, 
        rejection_rate=rejection_rate, 
        average_turnaround_days=average_turnaround, 
        sla_breached_claims=sla_breached, 
        ai_query_count=ai_query_count, 
        claims_by_month=_bucket_rows(month_counts), 
        claims_by_region=_bucket_rows(region_counts), 
        claims_by_type=_bucket_rows(type_counts), 
        adjuster_workload=[ 
            AdjusterWorkload( 
                user_id=user_id, 
                full_name=adjusters[user_id].full_name, 
                claim_count=int(count), 
            ) 
            for user_id, count in workload_counts.items() 
            if int(user_id) in adjusters 
        ], 
    ) 