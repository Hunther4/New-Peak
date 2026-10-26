import pytest
from sqlmodel import Session

from seed_paes import seed_paes_data


@pytest.fixture
def client(enrolled_user):
    """Real principal enrolled through the production services (conftest)."""
    return enrolled_user.client

def test_error_notebook_and_revenge_session(client, session: Session):
    seed_paes_data()

    # 1. Start a practice session
    start_resp = client.post("/api/paes/study/session/start", json={
        "session_mode": "PRACTICE",
        "subject_code": "M1",
        "question_count": 5
    })
    assert start_resp.status_code == 200
    session_data = start_resp.json()
    sess_id = session_data["session_id"]
    q0 = session_data["questions"][0]

    # 2. Submit an incorrect attempt
    attempt_resp = client.post("/api/paes/study/session/submit", json={
        "session_id": sess_id,
        "question_id": q0["id"],
        "selected_option": "Z_INCORRECT",
        "time_spent_seconds": 45,
        "perceived_confidence": 4,
        "mistake_cause": "CALCULO"
    })
    assert attempt_resp.status_code == 200
    assert attempt_resp.json()["is_correct"] is False

    # 3. Check GET /api/paes/study/error_notebook
    nb_resp = client.get("/api/paes/study/error_notebook?subject_code=M1")
    assert nb_resp.status_code == 200
    nb_data = nb_resp.json()
    assert nb_data["total_errors"] >= 1
    found_ids = [item["question_id"] for item in nb_data["items"]]
    assert q0["id"] in found_ids

    # 4. Start a REVENGE session
    rev_resp = client.post("/api/paes/study/session/start", json={
        "session_mode": "REVENGE",
        "subject_code": "M1",
        "question_count": 5
    })
    assert rev_resp.status_code == 200
    rev_data = rev_resp.json()
    assert rev_data["session_mode"] == "REVENGE"
    assert rev_data["total_questions"] >= 1
    assert any(q["id"] == q0["id"] for q in rev_data["questions"])
