"""Tests for backend/seed_models.py — listas canónicas sin duplicados y puntajes vivos."""
from sqlmodel import Session, select

import seed_models
from models.models import AiModel


def _all_seed_dicts():
    return (
        seed_models.GROQ_MODELS
        + seed_models.OPENROUTER_MODELS
        + seed_models.GENERALCOMPUTE_MODELS
        + seed_models.LM_STUDIO_MODEL
    )


def test_no_duplicate_model_ids_across_lists():
    """Ningún model_id aparece dos veces entre las listas semilla."""
    ids = [m["model_id"] for m in _all_seed_dicts()]
    assert len(ids) == len(set(ids))


def test_generalcompute_models_present_and_consistent():
    """GENERALCOMPUTE_MODELS: provider correcto, campos requeridos, ids conocidos."""
    gc = seed_models.GENERALCOMPUTE_MODELS
    assert len(gc) == 5
    expected_ids = {"minimax-m2.7", "gpt-oss-120b", "deepseek-v3.1", "deepseek-v3.2", "gemma-4-31B-it"}
    assert {m["model_id"] for m in gc} == expected_ids
    for m in gc:
        assert m["provider"] == "generalcompute"
        assert m["capabilities"]
        assert m["context_window"] > 0
        assert 0 <= m["score"] <= 100


def test_live_scores_spot_check():
    """Puntajes vivos: Qwen3 Coder 88 y modelo local 50 (bloques viejos eliminados)."""
    by_id = {m["model_id"]: m for m in _all_seed_dicts()}
    assert by_id["qwen/qwen3-coder:free"]["score"] == 88
    assert by_id["local-model"]["score"] == 50


def test_seed_populates_fresh_db(engine, monkeypatch):
    """seed() puebla la DB de test sin tocar ninguna DB real."""
    monkeypatch.setattr(seed_models, "engine", engine)
    seed_models.seed()
    with Session(engine) as s:
        models = s.exec(select(AiModel)).all()
    expected = (
        len(seed_models.GROQ_MODELS)
        + len(seed_models.OPENROUTER_MODELS)
        + len(seed_models.GENERALCOMPUTE_MODELS)
        + len(seed_models.LM_STUDIO_MODEL)
    )
    assert len(models) == expected
    ids = [m.model_id for m in models]
    assert len(ids) == len(set(ids))
    providers = {m.provider for m in models}
    assert "generalcompute" in providers


def test_seed_py_lm_row_reuses_canonical_values():
    """seed.py no duplica valores: su fila lm_studio es la canónica de seed_models."""
    import seed as legacy_seed

    lm_rows = [m for m in legacy_seed.MODELS if m.provider == "lm_studio"]
    assert len(lm_rows) == 1
    row = lm_rows[0]
    canon = seed_models.LM_STUDIO_MODEL[0]
    assert row.model_id == canon["model_id"] == "local-model"
    assert row.name == canon["name"]
    assert row.score == canon["score"] == 50
    assert row.capabilities == canon["capabilities"]
    assert row.context_window == canon["context_window"]
    assert row.is_active is True
