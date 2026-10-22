"""Canonical taxonomy for PAES distractor types.

The seeded banks (``curriculum_banks/``, ``services/paes/seed_*``) emit
fine-grained values such as ``CALCULATION_ERROR`` or ``SIGN_MISTAKE``, while
the question generators and the error aggregator use coarse values such as
``CALCULO`` or ``TRAMPA_HEURISTICA``. Two incompatible taxonomies meant that
every bank-sourced distractor fell into the generic "conceptual confusion"
bucket and the error analytics were meaningless.

This module owns ONE canonical taxonomy plus the explicit mapping table that
normalizes every observed raw value into it. Unknown values land in the
documented catch-all bucket ``NO_CLASIFICADO`` — never silently in
``CONCEPTUAL``.
"""
from typing import Dict, Optional, Tuple

__all__ = [
    "CANONICAL_DISTRACTOR_TYPES",
    "CANONICAL_UNCLASSIFIED",
    "CANONICAL_GENERIC",
    "DISTRACTOR_TYPE_ALIASES",
    "CANONICAL_LABELS",
    "normalize_distractor_type",
    "canonical_label",
]

# --- Canonical buckets -------------------------------------------------------
CANONICAL_CONCEPTUAL = "CONCEPTUAL"
CANONICAL_PROCEDURAL = "PROCEDIMENTAL"
CANONICAL_CALCULO = "CALCULO"
CANONICAL_INTERPRETACION = "INTERPRETACION"
CANONICAL_LECTURA = "LECTURA"
CANONICAL_TRAMPA_HEURISTICA = "TRAMPA_HEURISTICA"
CANONICAL_MEMORIA = "MEMORIA"
CANONICAL_ESTRATEGIA = "ESTRATEGIA"
CANONICAL_TIEMPO = "TIEMPO"
CANONICAL_AZAR = "AZAR"
CANONICAL_DISTRACTOR = "DISTRACTOR"
CANONICAL_UNCLASSIFIED = "NO_CLASIFICADO"

#: Every bucket a normalized distractor type can take.
CANONICAL_DISTRACTOR_TYPES: Tuple[str, ...] = (
    CANONICAL_CONCEPTUAL,
    CANONICAL_PROCEDURAL,
    CANONICAL_CALCULO,
    CANONICAL_INTERPRETACION,
    CANONICAL_LECTURA,
    CANONICAL_TRAMPA_HEURISTICA,
    CANONICAL_MEMORIA,
    CANONICAL_ESTRATEGIA,
    CANONICAL_TIEMPO,
    CANONICAL_AZAR,
    CANONICAL_DISTRACTOR,
    CANONICAL_UNCLASSIFIED,
)

#: Bucket used when the item has no recorded cause at all.
CANONICAL_GENERIC = CANONICAL_DISTRACTOR

