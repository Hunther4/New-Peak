"""
Pruebas unitarias para el generador autónomo de contenido PAES.
Verifica generación simbólica CAS, consistencia pedagógica y calibración 3PL IRT.
"""
import pytest
from sqlmodel import Session

from core.database import engine
from curriculum_banks.auto_content_generator import AutoContentGenerator


@pytest.fixture
def db_session():
    with Session(engine) as session:
        yield session


def test_generator_m1_batch(db_session):
    generator = AutoContentGenerator(db_session=db_session)
    items, rejections = generator.generate_batch("M1", count=4, save_to_db=False)

    assert len(items) == 4
    for item in items:
        assert item["stem"]
        assert len(item["options"]) == 4
        assert item["irt_status"] == "CALIBRATED_HEURISTIC"
        assert item["irt_a"] is not None
        assert item["irt_b"] is not None
        assert item["irt_c"] == 0.25
        # Comprobar que solo haya 1 opción correcta
        correct_opts = [o for o in item["options"] if o["is_correct"]]
        assert len(correct_opts) == 1
        assert "explanation" in item
        assert "correct_solution" in item["explanation"]


def test_generator_m2_batch(db_session):
    generator = AutoContentGenerator(db_session=db_session)
    items, rejections = generator.generate_batch("M2", count=3, save_to_db=False)

    assert len(items) == 3
    for item in items:
        assert item["stem"]
        assert len(item["options"]) == 4


def test_generator_humanities_and_sciences(db_session):
    generator = AutoContentGenerator(db_session=db_session)
    for subj in ["LECTURA", "CIENCIAS", "HISTORIA"]:
        items, _ = generator.generate_batch(subj, count=2, save_to_db=False)
        assert len(items) == 2
        for it in items:
            assert len(it["options"]) == 4
            assert it["irt_a"] is not None
