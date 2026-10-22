"""
Pruebas unitarias y de integración para el Simulador de Admisión y Probabilidad CRUCH.
Verifica:
1. Catálogo oficial CRUCH (10-15+ carreras, ponderaciones exactas = 100%, cortes 2024-2026).
2. Motor psicométrico IRT 3PL, simulación Monte Carlo y clasificación (Segura, Competitiva, Riesgosa).
3. Cálculo de la Brecha a la meta (puntos netos y aciertos adicionales requeridos).
4. Endpoints GET /api/paes/admission/careers y POST /api/paes/admission/simulate.
"""

import math

import pytest
from fastapi.testclient import TestClient

from main import app
from services.paes.cruch_data import (
    CRUCH_CAREERS,
    calculate_admission_chances,
    get_career_by_id,
    get_cruch_careers,
    normalize_nem_ranking,
    paes_score_to_raw_items,
    raw_items_to_paes_score,
)


@pytest.fixture
def client(disable_auth):
    return TestClient(app)


# --- 1. Pruebas de Catálogo y Datos CRUCH ---

def test_cruch_careers_catalog():
    careers = get_cruch_careers()
    assert len(careers) >= 10, "El catálogo debe tener al menos 10 carreras de alta demanda"

    top_universities = {"UCH", "PUC", "USACH", "UTFSM", "UdeC"}
    found_unis = {c["university_short"] for c in careers}
    assert top_universities.issubset(found_unis), f"Faltan universidades top chilenas: {top_universities - found_unis}"

    for c in careers:
        assert "id" in c and c["id"]
        assert "name" in c and c["name"]
        assert "university" in c and c["university"]
        assert "weights" in c
        assert "cutoffs" in c

        w = c["weights"]
        total_weight = (
            w.get("nem", 0.0)
            + w.get("ranking", 0.0)
            + w.get("lectura", 0.0)
            + w.get("m1", 0.0)
            + w.get("m2", 0.0)
            + w.get("ciencias", 0.0)
            + w.get("historia", 0.0)
        )
        assert math.isclose(total_weight, 1.0, abs_tol=1e-5), f"Ponderaciones de {c['id']} deben sumar exactamente 1.0"

        cutoffs = c["cutoffs"]
        assert "2024" in cutoffs and cutoffs["2024"] > 400
        assert "2025" in cutoffs and cutoffs["2025"] > 400
        assert "2026" in cutoffs and cutoffs["2026"] > 400


def test_get_career_by_id():
    med_uch = get_career_by_id("medicina-uch")
    assert med_uch is not None
    assert med_uch["name"] == "Medicina"
    assert med_uch["university_short"] == "UCH"

    not_found = get_career_by_id("carrera-inexistente-xyz")
    assert not_found is None


def test_normalize_nem_ranking():
    # Escala DEMRE directa (100 - 1000)
    assert normalize_nem_ranking(750) == 750.0
    assert normalize_nem_ranking(900.5) == 900.5

    # Escala de notas chilena oficial DEMRE (4.00 - 7.00)
    score_7 = normalize_nem_ranking(7.0)
    assert math.isclose(score_7, 1000.0, abs_tol=1.0)

    score_4 = normalize_nem_ranking(4.0)
    assert math.isclose(score_4, 100.0, abs_tol=1.0)

    score_5 = normalize_nem_ranking(5.0)
    assert math.isclose(score_5, 400.0, abs_tol=1.0)

    score_6 = normalize_nem_ranking(6.0)
    # 100 + 2.0 * 300 = 700
    assert math.isclose(score_6, 700.0, abs_tol=1.0)


def test_paes_score_to_raw_items():
    # 1000 puntos en M1 deben ser 60 aciertos
    assert paes_score_to_raw_items(1000, "M1") == 60
    # 100 puntos en M1 deben ser 0 aciertos
    assert paes_score_to_raw_items(100, "M1") == 0

    # Conversión bidireccional consistente
    raw_m1 = paes_score_to_raw_items(700, "M1")
    score_back = raw_items_to_paes_score(raw_m1, "M1")
    assert score_back >= 690


# --- 2. Pruebas del Motor Psicométrico IRT y Clasificación de Admisión ---

