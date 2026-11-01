"""Torre de Control — read-only live monitor for the admin (Drack).

Gate: only user_id == 1 (Drack's account) may call this endpoint.
No role table required; this is intentionally a single-owner shortcut.

Returns a snapshot of:
  - who is online (last_seen_at within the last 5 minutes)
  - PAES study sessions per subject (completed only)
  - estimated PAES score range per subject
"""

from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from core.database import get_session
from core.identity import Principal, UserPrincipalDep
from core.timeutils import to_utc_aware
from models import AuthSession, PaesAssessmentState, PaesStudySession, PaesSubject, User
from models.models import UserProfile

router = APIRouter()

_ONLINE_WINDOW_MINUTES = 5
_ACTIVITY_WINDOW_HOURS = 24 * 7  # show users active in the last 7 days


def _require_admin(principal: Principal = UserPrincipalDep) -> Principal:
    """Allow only Drack (user_id == 1). Simple, no role table."""
    if principal.user_id != 1:
        raise HTTPException(status_code=403, detail="Forbidden")
    return principal


@router.get("/live-monitor")
def live_monitor(
    _: Principal = Depends(_require_admin),
    db: Session = Depends(get_session),
):
    """
    Snapshot of connected family/friends for the Torre de Control.

    Response shape:
    {
        "online_count": int,
        "as_of": "ISO-8601",
        "users": [
            {
                "user_id": int,
                "email": str,
                "is_online": bool,
                "last_seen_minutes_ago": int | null,
                "subjects": [
                    {
                        "code": "M1",
                        "name": "Matemática 1",
                        "session_count": int,
                        "sessions": [
                            {
                                "started_at": "ISO-8601",
                                "items": int,
                                "correct": int,
                                "pct": float,
                                "score_min": int | null,
                                "score_max": int | null
                            }
                        ],
                        "best_score_min": int | null,
                        "best_score_max": int | null
                    }
                ]
            }
        ]
    }
    """
    now = datetime.now(timezone.utc)
    online_cutoff = now - timedelta(minutes=_ONLINE_WINDOW_MINUTES)
    activity_cutoff = now - timedelta(hours=_ACTIVITY_WINDOW_HOURS)

    # --- 1. Subjects lookup (code + name) ---
    subjects_rows = db.exec(select(PaesSubject)).all()
    subjects_by_id: dict[int, PaesSubject] = {s.id: s for s in subjects_rows}

    # --- 2. Users who have had any auth session in the activity window ---
    #        (excludes revoked sessions that never refreshed)
    recent_sessions = db.exec(
        select(AuthSession).where(AuthSession.revoked_at.is_(None)).where(AuthSession.last_seen_at >= activity_cutoff)
    ).all()

    if not recent_sessions:
        return {
            "online_count": 0,
            "as_of": now.isoformat(),
            "users": [],
        }

    # Deduplicate: keep the most-recent session per user
    latest_session_by_user: dict[int, AuthSession] = {}
    for s in recent_sessions:
        uid = s.user_id
        existing = latest_session_by_user.get(uid)
        s_seen = to_utc_aware(s.last_seen_at)
        if existing is None or s_seen > to_utc_aware(existing.last_seen_at):
            latest_session_by_user[uid] = s

    active_user_ids = list(latest_session_by_user.keys())

    # --- 3. Fetch users & profiles ---
    users_rows = db.exec(select(User).where(User.id.in_(active_user_ids))).all()
    users_by_id: dict[int, User] = {u.id: u for u in users_rows}

    profiles_rows = db.exec(select(UserProfile).where(UserProfile.user_id.in_(active_user_ids))).all()
    profiles_by_user_id: dict[int, UserProfile] = {p.user_id: p for p in profiles_rows}

    # --- 4. Fetch completed PAES study sessions for these users ---
    paes_sessions = db.exec(
        select(PaesStudySession)
        .where(PaesStudySession.user_id.in_(active_user_ids))
        .where(PaesStudySession.is_completed == True)  # noqa: E712
        .order_by(PaesStudySession.started_at.asc())
    ).all()

    # Index by user_id → subject_id → list[PaesStudySession]
    sessions_by_user_subject: dict[int, dict[int, list[PaesStudySession]]] = {}
    for ps in paes_sessions:
        sessions_by_user_subject.setdefault(ps.user_id, {}).setdefault(ps.subject_id, []).append(ps)

    # --- 5. Fetch assessment states (score estimates) ---
    assessment_states = db.exec(
        select(PaesAssessmentState).where(PaesAssessmentState.user_id.in_(active_user_ids))
    ).all()

    # Index: user_id → subject_id → PaesAssessmentState
    state_by_user_subject: dict[int, dict[int, PaesAssessmentState]] = {}
    for st in assessment_states:
        state_by_user_subject.setdefault(st.user_id, {})[st.subject_id] = st

    # --- 6. Build response ---
    online_count = 0
    user_list = []

    for uid in active_user_ids:
        # Skip Drack himself from the monitor
        if uid == 1:
            continue

        user = users_by_id.get(uid)
        if not user:
            continue

        auth_sess = latest_session_by_user[uid]
        last_seen = to_utc_aware(auth_sess.last_seen_at)
        delta_minutes = int((now - last_seen).total_seconds() / 60)
        is_online = last_seen >= online_cutoff

        if is_online:
            online_count += 1

        # Build per-subject breakdown
        subjects_out = []
        user_subjects = sessions_by_user_subject.get(uid, {})

        for subject_id, sess_list in user_subjects.items():
            subject = subjects_by_id.get(subject_id)
            subject_code = subject.code if subject else f"subject_{subject_id}"
            subject_name = subject.name if subject else subject_code

            # Assessment state for score estimates
            assessment = state_by_user_subject.get(uid, {}).get(subject_id)
            score_min_global: Optional[int] = int(assessment.estimated_paes_min) if assessment else None
            score_max_global: Optional[int] = int(assessment.estimated_paes_max) if assessment else None

            sessions_out = []
            for sess in sess_list:
                total = sess.total_items or 0
                correct = sess.correct_items or 0
                pct = round(correct / total * 100, 1) if total > 0 else 0.0
                sessions_out.append(
                    {
                        "started_at": to_utc_aware(sess.started_at).isoformat() if sess.started_at else None,
                        "items": total,
                        "correct": correct,
                        "pct": pct,
                        "score_min": score_min_global,
                        "score_max": score_max_global,
                    }
                )

            subjects_out.append(
                {
                    "code": subject_code,
                    "name": subject_name,
                    "session_count": len(sess_list),
                    "sessions": sessions_out,
                    "best_score_min": score_min_global,
                    "best_score_max": score_max_global,
                }
            )

        # Sort subjects alphabetically by code
        subjects_out.sort(key=lambda x: x["code"])

        prof = profiles_by_user_id.get(uid)
        display_name = prof.name if prof else user.email.split("@")[0].capitalize()
        user_list.append(
            {
                "user_id": uid,
                "email": user.email,
                "name": display_name,
                "is_online": is_online,
                "last_seen_minutes_ago": delta_minutes,
                "subjects": subjects_out,
            }
        )

    # Online users first, then by last_seen_minutes_ago
    user_list.sort(key=lambda u: (not u["is_online"], u["last_seen_minutes_ago"]))

    return {
        "online_count": online_count,
        "as_of": now.isoformat(),
        "users": user_list,
    }
