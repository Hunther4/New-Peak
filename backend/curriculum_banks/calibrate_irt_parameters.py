"""
Script de calibración heurística de parámetros IRT (3PL: a, b, c) para preguntas PAES.

Parámetros 3PL:
- b (dificultad): max(-3.0, min(3.0, (d - 0.50) * 4.0))
- a (discriminación): 1.0 + 0.3 * (d - 0.50) acotado entre [0.75, 1.50]
- c (adivinación): 0.25 para 4 opciones, 0.20 para 5 opciones
- irt_status: 'CALIBRATED_HEURISTIC'
"""
import argparse
import json
import logging
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def compute_irt_parameters(difficulty_estimate: float | None, options_json: str | None) -> tuple[float, float, float]:
    """Calcula los parámetros (a, b, c) del modelo 3PL a partir de dificultad y opciones."""
    d = float(difficulty_estimate) if difficulty_estimate is not None else 0.50

    # b: parámetro de dificultad centrado en 0, mapeado a [-3.0, 3.0]
    b = max(-3.0, min(3.0, (d - 0.50) * 4.0))

    # a: parámetro de discriminación acotado a [0.75, 1.50]
    a_raw = 1.0 + 0.30 * (d - 0.50)
    a = max(0.75, min(1.50, a_raw))

    # c: pseudoadivinación (guessing) según número de opciones
    num_opts = 4
    if options_json:
        try:
            opts = json.loads(options_json)
            if isinstance(opts, list) and len(opts) > 0:
                num_opts = len(opts)
        except Exception:
            num_opts = 4

    c = 0.20 if num_opts == 5 else 0.25

    return round(a, 4), round(b, 4), round(c, 4)


def calibrate_questions(db_path: Path | str) -> Dict[str, Any]:
    """Calibra todas las preguntas en paes_questions asignando (a, b, c) y CALIBRATED_HEURISTIC."""
    path = Path(db_path)
    if not path.exists():
        raise FileNotFoundError(f"Base de datos no encontrada en: {path}")

    conn = sqlite3.connect(path)
    cursor = conn.cursor()

    cursor.execute("SELECT id, difficulty_estimate, options_json FROM paes_questions")
    rows = cursor.fetchall()

    if not rows:
        conn.close()
        logger.warning("No se encontraron preguntas en paes_questions.")
        return {"total_calibrated": 0}

    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S.%f")
    updates = []
    a_values = []
    b_values = []
    c_counts = {0.25: 0, 0.20: 0}

    for q_id, diff, opt_json in rows:
        a, b, c = compute_irt_parameters(diff, opt_json)
        updates.append((a, b, c, "CALIBRATED_HEURISTIC", now_str, q_id))
        a_values.append(a)
        b_values.append(b)
        c_counts[c] = c_counts.get(c, 0) + 1

    cursor.executemany(
        """
        UPDATE paes_questions
        SET irt_a = ?, irt_b = ?, irt_c = ?, irt_status = ?, updated_at = ?
        WHERE id = ?
        """,
        updates,
    )
    conn.commit()
    conn.close()

    metrics = {
        "total_calibrated": len(updates),
        "irt_a": {
            "min": min(a_values),
            "max": max(a_values),
            "mean": round(sum(a_values) / len(a_values), 4),
        },
        "irt_b": {
            "min": min(b_values),
            "max": max(b_values),
            "mean": round(sum(b_values) / len(b_values), 4),
        },
        "irt_c": c_counts,
        "status": "CALIBRATED_HEURISTIC",
    }

    logger.info("Calibración completada con éxito: %d preguntas calibradas.", len(updates))
    logger.info("Métricas a (discriminación): min=%.4f, max=%.4f, mean=%.4f", metrics["irt_a"]["min"], metrics["irt_a"]["max"], metrics["irt_a"]["mean"])
    logger.info("Métricas b (dificultad): min=%.4f, max=%.4f, mean=%.4f", metrics["irt_b"]["min"], metrics["irt_b"]["max"], metrics["irt_b"]["mean"])
    logger.info("Distribución c (adivinación): %s", metrics["irt_c"])

    return metrics


if __name__ == "__main__":
    default_db = Path(__file__).resolve().parent.parent / "peak.db"
    parser = argparse.ArgumentParser(description="Calibrar parámetros IRT para preguntas PAES.")
    parser.add_argument("--db", type=str, default=str(default_db), help="Ruta a peak.db")
    args = parser.parse_args()

    res = calibrate_questions(args.db)
    print(json.dumps(res, indent=2))