def test_calculate_admission_chances_safe():
    # Puntajes excepcionales para Medicina UCH (corte ~953)
    user_scores = {
        "m1": 980,
        "lectura": 950,
        "m2": 950,
        "ciencias": 970,
        "historia": 700,
    }
    result = calculate_admission_chances(
        user_scores=user_scores,
        nem=980,
        ranking=990,
        career_id="medicina-uch",
        num_simulations=2000,
        seed=123,
    )

    assert result["career_id"] == "medicina-uch"
    assert result["weighted_score"] >= 955.0
    assert result["probability"] >= 85.0
    assert result["category"] == "Segura"
    assert result["color"] == "green"
    assert result["is_above_cutoff"] is True
    assert result["weighted_gap"] <= 0


def test_calculate_admission_chances_risky():
    # Puntajes insuficientes para Medicina PUC
    user_scores = {
        "m1": 700,
        "lectura": 650,
        "m2": 600,
        "ciencias": 680,
        "historia": 600,
    }
    result = calculate_admission_chances(
        user_scores=user_scores,
        nem=700,
        ranking=720,
        career_id="medicina-puc",
        num_simulations=2000,
        seed=123,
    )

    assert result["career_id"] == "medicina-puc"
    assert result["probability"] < 50.0
    assert result["category"] == "Riesgosa"
    assert result["color"] == "red"
    assert result["is_above_cutoff"] is False
    assert result["weighted_gap"] > 100.0


def test_calculate_admission_chances_competitive():
    # Puntajes ajustados al corte de Ingeniería Civil Plan Común UCH (~896.5)
    # Buscamos un ponderado ~898 - 903
    user_scores = {
        "m1": 845,
        "lectura": 810,
        "m2": 840,
        "ciencias": 800,
        "historia": 600,
    }
    result = calculate_admission_chances(
        user_scores=user_scores,
        nem=830,
        ranking=840,
        career_id="ing-civil-uch",
        num_simulations=2000,
        seed=123,
    )

    assert result["career_id"] == "ing-civil-uch"
    assert 50.0 <= result["probability"] <= 85.0
    assert result["category"] == "Competitiva"
    assert result["color"] == "amber"


def test_brecha_meta_calculation():
    # Puntaje con brecha en Ingeniería Civil UTFSM (Corte 841.5)
    user_scores = {
        "m1": 780,
        "lectura": 700,
        "m2": 720,
        "ciencias": 700,
    }
    result = calculate_admission_chances(
        user_scores=user_scores,
        nem=800,
        ranking=820,
        career_id="ing-civil-utfsm",
        num_simulations=1000,
    )

    assert result["weighted_gap"] > 0
    m1_gap = result["gap_breakdown"]["m1"]
    assert m1_gap["net_points_needed"] > 0
    assert m1_gap["additional_correct_needed"] > 0
    assert m1_gap["target_score"] > m1_gap["current_score"]

    # Plan equilibrado
    assert len(result["balanced_plan"]) > 0
    for item in result["balanced_plan"]:
        assert "recommended_target_score" in item
        assert "additional_correct_needed" in item


def test_all_careers_summary_populated():
    user_scores = {"m1": 800, "lectura": 750, "m2": 700, "ciencias": 720}
    result = calculate_admission_chances(
        user_scores=user_scores,
        nem=800,
        ranking=820,
        career_id="derecho-uch",
    )

    summaries = result["all_careers_summary"]
    assert len(summaries) == len(CRUCH_CAREERS)
    # Verificamos que esté ordenado por probabilidad descendente
    probs = [s["probability"] for s in summaries]
    assert probs == sorted(probs, reverse=True)


# --- 3. Pruebas de Endpoints HTTP FastAPI ---

def test_api_get_careers(client: TestClient):
    response = client.get("/api/paes/admission/careers")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["total_careers"] >= 10
    assert isinstance(data["careers"], list)
    first_career = data["careers"][0]
    assert "id" in first_career
    assert "weights" in first_career
    assert "cutoffs" in first_career