# --- Explicit mapping table --------------------------------------------------
# Every raw value observed in the seeded banks and the generators. Values that
# are not listed here are reported as CANONICAL_UNCLASSIFIED so that a missing
# mapping is visible instead of silently degrading the analytics.
DISTRACTOR_TYPE_ALIASES: Dict[str, str] = {
    # --- Already canonical ---------------------------------------------------
    "CONCEPTUAL": CANONICAL_CONCEPTUAL,
    "PROCEDIMENTAL": CANONICAL_PROCEDURAL,
    "PROCEDIMIENTO": CANONICAL_PROCEDURAL,
    "CALCULO": CANONICAL_CALCULO,
    "ARITMETICO": CANONICAL_CALCULO,
    "INTERPRETACION": CANONICAL_INTERPRETACION,
    "LECTURA": CANONICAL_LECTURA,
    "TRAMPA_HEURISTICA": CANONICAL_TRAMPA_HEURISTICA,
    "HEURISTICA": CANONICAL_TRAMPA_HEURISTICA,
    "MEMORIA": CANONICAL_MEMORIA,
    "ESTRATEGIA": CANONICAL_ESTRATEGIA,
    "TIEMPO": CANONICAL_TIEMPO,
    "AZAR": CANONICAL_AZAR,
    "DISTRACTOR": CANONICAL_DISTRACTOR,
    "GENERIC_DISTRACTOR": CANONICAL_DISTRACTOR,
    "PROCEDURE_ERROR": CANONICAL_PROCEDURAL,
    "PROCEDURAL_ERROR": CANONICAL_PROCEDURAL,
    "HEURISTIC_TRAP": CANONICAL_TRAMPA_HEURISTICA,
    "HEURISTIC_ERROR": CANONICAL_TRAMPA_HEURISTICA,
    "CONCEPT_ERROR": CANONICAL_CONCEPTUAL,
    "READING_ERROR": CANONICAL_LECTURA,
    "INTERPRETATION_ERROR": CANONICAL_INTERPRETACION,
    "CALCULATION_MISTAKE": CANONICAL_CALCULO,
    "ARITHMETIC_MISTAKE": CANONICAL_CALCULO,
    "SIGN_ERROR": CANONICAL_CALCULO,
    "TIME_PRESSURE": CANONICAL_TIEMPO,
    "RANDOM_GUESS": CANONICAL_AZAR,
    "STRATEGY_ERROR": CANONICAL_ESTRATEGIA,
    "MEMORY_ERROR": CANONICAL_MEMORIA,
    # The banks tag the correct option with "CORRECT"; it is not an error
    # cause, so it falls back to the generic distractor bucket.
    "CORRECT": CANONICAL_DISTRACTOR,
    # --- Arithmetic / algebraic slips --------------------------------------
    "ARITHMETIC_ERROR": CANONICAL_CALCULO,
    "CALCULATION_ERROR": CANONICAL_CALCULO,
    "ALGEBRAIC_ERROR": CANONICAL_CALCULO,
    "INCORRECT_SUBTRACTION": CANONICAL_CALCULO,
    "RAW_PERCENTAGE": CANONICAL_CALCULO,
    "SCALE_MISMATCH": CANONICAL_CALCULO,
    "SIGN_MISTAKE": CANONICAL_CALCULO,
    "SUM_OF_RESISTANCES": CANONICAL_CALCULO,
    # --- Wrong technique / wrong formula ------------------------------------
    "ACCELERATION_ONLY": CANONICAL_PROCEDURAL,
    "COSINE_INVERSION": CANONICAL_PROCEDURAL,
    "EQUIVALENT_RESISTANCE_ONLY": CANONICAL_PROCEDURAL,
    "EXTRANEOUS_ROOT": CANONICAL_PROCEDURAL,
    "EXTRANEOUS_ROOT_NOT_DISCARDED": CANONICAL_PROCEDURAL,
    "FACTORING_ERROR": CANONICAL_PROCEDURAL,
    "FORCE_TIMES_TIME": CANONICAL_PROCEDURAL,
    "INVALID_DOMAIN": CANONICAL_PROCEDURAL,
    "RECIPROCAL_CONFUSION": CANONICAL_PROCEDURAL,
    "RECIPROCAL_ONLY": CANONICAL_PROCEDURAL,
    "SERIES_RESISTANCE_CONFUSION": CANONICAL_PROCEDURAL,
    # --- Wrong principle / wrong fact ---------------------------------------
    "ABSURD_DISTRACTOR": CANONICAL_CONCEPTUAL,
    "ANATOMICAL_ERROR": CANONICAL_CONCEPTUAL,
    "CIVIL_LAW_CONFUSION": CANONICAL_CONCEPTUAL,
    "CONDITIONAL_RESTRICTION": CANONICAL_CONCEPTUAL,
    "CONFUSION_CELLS": CANONICAL_CONCEPTUAL,
    "CONFUSION_SITE": CANONICAL_CONCEPTUAL,
    "CONTRADICTION": CANONICAL_CONCEPTUAL,
    "CONTROLLED_VARIABLE": CANONICAL_CONCEPTUAL,
    "DEPENDENT_VARIABLE": CANONICAL_CONCEPTUAL,
    "DOMINANT_PROBABILITY": CANONICAL_CONCEPTUAL,
    "DOUBLE_DOMINANT": CANONICAL_CONCEPTUAL,
    "ECONOMIC_DOCTRINE": CANONICAL_CONCEPTUAL,
    "EXAGGERATION": CANONICAL_CONCEPTUAL,
    "EXTREME_ABSOLUTE": CANONICAL_CONCEPTUAL,
    "EXTREME_ABSURD": CANONICAL_CONCEPTUAL,
    "EXTREMISMO": CANONICAL_CONCEPTUAL,
    "FALSE_CORRELATION": CANONICAL_CONCEPTUAL,
    "GLOBALIZATION_CONFUSION": CANONICAL_CONCEPTUAL,
    "HETEROZYGOUS_CONFUSION": CANONICAL_CONCEPTUAL,
    "INCORRECT_GENRE": CANONICAL_CONCEPTUAL,
    "INCORRECT_SUBSTRATE": CANONICAL_CONCEPTUAL,
    "MONARCHIC_CONFUSION": CANONICAL_CONCEPTUAL,
    "MONOHYBRID_PROPORTION": CANONICAL_CONCEPTUAL,
    "OPPOSITE_EFFECT": CANONICAL_CONCEPTUAL,
    "OPPOSITE_PRINCIPLE": CANONICAL_CONCEPTUAL,
    "OVERGENERALIZATION": CANONICAL_CONCEPTUAL,
    "POWER_CONFUSION": CANONICAL_CONCEPTUAL,
    "RECESSIVE_SUPPRESSION": CANONICAL_CONCEPTUAL,
    "SINGLE_RECESSIVE": CANONICAL_CONCEPTUAL,
    "TERRITORIAL_CONCEPT": CANONICAL_CONCEPTUAL,
    "TERRITORIAL_ERROR": CANONICAL_CONCEPTUAL,
    "VELOCITY_EQUALS_FORCE": CANONICAL_CONCEPTUAL,
    # --- Misread statement / wrong context ---------------------------------
    "MISPLACED_TOPIC": CANONICAL_INTERPRETACION,
    "OPPOSITE_TONE": CANONICAL_INTERPRETACION,
    # --- Wrong approach / wrong instrument ----------------------------------
    "NON_MONETARY_TOOL": CANONICAL_ESTRATEGIA,
    "WRONG_TRANSMISSION": CANONICAL_ESTRATEGIA,
}

