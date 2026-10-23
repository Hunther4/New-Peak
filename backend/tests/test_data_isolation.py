"""S4 data isolation — a second enrolled user is invisible to the first.

Acceptance criteria:
  DO-01  no endpoint accepts a client-supplied ``user_id``: the OpenAPI schema
         of the 13 affected operations declares none, and a request that still
         carries one validates instead of being rejected (DO-01-S1);
         a forged id serves only the caller's rows (DO-01-S2); a write lands
         only on the caller's learning-state row — fsrs_stability, leitner_box,
         mastery_score, next_review_at — leaving the other user's row
         byte-for-byte unchanged (DO-01-S3).
  DO-02  the two raw session loads are owner-scoped: submitting into another
         user's session is a 404 with their counters unchanged (DO-02-S1),
         finalizing another user's exam is a 404 with their IRT ``theta``
         unchanged (DO-02-S2), and the caller's own session still works
         (DO-02-S3).
  DO-11  every response that still carries ``user_id`` reports the
         server-derived owner — the principal id, never the forged value.

Both users in every scenario are REAL: they enroll, complete the
challenge → verify round and obtain a bearer session through the production
services exactly as S2/S3 wired them (never a faked principal).

Run from the repo root:
  backend\\venv\\Scripts\\python.exe -m pytest backend/tests/test_data_isolation.py -q
"""
import base64

import pytest
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from core.crypto_keys import canonical_message
from core.limiter import limiter
from models.paes_models import (
    PaesAssessmentState,
    PaesCompetency,
    PaesCurriculumVersion,
    PaesEjeTematico,
    PaesLearningState,
    PaesQuestion,
    PaesStudySession,
    PaesSubject,
    PaesSubtopic,
    PaesTopic,
)

ENROLL_PATH = "/api/auth/enroll"
CHALLENGE_PATH = "/api/auth/challenge"
VERIFY_PATH = "/api/auth/verify"

#: The 13 DO-01 sites, as (method, path) OpenAPI operations.
ISOLATION_OPERATIONS = [
    ("get", "/api/paes/fsrs/status"),
    ("get", "/api/paes/curriculum/subtopics"),
    ("post", "/api/paes/study/session/start"),
    ("get", "/api/paes/study/error_notebook"),
    ("post", "/api/paes/study/session/{session_id}/finalize_exam"),
    ("post", "/api/paes/study/session/submit"),
    ("post", "/api/paes/study/plan/generate"),
    ("get", "/api/paes/study/routine"),
    ("post", "/api/paes/study/routine"),
    ("post", "/api/paes/study/routine/quick-start"),
    ("get", "/api/paes/errors/vault"),
    ("post", "/api/paes/errors/revenge-session"),
    ("post", "/api/coach/chat"),
]


@pytest.fixture(autouse=True)
def _reset_limiter():
    """Every test starts with clean per-minute challenge/verify budgets."""
    limiter.reset()
    yield
    limiter.reset()


# --- production-services helpers (S2/S3 pattern) ------------------------------

def _make_p256():
    return ec.generate_private_key(ec.SECP256R1())