def test_api_simulate_admission_valid(client: TestClient):
    payload = {
        "nem": 850,
        "ranking": 880,
        "career_id": "derecho-uch",
        "scores": {
            "m1": 800,
            "lectura": 850,
            "historia": 820,
            "ciencias": 700,
        },
    }
    response = client.post("/api/paes/admission/simulate", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    sim = data["simulation"]
    assert sim["career_id"] == "derecho-uch"
    assert "weighted_score" in sim
    assert "probability" in sim
    assert sim["category"] in {"Segura", "Competitiva", "Riesgosa"}
    assert "gap_breakdown" in sim
    assert "all_careers_summary" in sim


def test_api_simulate_admission_flat_scores(client: TestClient):
    # Soporte para payload plano sin objeto scores anidado
    payload = {
        "nem": 6.5,  # Escala de notas 1.0 - 7.0
        "ranking": 6.8,
        "career_id": "psicologia-puc",
        "m1": 750,
        "lectura": 820,
        "historia": 800,
    }
    response = client.post("/api/paes/admission/simulate", json=payload)
    assert response.status_code == 200
    data = response.json()
    sim = data["simulation"]
    assert sim["career_id"] == "psicologia-puc"
    assert sim["nem_normalized"] > 800  # Nota 6.5 normalizada a DEMRE


def test_api_simulate_career_not_found(client: TestClient):
    payload = {
        "nem": 700,
        "ranking": 700,
        "career_id": "carrera-fantasma-999",
        "m1": 600,
    }
    response = client.post("/api/paes/admission/simulate", json=payload)
    assert response.status_code == 404
    assert "no encontrada" in response.json()["detail"]


def test_api_simulate_validation_error(client: TestClient):
    # NEM inválido fuera de rango
    payload = {
        "nem": 0.5,  # Fuera de rango (mínimo 1.0)
        "ranking": 700,
        "career_id": "medicina-uch",
    }
    response = client.post("/api/paes/admission/simulate", json=payload)
    assert response.status_code == 422


def test_calculate_admission_chances_elective_max_sciences_chosen():
    # Derecho PUC permite electiva MAX (ciencias o historia)
    user_scores = {
        "m1": 700,
        "lectura": 700,
        "m2": 500,
        "ciencias": 850,
        "historia": 400,
    }
    result = calculate_admission_chances(
        user_scores=user_scores,
        nem=800,
        ranking=800,
        career_id="derecho-puc",
    )
    assert result["elective_used"] == "Ciencias"
    assert "ciencias" in result["gap_breakdown"]
    assert "historia" not in result["gap_breakdown"]
    balanced_subjs = [p["subject_code"] for p in result["balanced_plan"]]
    assert "CIENCIAS" in balanced_subjs
    assert "HISTORIA" not in balanced_subjs


# --- 4. TDD Edge-Case Tests (Requisitos Obligatorios y Validaciones Límite) ---

def test_career_requires_m2_disqualification_flag():
    """
    TDD: Si una carrera exige M2 (requires_m2=True, como Plan Común Beauchef o PUC)
    y el estudiante NO rindió M2 (o tiene puntaje default mínimo 100 sin rendir),
    el motor debe reportar explícitamente requires_m2=True y advertir la inhabilidad
    o cumplimiento del requisito excluyente DEMRE.
    """
    user_scores = {
        "m1": 950,
        "lectura": 900,
        "ciencias": 900,
        "m2": 100,  # No rendida o mínima
    }
    result = calculate_admission_chances(
        user_scores=user_scores,
        nem=950,
        ranking=950,
        career_id="ing-civil-uch",
    )
    assert result["career_id"] == "ing-civil-uch"
    assert "requires_m2" in result, "El resultado debe incluir si la carrera exige M2"
    assert result["requires_m2"] is True
    assert "m2_missing_warning" in result, "Debe advertir si M2 es obligatoria y el puntaje es el piso de no-rendición"
    assert result["m2_missing_warning"] is True


def test_normalize_nem_ranking_edge_cases():
    """
    TDD: Verifica que valores fuera del dominio chileno se comporten según la norma DEMRE.
    Notas chilenas: [4.0, 7.0] mapeadas a [100.0, 1000.0].
    Notas bajo 4.0 (reprobadas en media) no pueden dar menos del piso 100.0.
    Notas sobre 7.0 o puntajes sobre 1000 se acotan estrictamente a 1000.0.
    """
    assert normalize_nem_ranking(1.0) == 100.0
    assert normalize_nem_ranking(3.9) == 100.0
    assert normalize_nem_ranking(7.5) == 1000.0
    assert normalize_nem_ranking(1050.0) == 1000.0
    assert normalize_nem_ranking(-50.0) == 100.0