# --- Labels ------------------------------------------------------------------
CANONICAL_LABELS: Dict[str, str] = {
    CANONICAL_CONCEPTUAL: "Confusión Conceptual",
    CANONICAL_PROCEDURAL: "Falla de Procedimiento",
    CANONICAL_CALCULO: "Error de Cálculo",
    CANONICAL_INTERPRETACION: "Confusión de Interpretación",
    CANONICAL_LECTURA: "Error de Lectura",
    CANONICAL_TRAMPA_HEURISTICA: "Trampa Heurística",
    CANONICAL_MEMORIA: "Falla de Memoria",
    CANONICAL_ESTRATEGIA: "Error de Estrategia",
    CANONICAL_TIEMPO: "Falta de Tiempo",
    CANONICAL_AZAR: "Respuesta al Azar",
    CANONICAL_DISTRACTOR: "Distractor Genérico",
    CANONICAL_UNCLASSIFIED: "Causa No Clasificada",
}


def normalize_distractor_type(raw: Optional[str]) -> str:
    """Map a raw ``distractor_type`` to its canonical bucket.

    - ``None`` / empty -> ``DISTRACTOR`` (no specific cause recorded).
    - A canonical value -> itself.
    - A known alias -> its canonical bucket.
    - Anything else -> ``NO_CLASIFICADO`` (the documented catch-all).
    """
    if raw is None:
        return CANONICAL_GENERIC
    key = str(raw).strip().upper()
    if not key:
        return CANONICAL_GENERIC
    if key in CANONICAL_DISTRACTOR_TYPES:
        return key
    return DISTRACTOR_TYPE_ALIASES.get(key, CANONICAL_UNCLASSIFIED)


def canonical_label(canonical: str) -> str:
    """Human readable label for a canonical bucket."""
    return CANONICAL_LABELS.get(canonical, CANONICAL_LABELS[CANONICAL_UNCLASSIFIED])
