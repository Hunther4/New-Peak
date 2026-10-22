"""
Tests para la Rutina Semanal y Sesión Rápida de 1-Clic PAES.
Verifica:
1. Obtención y persistencia de la rutina de 7 días (Lunes a Domingo).
2. Asignación de materias válidas ('M1', 'LECTURA', 'CIENCIAS', 'M2', 'HISTORIA', 'REST').
3. Endpoint de Quick-Start que resuelve el día de la semana y lanza la sesión automáticamente.

Nota: las materias de la rutina se validan contra las asignaturas que existen
en la base de datos, por lo que los tests siembran LECTURA/CIENCIAS/M2 antes
de asignarlas.
"""
import pytest
from fastapi.testclient import TestClient

from main import app
from seed_paes import seed_paes_data
from services.paes.seed_multidisciplinary import seed_multidisciplinary


@pytest.fixture
def client(disable_auth):
    return TestClient(app)


@pytest.fixture
def full_curriculum(session):
    """Siembra M1 + las asignaturas multidisciplinares (LECTURA, M2, CIENCIAS...)."""
    seed_paes_data()
    seed_multidisciplinary(session)
    return session


def test_get_default_weekly_routine(client):
    resp = client.get("/api/paes/study/routine?user_id=1")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    routine = data["routine"]
    days = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
    for day in days:
        assert day in routine
        assert routine[day] in {"M1", "LECTURA", "CIENCIAS", "M2", "HISTORIA", "REST"}


def test_update_weekly_routine(client, full_curriculum):
    new_routine = {
        "monday": "LECTURA",
        "tuesday": "M1",
        "wednesday": "CIENCIAS",
        "thursday": "M1",
        "friday": "M2",
        "saturday": "M1",
        "sunday": "REST",
    }
    resp = client.post("/api/paes/study/routine", json={"user_id": 1, "routine": new_routine})
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    assert data["routine"]["monday"] == "LECTURA"
    assert data["routine"]["wednesday"] == "CIENCIAS"

    # Verificar persistencia en GET
    get_resp = client.get("/api/paes/study/routine?user_id=1")
    assert get_resp.status_code == 200
    assert get_resp.json()["routine"]["monday"] == "LECTURA"


def test_quick_start_resolves_today_session(client):
    seed_paes_data()
    # Ejecutar quick-start
    resp = client.post("/api/paes/study/routine/quick-start", json={
        "user_id": 1,
        "question_count": 15
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    assert "session_id" in data
    assert "today_day" in data
    assert "subject_code" in data
    assert len(data["questions"]) > 0
