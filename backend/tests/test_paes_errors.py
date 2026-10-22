import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from main import app
from seed_paes import seed_paes_data


@pytest.fixture
def client(disable_auth):
    return TestClient(app)

def test_paes_errors_vault_empty(client, session: Session):
    seed_paes_data()
    # User 999 has no attempts
    resp = client.get("/api/paes/errors/vault?user_id=999")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_errors"] == 0
    assert data["items"] == []
    assert data["by_subject"] == {}
    assert data["by_distractor_type"] == {}

def test_paes_errors_lifecycle_and_revenge(client, session: Session):
    seed_paes_data()
    user_id = 1

    # 1. Iniciar sesión de práctica
    start_resp = client.post("/api/paes/study/session/start", json={
        "session_mode": "PRACTICE",
        "subject_code": "M1",
        "question_count": 3
    })
    assert start_resp.status_code == 200
    s_data = start_resp.json()
    sess_id = s_data["session_id"]
    q0 = s_data["questions"][0]

    # 2. Registrar un intento erróneo con causa de cálculo
    attempt_resp = client.post("/api/paes/study/session/submit", json={
        "session_id": sess_id,
        "question_id": q0["id"],
        "selected_option": "Z_WRONG",
        "time_spent_seconds": 35,
        "perceived_confidence": 3,
        "mistake_cause": "CALCULO"
    })
    assert attempt_resp.status_code == 200
    assert attempt_resp.json()["is_correct"] is False

    # 3. Consultar GET /api/paes/errors/vault
    vault_resp = client.get(f"/api/paes/errors/vault?user_id={user_id}")
    assert vault_resp.status_code == 200
    vault_data = vault_resp.json()
    assert vault_data["total_errors"] >= 1
    assert "M1" in vault_data["by_subject"]
    assert "CALCULO" in vault_data["by_distractor_type"] or "CALCULO" in vault_data["by_mistake_cause"]
    assert any(item["question_id"] == q0["id"] for item in vault_data["items"])

    # 4. Generar sesión de revancha POST /api/paes/errors/revenge-session
    rev_resp = client.post("/api/paes/errors/revenge-session", json={
        "subject_code": "M1",
        "question_count": 10,
        "user_id": user_id
    })
    assert rev_resp.status_code == 200
    rev_data = rev_resp.json()
    assert rev_data["session_mode"] == "REVENGE"
    assert rev_data["total_questions"] >= 1
    assert any(q["id"] == q0["id"] for q in rev_data["questions"])

    # 5. Obtener variante paramétrica con SymPy: GET /api/paes/questions/{question_id}/variant
    var_resp = client.get(f"/api/paes/questions/{q0['id']}/variant")
    assert var_resp.status_code == 200
    var_data = var_resp.json()
    assert var_data["original_question_id"] == q0["id"]
    assert var_data["is_variant"] is True
    assert "stem" in var_data and len(var_data["stem"]) > 0
    assert len(var_data["options"]) == 4
    correct_opts = [o for o in var_data["options"] if o.get("is_correct")]
    assert len(correct_opts) == 1
    assert "explanation" in var_data

    # También verificar ruta alternativa bajo /errors/questions/{id}/variant
    alt_var_resp = client.get(f"/api/paes/errors/questions/{q0['id']}/variant")
    assert alt_var_resp.status_code == 200

def test_paes_variant_not_found(client, session: Session):
    resp = client.get("/api/paes/questions/non-existent-question-id-12345/variant")
    assert resp.status_code == 404

def test_revenge_session_no_errors(client, session: Session):
    seed_paes_data()
    # Usuario sin errores
    resp = client.post("/api/paes/errors/revenge-session", json={
        "subject_code": "M1",
        "question_count": 10,
        "user_id": 99999
    })
    assert resp.status_code == 400
    assert "No tienes preguntas pendientes" in resp.json()["detail"]