def _spki_b64(key) -> str:
    spki = key.public_key().public_bytes(
        serialization.Encoding.DER,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    return base64.b64encode(spki).decode("ascii")


def _challenge_signed(privkey, challenge: dict) -> str:
    """Sign the challenge body verbatim — the six server-supplied lines."""
    message = canonical_message(
        challenge_id=challenge["challenge_id"],
        nonce=challenge["nonce"],
        email=challenge["email"],
        origin=challenge["origin"],
        deployment_id=challenge["deployment_id"],
    )
    raw = privkey.sign(message, ec.ECDSA(hashes.SHA256()))
    return base64.b64encode(raw).decode("ascii")


def _enroll_and_login(client: TestClient, email: str):
    """A real enrolled user: enroll → challenge → verify. Returns (headers, uid, privkey)."""
    privkey = _make_p256()
    response = client.post(
        ENROLL_PATH,
        json={"email": email, "public_key_b64": _spki_b64(privkey), "label": "iso"},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    uid = body["user_id"]
    challenge = client.post(
        CHALLENGE_PATH, json={"email": email, "device_id": body["device_id"]}
    ).json()
    response = client.post(
        VERIFY_PATH,
        json={
            "challenge_id": challenge["challenge_id"],
            "signature_b64": _challenge_signed(privkey, challenge),
        },
    )
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['token']}"}, uid, privkey


# --- curriculum + learning-state seeds ----------------------------------------

def _seed_curriculum(session: Session):
    """One M1 subject with two subtopics, each holding one question."""
    cv = PaesCurriculumVersion(id="cv-iso", code="DEMRE-ISO-2026", name="Isolation 2026", year=2026)
    session.add(cv)
    session.flush()
    subject = PaesSubject(id="subj-iso-m1", curriculum_version_id=cv.id, code="M1", name="Prueba M1")
    session.add(subject)
    session.flush()
    comp = PaesCompetency(id="comp-iso", code="RESOLVER_PROBLEMAS", name="Resolver Problemas")
    session.add(comp)
    session.flush()
    eje = PaesEjeTematico(id="eje-iso", subject_id="subj-iso-m1", name="Números", order_index=1)
    session.add(eje)
    session.flush()
    topic = PaesTopic(id="top-iso-a", eje_id=eje.id, name="Tema A", order_index=1)
    topic_b = PaesTopic(id="top-iso-b", eje_id=eje.id, name="Tema B", order_index=2)
    session.add_all([topic, topic_b])
    session.flush()
    sub_a = PaesSubtopic(id="sub-iso-a", topic_id=topic.id, name="Subtema A", slug="iso-sub-a")
    sub_b = PaesSubtopic(id="sub-iso-b", topic_id=topic_b.id, name="Subtema B", slug="iso-sub-b")
    session.add_all([sub_a, sub_b])
    session.flush()
    for idx, sub in enumerate([sub_a, sub_b]):
        session.add(
            PaesQuestion(
                id=f"q-iso-{idx}",
                subtopic_id=sub.id,
                skill_id=comp.id,
                stem=f"Pregunta iso {idx}",
                options_json=(
                    '[{"id": "A", "content": "A", "is_correct": true},'
                    ' {"id": "B", "content": "B", "is_correct": false}]'
                ),
                explanation_json="{}",
                difficulty_estimate=0.5,
            )
        )
    session.commit()
    return subject, sub_a, sub_b


def _seed_learning_state(session: Session, user_id: int, subtopic_id: str) -> PaesLearningState:
    """A distinctive per-user learning-state row (values are asserted later)."""
    row = PaesLearningState(
        id=f"ls-iso-{user_id}-{subtopic_id}",
        user_id=user_id,
        subtopic_id=subtopic_id,
        mastery_score=0.42,
        leitner_box=2,
        fsrs_stability=7.5,
        fsrs_difficulty=6.25,
        total_attempts=10,
        total_successes=7,
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def _state_tuple(row: PaesLearningState):
    return (
        row.fsrs_stability,
        row.leitner_box,
        row.mastery_score,
        row.next_review_at,
        row.total_attempts,
        row.total_successes,
        row.last_practiced_at,
    )


def _reload_learning_state(session: Session, state_id: str) -> PaesLearningState:
    session.expire_all()
    return session.get(PaesLearningState, state_id)


def _start_session(client: TestClient, headers, mode: str = "PRACTICE", **extra) -> dict:
    response = client.post(
        "/api/paes/study/session/start",
        json={"session_mode": mode, "subject_code": "M1", "question_count": 2, **extra},
        headers=headers,
    )
    assert response.status_code == 200, response.text
    return response.json()


# --- DO-01-S1: the schema no longer offers a user id --------------------------

def test_openapi_13_operations_declare_no_user_id(client):
    schema = client.get("/openapi.json").json()
    for method, path in ISOLATION_OPERATIONS:
        operation = schema["paths"][path][method]
        parameter_names = [p["name"] for p in operation.get("parameters", [])]
        assert "user_id" not in parameter_names, f"{method} {path}: {parameter_names}"
        request_body = operation.get("requestBody")
        if not request_body:
            continue
        for content in request_body["content"].values():
            ref = content["schema"].get("$ref")
            if ref:
                model = schema["components"]["schemas"][ref.rsplit("/", 1)[-1]]
            else:
                model = content["schema"]
            assert "user_id" not in model.get("properties", {}), (
                f"{method} {path}: body model still declares user_id"
            )


def test_requests_carrying_unknown_user_id_still_validate(client, session):
    """An unknown ``user_id`` is ignored, never rejected (DO-01-S1)."""
    _, _, _ = _seed_curriculum(session)
    headers, caller_id, _ = _enroll_and_login(client, "unknown-id@example.com")

    checks = [
        ("get", "/api/paes/study/routine?user_id=999", None),
        ("get", "/api/paes/fsrs/status?user_id=999", None),
        ("get", "/api/paes/errors/vault?user_id=999", None),
        (
            "post",
            "/api/paes/study/routine",
            {"user_id": 999, "routine": {"monday": "M1"}},
        ),
        (
            "post",
            "/api/paes/study/routine/quick-start",
            {"user_id": 999, "question_count": 1},
        ),
        (
            "post",
            "/api/paes/errors/revenge-session",
            {"user_id": 999, "subject_code": "M1", "question_count": 2},
        ),
    ]
    for method, url, payload in checks:
        if method == "get":
            response = client.get(url, headers=headers)
        else:
            response = client.post(url, json=payload, headers=headers)
        assert response.status_code != 422, f"{method} {url}: {response.status_code} {response.text}"


# --- DO-01-S2 / DO-11: a forged id serves only the caller's rows ---------------

def test_forged_user_id_serves_only_the_callers_rows(client, session):
    _, sub_a, sub_b = _seed_curriculum(session)
    headers_a, caller_id, _ = _enroll_and_login(client, "forge-a@example.com")
    _, other_id, _ = _enroll_and_login(client, "forge-b@example.com")
    _seed_learning_state(session, caller_id, sub_a.id, )
    _seed_learning_state(session, other_id, sub_b.id)

    # A forges B's id into the query; the response must still be A's data.
    status = client.get(f"/api/paes/fsrs/status?user_id={other_id}", headers=headers_a).json()
    tracked = {item["subtopic_id"] for item in status["subtopics"]}
    assert status["user_id"] == caller_id  # server-derived, never the forged value
    assert status["user_id"] != other_id
    assert sub_b.id not in tracked  # B's row is invisible
    assert sub_a.id in tracked  # the caller's own row is what resolved

    curriculum = client.get(f"/api/paes/curriculum/subtopics?user_id={other_id}", headers=headers_a).json()
    by_id = {entry["id"]: entry for entry in curriculum["subtopics"]}
    assert by_id[sub_a.id]["mastery"] == 0.42  # A's state
    assert by_id[sub_b.id]["mastery"] == 0.0  # A has no state on B's subtopic


def test_forged_revenge_session_serves_only_the_callers_errors(client, session):
    _, sub_a, sub_b = _seed_curriculum(session)
    headers_a, caller_id, _ = _enroll_and_login(client, "rev-a@example.com")
    _, other_id, _ = _enroll_and_login(client, "rev-b@example.com")

    started = _start_session(client, headers_a)
    response = client.post(
        "/api/paes/study/session/submit",
        json={
            "session_id": started["session_id"],
            "question_id": started["questions"][0]["id"],
            "selected_option": "B",  # wrong on purpose
            "time_spent_seconds": 10,
        },
        headers=headers_a,
    )
    assert response.status_code == 200, response.text

    # A forges B's id into the body; only A's own failed question may come back.
    response = client.post(
        "/api/paes/errors/revenge-session",
        json={"user_id": other_id, "subject_code": "M1", "question_count": 10},
        headers=headers_a,
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["session_mode"] == "REVENGE"
    assert data["total_questions"] >= 1  # A HAS one unmastered question
    assert any(q["id"] == started["questions"][0]["id"] for q in data["questions"])


# --- DO-01-S3: a write lands on the caller's row only --------------------------

def test_submit_updates_only_the_callers_learning_state(client, session):
    subject, sub_a, sub_b = _seed_curriculum(session)
    headers_a, caller_id, _ = _enroll_and_login(client, "wr-a@example.com")
    _, other_id, _ = _enroll_and_login(client, "wr-b@example.com")
    own_state = _seed_learning_state(session, caller_id, sub_a.id)
    other_state = _seed_learning_state(session, other_id, sub_a.id)
    own_before = _state_tuple(own_state)
    other_before = _state_tuple(other_state)

    started = _start_session(client, headers_a, subtopic_slug="iso-sub-a")
    question = started["questions"][0]
    response = client.post(
        "/api/paes/study/session/submit",
        json={
            "session_id": started["session_id"],
            "question_id": question["id"],
            "selected_option": "A",  # correct
            "time_spent_seconds": 15,
        },
        headers=headers_a,
    )
    assert response.status_code == 200, response.text  # DO-02-S3: own session works
    assert response.json()["session_progress"]["total_answered"] == 1

    own_after = _state_tuple(_reload_learning_state(session, own_state.id))
    other_after = _state_tuple(_reload_learning_state(session, other_state.id))
    assert own_after != own_before  # the caller's row moved
    assert other_after == other_before  # byte-for-byte unchanged


# --- DO-02-S1: submitting into another user's session is a 404 -----------------

def test_submit_into_another_users_session_is_a_404(client, session):
    subject, sub_a, sub_b = _seed_curriculum(session)
    headers_a, _, _ = _enroll_and_login(client, "sec-a@example.com")
    headers_b, other_id, _ = _enroll_and_login(client, "sec-b@example.com")
    _seed_learning_state(session, other_id, sub_b.id)

    other_session = _start_session(client, headers_b, subtopic_slug="iso-sub-b")
    session_row = session.get(PaesStudySession, other_session["session_id"])
    session.expire_all()
    row_before = (session_row.total_items, session_row.correct_items, session_row.user_id)

    response = client.post(
        "/api/paes/study/session/submit",
        json={
            "session_id": other_session["session_id"],
            "question_id": other_session["questions"][0]["id"],
            "selected_option": "A",
            "time_spent_seconds": 12,
        },
        headers=headers_a,
    )
    assert response.status_code == 404  # never 403 — existence stays unconfirmed

    session.expire_all()
    row_after = session.get(PaesStudySession, other_session["session_id"])
    assert (row_after.total_items, row_after.correct_items, row_after.user_id) == row_before


# --- DO-02-S2: finalizing another user's exam is a 404 -------------------------

def test_finalize_another_users_exam_is_a_404(client, session):
    subject, sub_a, sub_b = _seed_curriculum(session)
    headers_a, _, _ = _enroll_and_login(client, "fin-a@example.com")
    headers_b, other_id, _ = _enroll_and_login(client, "fin-b@example.com")

    # B owns an exam session, scores it, and the IRT estimate lands on B's row.
    started = _start_session(client, headers_b, mode="EXAM")
    answers = [
        {"question_id": q["id"], "selected_option": "A", "time_spent_seconds": 5}
        for q in started["questions"]
    ]
    own_final = client.post(
        f"/api/paes/study/session/{started['session_id']}/finalize_exam",
        json={"answers": answers, "subject_code": "M1"},
        headers=headers_b,
    )
    assert own_final.status_code == 200, own_final.text  # DO-02-S3: own exam works

    session.expire_all()
    theta_row = session.exec(
        select(PaesAssessmentState).where(PaesAssessmentState.user_id == other_id)
    ).first()
    assert theta_row is not None and theta_row.user_id == other_id
    theta_before = (theta_row.theta, theta_row.theta_se, theta_row.total_scored_items_answered)

    # A finalizes B's exam session id: 404, and B's theta must not budge.
    forged = client.post(
        f"/api/paes/study/session/{started['session_id']}/finalize_exam",
        json={
            "answers": [
                {"question_id": q["id"], "selected_option": "B", "time_spent_seconds": 7}
                for q in started["questions"]
            ],
            "subject_code": "M1",
        },
        headers=headers_a,
    )
    assert forged.status_code == 404  # never 403 — existence stays unconfirmed

    session.expire_all()
    theta_after = session.get(PaesAssessmentState, theta_row.id)
    assert (theta_after.theta, theta_after.theta_se, theta_after.total_scored_items_answered) == theta_before


# --- DO-01: the coach chat body accepts no user_id -----------------------------

def test_coach_chat_accepts_no_user_id(client, session):
    schema = client.get("/openapi.json").json()
    body = schema["paths"]["/api/coach/chat"]["post"]["requestBody"]
    for content in body["content"].values():
        ref = content["schema"].get("$ref")
        model = schema["components"]["schemas"][ref.rsplit("/", 1)[-1]] if ref else content["schema"]
        assert "user_id" not in model.get("properties", {}), "CoachChatRequest still carries user_id"

    # The documented validation: an unknown user_id in the body does not 422.
    from unittest.mock import patch

    from api.routes.coach import CoachChatResponse

    with patch("api.routes.coach.execute_with_router") as mock_router:
        mock_router.return_value = CoachChatResponse(reply="ok")
        response = client.post(
            "/api/coach/chat",
            json={"message": "hola", "user_id": 999},
        )
    assert response.status_code == 200, response.text
