"""
Tests para curriculum_banks/quality_filter.py
Verifica el filtrado de calidad de ítems PAES y la validación de KaTeX.
"""
from curriculum_banks.quality_filter import QualityFilter


def test_quality_filter_valid_item():
    item = {
        "stem": "¿Cuál es el valor de $x$ en la ecuación $2x = 10$?",
        "subtopic_id": "sub-test",
        "options": [
            {"key": "A", "text": "$5$", "is_correct": True},
            {"key": "B", "text": "$2$", "is_correct": False},
            {"key": "C", "text": "$10$", "is_correct": False},
            {"key": "D", "text": "$20$", "is_correct": False},
        ],
        "explanation": {
            "correct_solution": "Dividiendo por $2$ ambos lados, obtenemos $x = 5$."
        }
    }
    is_valid, errors = QualityFilter.validate_item(item, {"sub-test"})
    assert is_valid is True
    assert len(errors) == 0


def test_quality_filter_unbalanced_katex():
    item = {
        "stem": "¿Cuál es el valor de $x en la ecuación $2x = 10$?", # Delimitador desbalanceado
        "subtopic_id": "sub-test",
        "options": [
            {"key": "A", "text": "5", "is_correct": True},
            {"key": "B", "text": "2", "is_correct": False},
            {"key": "C", "text": "10", "is_correct": False},
            {"key": "D", "text": "20", "is_correct": False},
        ],
        "explanation": {
            "correct_solution": "Solución válida."
        }
    }
    is_valid, errors = QualityFilter.validate_item(item, {"sub-test"})
    assert is_valid is False
    assert any("KaTeX" in e for e in errors)


def test_quality_filter_multiple_correct_options():
    item = {
        "stem": "Selecciona la afirmación correcta sobre los números pares:",
        "subtopic_id": "sub-test",
        "options": [
            {"key": "A", "text": "2 es par", "is_correct": True},
            {"key": "B", "text": "4 es par", "is_correct": True}, # 2 correctas
            {"key": "C", "text": "3 es par", "is_correct": False},
            {"key": "D", "text": "5 es par", "is_correct": False},
        ],
        "explanation": {
            "correct_solution": "Explicación."
        }
    }
    is_valid, errors = QualityFilter.validate_item(item, {"sub-test"})
    assert is_valid is False
    assert any("exactamente 1 opción correcta" in e for e in errors)
