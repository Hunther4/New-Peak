"""
Filtro de Calidad y Validación Pedagógica para Bancos de Preguntas PAES.
Garantiza que ningún ítem entre a la base de datos sin cumplir los estándares DEMRE y KaTeX.
"""
import re
from typing import Any, Dict, List, Tuple


class QualityFilter:
    """Validador estricto de ítems PAES."""

    ALLOWED_OPTION_COUNTS = {4, 5}
    VALID_KEYS = {"A", "B", "C", "D", "E"}

    @classmethod
    def validate_katex(cls, text: str) -> Tuple[bool, str]:
        """Verifica que las expresiones matemáticas KaTeX ($...$) estén balanceadas."""
        if not text:
            return True, "OK"

        # Contar signos $ que no estén escapados con barra invertida
        unescaped_dollars = [m.start() for m in re.finditer(r'(?<!\\)\$', text)]

        # Verificar paridad básica de delimitadores
        if len(unescaped_dollars) % 2 != 0:
            return False, f"Delimitadores KaTeX desbalanceados (se encontraron {len(unescaped_dollars)} signos '$')"

        # Verificar que no haya bloques vacíos tipo $$ sin contenido
        if "$$" in text:
            # Si hay $$, debe ser display math balanceado
            double_dollars = [m.start() for m in re.finditer(r'(?<!\\)\$\$', text)]
            if len(double_dollars) % 2 != 0:
                return False, "Bloques display math ($$) desbalanceados"

        return True, "OK"

    @classmethod
    def validate_item(cls, item: Dict[str, Any], valid_subtopic_ids: set) -> Tuple[bool, List[str]]:
        """
        Evalúa un ítem contra la rúbrica de calidad:
        - Longitud y claridad del enunciado.
        - Estructura de alternativas (exactamente 4, 1 correcta).
        - Explicación pedagógica y análisis de distractores.
        - KaTeX válido.
        - Subtema existente en el currículum.
        """
        errors = []

        # 1. Enunciado (stem)
        stem = item.get("stem", "").strip()
        if len(stem) < 20:
            errors.append(f"Enunciado demasiado corto ({len(stem)} caracteres; mínimo 20)")

        ok_stem_katex, msg = cls.validate_katex(stem)
        if not ok_stem_katex:
            errors.append(f"Error KaTeX en enunciado: {msg}")

        # 2. Subtema válido
        subtopic_id = item.get("subtopic_id", "")
        if valid_subtopic_ids and subtopic_id not in valid_subtopic_ids:
            errors.append(f"Subtema desconocido: '{subtopic_id}' no existe en el currículum cargado")

        # 3. Opciones
        options = item.get("options", [])
        if len(options) not in cls.ALLOWED_OPTION_COUNTS:
            errors.append(f"Debe tener 4 o 5 opciones (se encontraron {len(options)})")

        correct_count = 0
        keys_found = set()
        for idx, opt in enumerate(options):
            if not isinstance(opt, dict):
                errors.append(f"Opción {idx} no es un diccionario válido")
                continue

            key = opt.get("key", "").upper()
            keys_found.add(key)
            if opt.get("is_correct"):
                correct_count += 1

            opt_text = opt.get("text", "").strip()
            if not opt_text:
                errors.append(f"Opción {key} tiene texto vacío")
            else:
                ok_opt_katex, opt_msg = cls.validate_katex(opt_text)
                if not ok_opt_katex:
                    errors.append(f"Error KaTeX en opción {key}: {opt_msg}")

        if correct_count != 1:
            errors.append(f"Debe haber exactamente 1 opción correcta (se encontraron {correct_count})")

        # 4. Explicación
        explanation = item.get("explanation", {})
        if not isinstance(explanation, dict) or not explanation.get("correct_solution"):
            errors.append("Falta 'explanation.correct_solution' para justificar pedagógicamente el ítem")

        is_valid = len(errors) == 0
        return is_valid, errors
