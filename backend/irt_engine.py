# -*- coding: utf-8 -*-
"""
Módulo de compatibilidad para el motor psicométrico 3PL IRT.
Reexporta todas las definiciones y funciones desde `services.paes.irt_engine`.
"""
from services.paes.irt_engine import (
    D_SCALING,
    AbilityEstimate,
    ItemParameters,
    calculate_test_information,
    calibrate_mmle_em,
    estimate_theta_eap,
    estimate_theta_hybrid,
    estimate_theta_mle,
    item_information,
    prob_3pl,
    select_next_adaptive_item,
    standard_error,
    theta_to_demre_score,
)

__all__ = [
    "D_SCALING",
    "AbilityEstimate",
    "ItemParameters",
    "calculate_test_information",
    "calibrate_mmle_em",
    "estimate_theta_eap",
    "estimate_theta_hybrid",
    "estimate_theta_mle",
    "item_information",
    "prob_3pl",
    "select_next_adaptive_item",
    "standard_error",
    "theta_to_demre_score",
]
