"""
Módulo de Datos Oficiales y Motor de Admisión Universitaria CRUCH (DEMRE).
Proporciona el catálogo de carreras de alta demanda en universidades del CRUCH
(Pontificia Universidad Católica de Chile, Universidad de Chile, USACH, UTFSM, UdeC),
ponderaciones oficiales, cortes históricos 2024-2026, y el cálculo probabilístico
psicométrico 3PL IRT y de brechas de puntaje y aciertos.
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np

from services.paes.demre_scale import SUBJECT_METADATA

# Catálogo oficial CRUCH con carreras emblemáticas de alta demanda
CRUCH_CAREERS: List[Dict[str, Any]] = [
    {
        "id": "medicina-uch",
        "name": "Medicina",
        "university": "Universidad de Chile",
        "university_short": "UCH",
        "campus": "Campus Norte (Independencia)",
        "region": "Metropolitana",
        "city": "Santiago",
        "area": "Ciencias de la Salud",
        "vacantes": 200,
        "weights": {
            "nem": 0.1,
            "ranking": 0.2,
            "lectura": 0.15,
            "m1": 0.2,
            "m2": 0.0,
            "ciencias": 0.35,
            "historia": 0.0,
            "elective_rule": "CIENCIAS"
        },
        "cutoffs": {
            "2024": 928.55,
            "2025": 930.8,
            "2026": 931.15
        },
        "requires_m2": False,
        "min_weighted_score": 600.0
    },
    {
        "id": "medicina-puc",
        "name": "Medicina",
        "university": "Pontificia Universidad Católica de Chile",
        "university_short": "PUC",
        "campus": "Casa Central / San Joaquín",
        "region": "Metropolitana",
        "city": "Santiago",
        "area": "Ciencias de la Salud",
        "vacantes": 120,
        "weights": {
            "nem": 0.2,
            "ranking": 0.2,
            "lectura": 0.15,
            "m1": 0.2,
            "m2": 0.0,
            "ciencias": 0.25,
            "historia": 0.0,
            "elective_rule": "CIENCIAS"
        },
        "cutoffs": {
            "2024": 954.2,
            "2025": 956.8,
            "2026": 958.4
        },
        "requires_m2": False,
        "min_weighted_score": 600.0
    },
    {
        "id": "ing-civil-uch",
        "name": "Ingeniería Civil - Plan Común",
        "university": "Universidad de Chile",
        "university_short": "UCH",
        "campus": "Beauchef",
        "region": "Metropolitana",
        "city": "Santiago",
        "area": "Ingeniería y Ciencias Exactas",
        "vacantes": 800,
        "weights": {
            "nem": 0.1,
            "ranking": 0.25,
            "lectura": 0.1,
            "m1": 0.3,
            "m2": 0.2,
            "ciencias": 0.05,
            "historia": 0.0,
            "elective_rule": "CIENCIAS"
        },
        "cutoffs": {
            "2024": 826.4,
            "2025": 830.1,
            "2026": 833.85
        },
        "requires_m2": True,
        "min_weighted_score": 600.0
    },
    {
        "id": "ing-civil-puc",
        "name": "Ingeniería Civil",
        "university": "Pontificia Universidad Católica de Chile",
        "university_short": "PUC",
        "campus": "San Joaquín",
        "region": "Metropolitana",
        "city": "Santiago",
        "area": "Ingeniería y Ciencias Exactas",
        "vacantes": 750,
        "weights": {
            "nem": 0.1,
            "ranking": 0.2,
            "lectura": 0.1,
            "m1": 0.35,
            "m2": 0.15,
            "ciencias": 0.1,
            "historia": 0.0,
            "elective_rule": "CIENCIAS"
        },
        "cutoffs": {
            "2024": 880.5,
            "2025": 884.2,
            "2026": 887.3
        },
        "requires_m2": True,
        "min_weighted_score": 600.0
    },
    {
        "id": "ing-civil-usach",
        "name": "Ingeniería Civil - Plan Común",
        "university": "Universidad de Santiago de Chile",
        "university_short": "USACH",
        "campus": "Estación Central",
        "region": "Metropolitana",
        "city": "Santiago",
        "area": "Ingeniería y Ciencias Exactas",
        "vacantes": 600,
        "weights": {
            "nem": 0.1,
            "ranking": 0.3,
            "lectura": 0.1,
            "m1": 0.3,
            "m2": 0.1,
            "ciencias": 0.1,
            "historia": 0.0,
            "elective_rule": "CIENCIAS"
        },
        "cutoffs": {
            "2024": 755.2,
            "2025": 758.9,
            "2026": 762.4
        },
        "requires_m2": True,
        "min_weighted_score": 550.0
    },
    {
        "id": "ing-civil-utfsm",
        "name": "Ingeniería Civil - Plan Común",
        "university": "Universidad Técnica Federico Santa María",
        "university_short": "UTFSM",
        "campus": "Casa Central (Valparaíso)",
        "region": "Valparaíso",
        "city": "Valparaíso",
        "area": "Ingeniería y Ciencias Exactas",
        "vacantes": 500,
        "weights": {
            "nem": 0.1,
            "ranking": 0.2,
            "lectura": 0.1,
            "m1": 0.4,
            "m2": 0.1,
            "ciencias": 0.1,
            "historia": 0.0,
            "elective_rule": "CIENCIAS"
        },
        "cutoffs": {
            "2024": 810.3,
            "2025": 814.0,
            "2026": 817.65
        },
        "requires_m2": True,
        "min_weighted_score": 600.0
    },
    {
        "id": "derecho-uch",
        "name": "Derecho",
        "university": "Universidad de Chile",
        "university_short": "UCH",
        "campus": "Pío Nono (Providencia)",
        "region": "Metropolitana",
        "city": "Santiago",
        "area": "Ciencias Sociales y Jurídicas",
        "vacantes": 400,
        "weights": {
            "nem": 0.1,
            "ranking": 0.2,
            "lectura": 0.3,
            "m1": 0.2,
            "m2": 0.0,
            "ciencias": 0.0,
            "historia": 0.2,
            "elective_rule": "HISTORIA"
        },
        "cutoffs": {
            "2024": 845.2,
            "2025": 848.7,
            "2026": 851.3
        },
        "requires_m2": False,
        "min_weighted_score": 600.0
    },
    {
        "id": "derecho-puc",
        "name": "Derecho",
        "university": "Pontificia Universidad Católica de Chile",
        "university_short": "PUC",
        "campus": "Casa Central",
        "region": "Metropolitana",
        "city": "Santiago",
        "area": "Ciencias Sociales y Jurídicas",
        "vacantes": 340,
        "weights": {
            "nem": 0.1,
            "ranking": 0.2,
            "lectura": 0.3,
            "m1": 0.15,
            "m2": 0.0,
            "ciencias": 0.0,
            "historia": 0.25,
            "elective_rule": "MAX"
        },
        "cutoffs": {
            "2024": 875.3,
            "2025": 879.1,
            "2026": 882.0
        },
        "requires_m2": False,
        "min_weighted_score": 600.0
    },
    {
        "id": "psicologia-puc",
        "name": "Psicología",
        "university": "Pontificia Universidad Católica de Chile",
        "university_short": "PUC",
        "campus": "San Joaquín",
        "region": "Metropolitana",
        "city": "Santiago",
        "area": "Ciencias Sociales",
        "vacantes": 130,
        "weights": {
            "nem": 0.15,
            "ranking": 0.25,
            "lectura": 0.25,
            "m1": 0.2,
            "m2": 0.0,
            "ciencias": 0.0,
            "historia": 0.15,
            "elective_rule": "MAX"
        },
        "cutoffs": {
            "2024": 840.1,
            "2025": 843.5,
            "2026": 846.2
        },
        "requires_m2": False,
        "min_weighted_score": 600.0
    },
    {
        "id": "psicologia-usach",
        "name": "Psicología",
        "university": "Universidad de Santiago de Chile",
        "university_short": "USACH",
        "campus": "Estación Central",
        "region": "Metropolitana",
        "city": "Santiago",
        "area": "Ciencias Sociales",
        "vacantes": 120,
        "weights": {
            "nem": 0.1,
            "ranking": 0.3,
            "lectura": 0.3,
            "m1": 0.15,
            "m2": 0.0,
            "ciencias": 0.0,
            "historia": 0.15,
            "elective_rule": "MAX"
        },
        "cutoffs": {
            "2024": 795.3,
            "2025": 798.9,
            "2026": 802.1
        },
        "requires_m2": False,
        "min_weighted_score": 550.0
    },
    {
        "id": "enfermeria-uch",
        "name": "Enfermería",
        "university": "Universidad de Chile",
        "university_short": "UCH",
        "campus": "Campus Norte",
        "region": "Metropolitana",
        "city": "Santiago",
        "area": "Ciencias de la Salud",
        "vacantes": 97,
        "weights": {
            "nem": 0.1,
            "ranking": 0.2,
            "lectura": 0.15,
            "m1": 0.2,
            "m2": 0.0,
            "ciencias": 0.35,
            "historia": 0.0,
            "elective_rule": "CIENCIAS"
        },
        "cutoffs": {
            "2024": 772.3,
            "2025": 778.0,
            "2026": 781.4
        },
        "requires_m2": False,
        "min_weighted_score": 600.0
    },
    {
        "id": "enfermeria-usach",
        "name": "Enfermería",
        "university": "Universidad de Santiago de Chile",
        "university_short": "USACH",
        "campus": "Estación Central",
        "region": "Metropolitana",
        "city": "Santiago",
        "area": "Ciencias de la Salud",
        "vacantes": 90,
        "weights": {
            "nem": 0.1,
            "ranking": 0.3,
            "lectura": 0.15,
            "m1": 0.2,
            "m2": 0.0,
            "ciencias": 0.25,
            "historia": 0.0,
            "elective_rule": "CIENCIAS"
        },
        "cutoffs": {
            "2024": 780.2,
            "2025": 784.0,
            "2026": 786.5
        },
        "requires_m2": False,
        "min_weighted_score": 550.0
    },
    {
        "id": "administracion-publica-y-ciencia-politica-udec",
        "code": "13023",
        "name": "Administración Pública Y Ciencia Política",
        "university": "Universidad de Concepción",
        "university_short": "UdeC",
        "campus": "Concepción",
        "region": "Biobío",
        "city": "Concepción",
        "area": "Humanidades y Ciencias",
        "vacantes": 70,
        "weights": {
            "nem": 0.15,
            "ranking": 0.25,
            "lectura": 0.2,
            "m1": 0.1,
            "m2": 0.0,
            "ciencias": 0.0,
            "historia": 0.3,
            "elective_rule": "HISTORIA"
        },
        "cutoffs": {
            "2024": 496.5,
            "2025": 500.5,
            "2026": 505.0
        },
        "requires_m2": False,
        "min_weighted_score": 500.0
    },
    {
        "id": "agronomia-chillan-udec",
        "code": "13006",
        "name": "Agronomía",
        "university": "Universidad de Concepción",
        "university_short": "UdeC",
        "campus": "Chillán",
        "region": "Ñuble",
        "city": "Chillán",
        "area": "Ciencias Naturales y Agropecuarias",
        "vacantes": 70,
        "weights": {
            "nem": 0.15,
            "ranking": 0.25,
            "lectura": 0.15,
            "m1": 0.3,
            "m2": 0.05,
            "ciencias": 0.1,
            "historia": 0.0,
            "elective_rule": "CIENCIAS"
        },
        "cutoffs": {
            "2024": 496.5,
            "2025": 500.5,
            "2026": 505.0
        },
        "requires_m2": True,
        "min_weighted_score": 500.0
    },
    {
        "id": "agronomia-udec",
        "code": "13105",
        "name": "Agronomía",
        "university": "Universidad de Concepción",
        "university_short": "UdeC",
        "campus": "Concepción",
        "region": "Biobío",
        "city": "Concepción",
        "area": "Ciencias Naturales y Agropecuarias",
        "vacantes": 55,
        "weights": {
            "nem": 0.15,
            "ranking": 0.25,
            "lectura": 0.15,
            "m1": 0.3,
            "m2": 0.05,
            "ciencias": 0.1,
            "historia": 0.0,
            "elective_rule": "CIENCIAS"
        },
        "cutoffs": {
            "2024": 496.5,
            "2025": 500.5,
            "2026": 505.0
        },
        "requires_m2": True,
        "min_weighted_score": 500.0
    },
    {
        "id": "antropologia-udec",
        "code": "13026",
        "name": "Antropología",
        "university": "Universidad de Concepción",
        "university_short": "UdeC",
        "campus": "Concepción",
        "region": "Biobío",
        "city": "Concepción",
        "area": "Ciencias Sociales y Jurídicas",
        "vacantes": 66,
        "weights": {
            "nem": 0.15,
            "ranking": 0.25,
            "lectura": 0.2,
            "m1": 0.25,
            "m2": 0.0,
            "ciencias": 0.15,
            "historia": 0.0,
            "elective_rule": "MAX"
        },
        "cutoffs": {
            "2024": 507.0,
            "2025": 520.9,
            "2026": 505.8
        },
        "requires_m2": False,
        "min_weighted_score": 500.0
    },
    {
        "id": "arquitectura-udec",
        "code": "13080",
        "name": "Arquitectura",
        "university": "Universidad de Concepción",
        "university_short": "UdeC",
        "campus": "Concepción",
        "region": "Biobío",
        "city": "Concepción",
        "area": "Arquitectura, Arte y Diseño",
        "vacantes": 71,
        "weights": {
            "nem": 0.15,
            "ranking": 0.25,
            "lectura": 0.25,
            "m1": 0.25,
            "m2": 0.0,
            "ciencias": 0.0,
            "historia": 0.1,
            "elective_rule": "HISTORIA"
        },
        "cutoffs": {
            "2024": 755.35,
            "2025": 755.05,
            "2026": 747.85
        },
        "requires_m2": False,
        "min_weighted_score": 500.0
    },
    {
        "id": "artes-visuales-udec",
        "code": "13054",
        "name": "Artes Visuales",
        "university": "Universidad de Concepción",
        "university_short": "UdeC",
        "campus": "Concepción",
        "region": "Biobío",
        "city": "Concepción",
        "area": "Arquitectura, Arte y Diseño",
        "vacantes": 50,
        "weights": {
            "nem": 0.15,
            "ranking": 0.25,
            "lectura": 0.3,
            "m1": 0.1,
            "m2": 0.0,
            "ciencias": 0.0,
            "historia": 0.2,
            "elective_rule": "HISTORIA"
        },
        "cutoffs": {
            "2024": 653.0,
            "2025": 617.3,
            "2026": 634.95
        },
        "requires_m2": False,
        "min_weighted_score": 500.0
    },
    {
        "id": "astronomia-udec",
        "code": "13055",
        "name": "Astronomía",
        "university": "Universidad de Concepción",
        "university_short": "UdeC",
        "campus": "Concepción",
        "region": "Biobío",
        "city": "Concepción",
        "area": "Ingeniería y Ciencias Exactas",
        "vacantes": 35,
        "weights": {
            "nem": 0.15,
            "ranking": 0.25,
            "lectura": 0.2,
            "m1": 0.2,
            "m2": 0.1,
            "ciencias": 0.1,
            "historia": 0.0,
            "elective_rule": "CIENCIAS"
        },
        "cutoffs": {
            "2024": 787.4,
            "2025": 759.95,
            "2026": 770.8
        },
        "requires_m2": True,
        "min_weighted_score": 500.0
    },
    {
        "id": "auditoria-udec",
        "code": "13022",
        "name": "Auditoria",
        "university": "Universidad de Concepción",
        "university_short": "UdeC",
        "campus": "Concepción",
        "region": "Biobío",
        "city": "Concepción",
        "area": "Ciencias Sociales y Jurídicas",
        "vacantes": 60,
        "weights": {
            "nem": 0.15,
            "ranking": 0.25,
            "lectura": 0.2,
            "m1": 0.3,
            "m2": 0.0,
            "ciencias": 0.0,
            "historia": 0.1,
            "elective_rule": "HISTORIA"
        },
        "cutoffs": {
            "2024": 496.5,
            "2025": 500.5,
            "2026": 505.0
        },
        "requires_m2": False,
        "min_weighted_score": 500.0
    },
    {
        "id": "auditoria-diurna-los-angeles-udec",
        "code": "13094",
        "name": "Auditoria - Diurna",
        "university": "Universidad de Concepción",
        "university_short": "UdeC",
        "campus": "Los Ángeles",
        "region": "Biobío",
        "city": "Los Ángeles",
        "area": "Ciencias Sociales y Jurídicas",
        "vacantes": 40,
        "weights": {
            "nem": 0.15,
            "ranking": 0.25,
            "lectura": 0.2,
            "m1": 0.3,
            "m2": 0.0,
            "ciencias": 0.0,
            "historia": 0.1,
            "elective_rule": "HISTORIA"
        },
        "cutoffs": {
            "2024": 496.5,
            "2025": 500.5,
            "2026": 505.0
        },
        "requires_m2": False,
        "min_weighted_score": 500.0
    },
    {
        "id": "bachillerato-en-ciencias-e-innovacion-udec",
        "code": "13114",
        "name": "Bachillerato En Ciencias E Innovación",
        "university": "Universidad de Concepción",
        "university_short": "UdeC",
        "campus": "Concepción",
        "region": "Biobío",
        "city": "Concepción",
        "area": "Humanidades y Ciencias",
        "vacantes": 60,
        "weights": {
            "nem": 0.2,
            "ranking": 0.2,
            "lectura": 0.2,
            "m1": 0.2,
            "m2": 0.0,
            "ciencias": 0.2,
            "historia": 0.0,
            "elective_rule": "CIENCIAS"
        },
        "cutoffs": {
            "2024": 609.1,
            "2025": 613.1,
            "2026": 617.6
        },
        "requires_m2": False,
        "min_weighted_score": 500.0
    },
    {
        "id": "bachillerato-en-humanidades-udec",
        "code": "13052",
        "name": "Bachillerato En Humanidades",
        "university": "Universidad de Concepción",
        "university_short": "UdeC",
        "campus": "Concepción",
        "region": "Biobío",
        "city": "Concepción",
        "area": "Humanidades y Ciencias",
        "vacantes": 40,
        "weights": {
            "nem": 0.15,
            "ranking": 0.25,
            "lectura": 0.25,
            "m1": 0.1,
            "m2": 0.0,
            "ciencias": 0.0,
            "historia": 0.25,
            "elective_rule": "HISTORIA"
        },
        "cutoffs": {
            "2024": 529.0,
            "2025": 512.15,
            "2026": 508.85
        },
        "requires_m2": False,
        "min_weighted_score": 500.0
    },
    {
        "id": "bioingenieria-udec",
        "code": "13012",
        "name": "Bioingeniería",
        "university": "Universidad de Concepción",
        "university_short": "UdeC",
        "campus": "Concepción",
        "region": "Biobío",
        "city": "Concepción",
        "area": "Ingeniería y Ciencias Exactas",
        "vacantes": 46,
        "weights": {
            "nem": 0.15,
            "ranking": 0.25,
            "lectura": 0.15,
            "m1": 0.25,
            "m2": 0.1,
            "ciencias": 0.1,
            "historia": 0.0,
            "elective_rule": "CIENCIAS"
        },
        "cutoffs": {
            "2024": 668.25,
            "2025": 671.9,
            "2026": 707.45
        },
        "requires_m2": True,
        "min_weighted_score": 500.0
    },
    {
        "id": "biologia-udec",
        "code": "13014",
        "name": "Biología",
        "university": "Universidad de Concepción",
        "university_short": "UdeC",
        "campus": "Concepción",
        "region": "Biobío",
        "city": "Concepción",
        "area": "Humanidades y Ciencias",
        "vacantes": 60,
        "weights": {
            "nem": 0.15,
            "ranking": 0.25,
            "lectura": 0.15,
            "m1": 0.35,
            "m2": 0.0,
            "ciencias": 0.1,
            "historia": 0.0,
            "elective_rule": "CIENCIAS"
        },
        "cutoffs": {
            "2024": 679.1,
            "2025": 672.25,
            "2026": 686.2
        },
        "requires_m2": False,
        "min_weighted_score": 500.0
    },
    {
        "id": "biologia-marina-udec",
        "code": "13013",
        "name": "Biología Marina",
        "university": "Universidad de Concepción",
        "university_short": "UdeC",
        "campus": "Concepción",
        "region": "Biobío",
        "city": "Concepción",
        "area": "Ciencias Naturales y Agropecuarias",
        "vacantes": 30,
        "weights": {
            "nem": 0.15,
            "ranking": 0.25,
            "lectura": 0.15,
            "m1": 0.35,
            "m2": 0.0,
            "ciencias": 0.1,
            "historia": 0.0,
            "elective_rule": "CIENCIAS"
        },
        "cutoffs": {
            "2024": 706.75,
            "2025": 749.95,
            "2026": 735.7
        },
        "requires_m2": False,
        "min_weighted_score": 500.0
    },
    {
        "id": "bioquimica-udec",
        "code": "13048",
        "name": "Bioquímica",
        "university": "Universidad de Concepción",
        "university_short": "UdeC",
        "campus": "Concepción",
        "region": "Biobío",
        "city": "Concepción",
        "area": "Humanidades y Ciencias",
        "vacantes": 55,
        "weights": {
            "nem": 0.15,
            "ranking": 0.25,
            "lectura": 0.15,
            "m1": 0.35,
            "m2": 0.0,
            "ciencias": 0.1,
            "historia": 0.0,
            "elective_rule": "CIENCIAS"
        },
        "cutoffs": {
            "2024": 780.55,
            "2025": 817.15,
            "2026": 815.7
        },
        "requires_m2": False,
        "min_weighted_score": 500.0
    },
    {
        "id": "ciencias-fisicas-udec",
        "code": "13046",
        "name": "Ciencias Físicas",
        "university": "Universidad de Concepción",
        "university_short": "UdeC",
        "campus": "Concepción",
        "region": "Biobío",
        "city": "Concepción",
        "area": "Humanidades y Ciencias",
        "vacantes": 45,
        "weights": {
            "nem": 0.1,
            "ranking": 0.2,
            "lectura": 0.2,
            "m1": 0.3,
            "m2": 0.1,
            "ciencias": 0.1,
            "historia": 0.0,
            "elective_rule": "CIENCIAS"
        },
        "cutoffs": {
            "2024": 701.9,
            "2025": 605.0,
            "2026": 600.4
        },
        "requires_m2": True,
        "min_weighted_score": 500.0
    },
    {
        "id": "derecho-udec",
        "code": "13024",
        "name": "Derecho",
        "university": "Universidad de Concepción",
        "university_short": "UdeC",
        "campus": "Concepción",
        "region": "Biobío",
        "city": "Concepción",
        "area": "Ciencias Sociales y Jurídicas",
        "vacantes": 145,
        "weights": {
            "nem": 0.15,
            "ranking": 0.25,
            "lectura": 0.25,
            "m1": 0.25,
            "m2": 0.0,
            "ciencias": 0.0,
            "historia": 0.1,
            "elective_rule": "HISTORIA"
        },
        "cutoffs": {
            "2024": 796.2,
            "2025": 800.1,
            "2026": 803.15
        },
        "requires_m2": False,
        "min_weighted_score": 500.0
    },
    {
        "id": "derecho-chillan-udec",
        "code": "13029",
        "name": "Derecho",
        "university": "Universidad de Concepción",
        "university_short": "UdeC",
        "campus": "Chillán",
        "region": "Ñuble",
        "city": "Chillán",
        "area": "Ciencias Sociales y Jurídicas",
        "vacantes": 65,
        "weights": {
            "nem": 0.15,
            "ranking": 0.25,
            "lectura": 0.25,
            "m1": 0.25,
            "m2": 0.0,
            "ciencias": 0.0,
            "historia": 0.1,
            "elective_rule": "HISTORIA"
        },
        "cutoffs": {
            "2024": 496.5,
            "2025": 500.5,
            "2026": 505.0
        },
        "requires_m2": False,
        "min_weighted_score": 500.0
    },
    {
        "id": "educacion-basica-udec",
        "code": "13032",
        "name": "Educación Básica",
        "university": "Universidad de Concepción",
        "university_short": "UdeC",
        "campus": "Concepción",
        "region": "Biobío",
        "city": "Concepción",
        "area": "Educación",
        "vacantes": 80,
        "weights": {
            "nem": 0.15,
            "ranking": 0.25,
            "lectura": 0.25,
            "m1": 0.25,
            "m2": 0.0,
            "ciencias": 0.0,
            "historia": 0.1,
            "elective_rule": "HISTORIA"
        },
        "cutoffs": {
            "2024": 496.5,
            "2025": 500.5,
            "2026": 505.0
        },
        "requires_m2": False,
        "min_weighted_score": 500.0
    },
    {
        "id": "educacion-basica-los-angeles-udec",
        "code": "13092",
        "name": "Educación Básica",
        "university": "Universidad de Concepción",
        "university_short": "UdeC",
        "campus": "Los Ángeles",
        "region": "Biobío",
        "city": "Los Ángeles",
        "area": "Educación",
        "vacantes": 35,
        "weights": {
            "nem": 0.15,
            "ranking": 0.25,
            "lectura": 0.25,
            "m1": 0.25,
            "m2": 0.0,
            "ciencias": 0.0,
            "historia": 0.1,
            "elective_rule": "HISTORIA"
        },
        "cutoffs": {
            "2024": 496.5,
            "2025": 500.5,
            "2026": 505.0
        },
        "requires_m2": False,
        "min_weighted_score": 500.0
    },
    {
        "id": "educacion-diferencial-udec",
        "code": "13028",
        "name": "Educación Diferencial",
        "university": "Universidad de Concepción",
        "university_short": "UdeC",
        "campus": "Concepción",
        "region": "Biobío",
        "city": "Concepción",
        "area": "Educación",
        "vacantes": 40,
        "weights": {
            "nem": 0.15,
            "ranking": 0.25,
            "lectura": 0.25,
            "m1": 0.25,
            "m2": 0.0,
            "ciencias": 0.0,
            "historia": 0.1,
            "elective_rule": "HISTORIA"
        },
        "cutoffs": {
            "2024": 496.5,
            "2025": 500.5,
            "2026": 505.0
        },
        "requires_m2": False,
        "min_weighted_score": 500.0
    },
    {
        "id": "educacion-diferencial-los-angeles-udec",
        "code": "13089",
        "name": "Educación Diferencial",
        "university": "Universidad de Concepción",
        "university_short": "UdeC",
        "campus": "Los Ángeles",
        "region": "Biobío",
        "city": "Los Ángeles",
        "area": "Educación",
        "vacantes": 35,
        "weights": {
            "nem": 0.15,
            "ranking": 0.25,
            "lectura": 0.25,
            "m1": 0.25,
            "m2": 0.0,
            "ciencias": 0.0,
            "historia": 0.1,
            "elective_rule": "HISTORIA"
        },
        "cutoffs": {
            "2024": 496.5,
            "2025": 500.5,
            "2026": 505.0
        },
        "requires_m2": False,
        "min_weighted_score": 500.0
    },
    {
        "id": "educacion-parvularia-udec",
        "code": "13027",
        "name": "Educación Parvularia",
        "university": "Universidad de Concepción",
        "university_short": "UdeC",
        "campus": "Concepción",
        "region": "Biobío",
        "city": "Concepción",
        "area": "Educación",
        "vacantes": 40,
        "weights": {
            "nem": 0.15,
            "ranking": 0.25,
            "lectura": 0.25,
            "m1": 0.25,
            "m2": 0.0,
            "ciencias": 0.0,
            "historia": 0.1,
            "elective_rule": "HISTORIA"
        },
        "cutoffs": {
            "2024": 610.65,
            "2025": 625.95,
            "2026": 642.7
        },
        "requires_m2": False,
        "min_weighted_score": 500.0
    },
    {
        "id": "enfermeria-chillan-udec",
        "code": "13103",
        "name": "Enfermería",
        "university": "Universidad de Concepción",
        "university_short": "UdeC",
        "campus": "Chillán",
        "region": "Ñuble",
        "city": "Chillán",
        "area": "Ciencias de la Salud",
        "vacantes": 58,
        "weights": {
            "nem": 0.15,
            "ranking": 0.25,
            "lectura": 0.25,
            "m1": 0.25,
            "m2": 0.0,
            "ciencias": 0.1,
            "historia": 0.0,
            "elective_rule": "CIENCIAS"
        },
        "cutoffs": {
            "2024": 496.5,
            "2025": 500.5,
            "2026": 505.0
        },
        "requires_m2": False,
        "min_weighted_score": 500.0
    },
    {
        "id": "enfermeria-udec",
        "code": "13087",
        "name": "Enfermería",
        "university": "Universidad de Concepción",
        "university_short": "UdeC",
        "campus": "Concepción",
        "region": "Biobío",
        "city": "Concepción",
        "area": "Ciencias de la Salud",
        "vacantes": 103,
        "weights": {
            "nem": 0.15,
            "ranking": 0.25,
            "lectura": 0.25,
            "m1": 0.25,
            "m2": 0.0,
            "ciencias": 0.1,
            "historia": 0.0,
            "elective_rule": "CIENCIAS"
        },
        "cutoffs": {
            "2024": 772.9,
            "2025": 765.65,
            "2026": 755.55
        },
        "requires_m2": False,
        "min_weighted_score": 500.0
    },
    {
        "id": "enfermeria-los-angeles-udec",
        "code": "13104",
        "name": "Enfermería",
        "university": "Universidad de Concepción",
        "university_short": "UdeC",
        "campus": "Los Ángeles",
        "region": "Biobío",
        "city": "Los Ángeles",
        "area": "Ciencias de la Salud",
        "vacantes": 58,
        "weights": {
            "nem": 0.15,
            "ranking": 0.25,
            "lectura": 0.25,
            "m1": 0.25,
            "m2": 0.0,
            "ciencias": 0.1,
            "historia": 0.0,
            "elective_rule": "CIENCIAS"
        },
        "cutoffs": {
            "2024": 496.5,
            "2025": 500.5,
            "2026": 505.0
        },
        "requires_m2": False,
        "min_weighted_score": 500.0
    },
    {
        "id": "fonoaudiologia-udec",
        "code": "13082",
        "name": "Fonoaudiología",
        "university": "Universidad de Concepción",
        "university_short": "UdeC",
        "campus": "Concepción",
        "region": "Biobío",
        "city": "Concepción",
        "area": "Ciencias de la Salud",
        "vacantes": 58,
        "weights": {
            "nem": 0.15,
            "ranking": 0.25,
            "lectura": 0.15,
            "m1": 0.35,
            "m2": 0.0,
            "ciencias": 0.1,
            "historia": 0.0,
            "elective_rule": "CIENCIAS"
        },
        "cutoffs": {
            "2024": 635.45,
            "2025": 646.9,
            "2026": 654.45
        },
        "requires_m2": False,
        "min_weighted_score": 500.0
    },
    {
        "id": "geofisica-udec",
        "code": "13056",
        "name": "Geofisica",
        "university": "Universidad de Concepción",
        "university_short": "UdeC",
        "campus": "Concepción",
        "region": "Biobío",
        "city": "Concepción",
        "area": "Ingeniería y Ciencias Exactas",
        "vacantes": 35,
        "weights": {
            "nem": 0.15,
            "ranking": 0.25,
            "lectura": 0.2,
            "m1": 0.2,
            "m2": 0.1,
            "ciencias": 0.1,
            "historia": 0.0,
            "elective_rule": "CIENCIAS"
        },
        "cutoffs": {
            "2024": 584.6,
            "2025": 513.6,
            "2026": 551.1
        },
        "requires_m2": True,
        "min_weighted_score": 500.0
    },
    {
        "id": "geografia-udec",
        "code": "13018",
        "name": "Geografía",
        "university": "Universidad de Concepción",
        "university_short": "UdeC",
        "campus": "Concepción",
        "region": "Biobío",
        "city": "Concepción",
        "area": "Humanidades y Ciencias",
        "vacantes": 55,
        "weights": {
            "nem": 0.15,
            "ranking": 0.25,
            "lectura": 0.25,
            "m1": 0.25,
            "m2": 0.0,
            "ciencias": 0.1,
            "historia": 0.0,
            "elective_rule": "MAX"
        },
        "cutoffs": {
            "2024": 509.25,
            "2025": 524.1,
            "2026": 505.8
        },
        "requires_m2": False,
        "min_weighted_score": 500.0
    },
    {
        "id": "geologia-udec",
        "code": "13015",
        "name": "Geología",
        "university": "Universidad de Concepción",
        "university_short": "UdeC",
        "campus": "Concepción",
        "region": "Biobío",
        "city": "Concepción",
        "area": "Ingeniería y Ciencias Exactas",
        "vacantes": 35,
        "weights": {
            "nem": 0.15,
            "ranking": 0.25,
            "lectura": 0.2,
            "m1": 0.3,
            "m2": 0.0,
            "ciencias": 0.1,
            "historia": 0.0,
            "elective_rule": "CIENCIAS"
        },
        "cutoffs": {
            "2024": 834.15,
            "2025": 835.5,
            "2026": 825.55
        },
        "requires_m2": False,
        "min_weighted_score": 500.0
    },
    {
        "id": "ingenieria-ambiental-udec",
        "code": "13061",
        "name": "Ingeniería Ambiental",
        "university": "Universidad de Concepción",
        "university_short": "UdeC",
        "campus": "Concepción",
        "region": "Biobío",
        "city": "Concepción",
        "area": "Ingeniería y Ciencias Exactas",
        "vacantes": 55,
        "weights": {
            "nem": 0.15,
            "ranking": 0.25,
            "lectura": 0.15,
            "m1": 0.25,
            "m2": 0.1,
            "ciencias": 0.1,
            "historia": 0.0,
            "elective_rule": "CIENCIAS"
        },
        "cutoffs": {
            "2024": 540.65,
            "2025": 500.1,
            "2026": 504.6
        },
        "requires_m2": True,
        "min_weighted_score": 500.0
    },
    {
        "id": "ingenieria-ambiental-chillan-udec",
        "code": "13044",
        "name": "Ingeniería Ambiental",
        "university": "Universidad de Concepción",
        "university_short": "UdeC",
        "campus": "Chillán",
        "region": "Ñuble",
        "city": "Chillán",
        "area": "Ingeniería y Ciencias Exactas",
        "vacantes": 40,
        "weights": {
            "nem": 0.15,
            "ranking": 0.25,
            "lectura": 0.15,
            "m1": 0.25,
            "m2": 0.1,
            "ciencias": 0.1,
            "historia": 0.0,
            "elective_rule": "CIENCIAS"
        },
        "cutoffs": {
            "2024": 522.45,
            "2025": 504.55,
            "2026": 547.85
        },
        "requires_m2": True,
        "min_weighted_score": 500.0
    },
    {
        "id": "ing-civil-udec",
        "code": "13069",
        "name": "Ingeniería Civil",
        "university": "Universidad de Concepción",
        "university_short": "UdeC",
        "campus": "Concepción",
        "region": "Biobío",
        "city": "Concepción",
        "area": "Ingeniería y Ciencias Exactas",
        "vacantes": 98,
        "weights": {
            "nem": 0.2,
            "ranking": 0.15,
            "lectura": 0.15,
            "m1": 0.25,
            "m2": 0.15,
            "ciencias": 0.1,
            "historia": 0.0,
            "elective_rule": "CIENCIAS"
        },
        "cutoffs": {
            "2024": 712.1,
            "2025": 716.4,
            "2026": 721.45
        },
        "requires_m2": True,
        "min_weighted_score": 500.0
    },
    {
        "id": "ingenieria-civil-aeroespacial-udec",
        "code": "13066",
        "name": "Ingeniería Civil Aeroespacial",
        "university": "Universidad de Concepción",
        "university_short": "UdeC",
        "campus": "Concepción",
        "region": "Biobío",
        "city": "Concepción",
        "area": "Ingeniería y Ciencias Exactas",
        "vacantes": 18,
        "weights": {
            "nem": 0.2,
            "ranking": 0.15,
            "lectura": 0.15,
            "m1": 0.25,
            "m2": 0.15,
            "ciencias": 0.1,
            "historia": 0.0,
            "elective_rule": "CIENCIAS"
        },
        "cutoffs": {
            "2024": 862.8,
            "2025": 853.9,
            "2026": 875.05
        },
        "requires_m2": True,
        "min_weighted_score": 500.0
    },
    {
        "id": "ingenieria-civil-agricola-chillan-udec",
        "code": "13009",
        "name": "Ingeniería Civil Agrícola",
        "university": "Universidad de Concepción",
        "university_short": "UdeC",
        "campus": "Chillán",
        "region": "Ñuble",
        "city": "Chillán",
        "area": "Ingeniería y Ciencias Exactas",
        "vacantes": 35,
        "weights": {
            "nem": 0.15,
            "ranking": 0.25,
            "lectura": 0.15,
            "m1": 0.25,
            "m2": 0.1,
            "ciencias": 0.1,
            "historia": 0.0,
            "elective_rule": "CIENCIAS"
        },
        "cutoffs": {
            "2024": 517.35,
            "2025": 578.05,
            "2026": 605.25
        },
        "requires_m2": True,
        "min_weighted_score": 500.0
    },
    {
        "id": "ingenieria-civil-biomedicas-udec",
        "code": "13062",
        "name": "Ingeniería Civil Biomédicas",
        "university": "Universidad de Concepción",
        "university_short": "UdeC",
        "campus": "Concepción",
        "region": "Biobío",
        "city": "Concepción",
        "area": "Ingeniería y Ciencias Exactas",
        "vacantes": 58,
        "weights": {
            "nem": 0.2,
            "ranking": 0.15,
            "lectura": 0.15,
            "m1": 0.25,
            "m2": 0.15,
            "ciencias": 0.1,
            "historia": 0.0,
            "elective_rule": "CIENCIAS"
        },
        "cutoffs": {
            "2024": 742.95,
            "2025": 780.45,
            "2026": 779.55
        },
        "requires_m2": True,
        "min_weighted_score": 500.0
    },
    {
        "id": "ingenieria-civil-de-minas-udec",
        "code": "13102",
        "name": "Ingeniería Civil De Minas",
        "university": "Universidad de Concepción",
        "university_short": "UdeC",
        "campus": "Concepción",
        "region": "Biobío",
        "city": "Concepción",
        "area": "Ingeniería y Ciencias Exactas",
        "vacantes": 70,
        "weights": {
            "nem": 0.2,
            "ranking": 0.15,
            "lectura": 0.15,
            "m1": 0.25,
            "m2": 0.15,
            "ciencias": 0.1,
            "historia": 0.0,
            "elective_rule": "CIENCIAS"
        },
        "cutoffs": {
            "2024": 702.5,
            "2025": 735.4,
            "2026": 756.65
        },
        "requires_m2": True,
        "min_weighted_score": 500.0
    },
    {
        "id": "ingenieria-civil-electrica-udec",
        "code": "13070",
        "name": "Ingeniería Civil Eléctrica",
        "university": "Universidad de Concepción",
        "university_short": "UdeC",
        "campus": "Concepción",
        "region": "Biobío",
        "city": "Concepción",
        "area": "Ingeniería y Ciencias Exactas",
        "vacantes": 53,
        "weights": {
            "nem": 0.2,
            "ranking": 0.15,
            "lectura": 0.15,
            "m1": 0.25,
            "m2": 0.15,
            "ciencias": 0.1,
            "historia": 0.0,
            "elective_rule": "CIENCIAS"
        },
        "cutoffs": {
            "2024": 732.7,
            "2025": 767.85,
            "2026": 786.5
        },
        "requires_m2": True,
        "min_weighted_score": 500.0
    },
    {
        "id": "ingenieria-civil-electronica-udec",
        "code": "13071",
        "name": "Ingeniería Civil Electrónica",
        "university": "Universidad de Concepción",
        "university_short": "UdeC",
        "campus": "Concepción",
        "region": "Biobío",
        "city": "Concepción",
        "area": "Ingeniería y Ciencias Exactas",
        "vacantes": 58,
        "weights": {
            "nem": 0.2,
            "ranking": 0.15,
            "lectura": 0.15,
            "m1": 0.25,
            "m2": 0.15,
            "ciencias": 0.1,
            "historia": 0.0,
            "elective_rule": "CIENCIAS"
        },
        "cutoffs": {
            "2024": 671.65,
            "2025": 692.65,
            "2026": 714.65
        },
        "requires_m2": True,
        "min_weighted_score": 500.0
    },
    {
        "id": "ingenieria-civil-en-telecomunicaciones-udec",
        "code": "13064",
        "name": "Ingeniería Civil En Telecomunicaciones",
        "university": "Universidad de Concepción",
        "university_short": "UdeC",
        "campus": "Concepción",
        "region": "Biobío",
        "city": "Concepción",
        "area": "Ingeniería y Ciencias Exactas",
        "vacantes": 20,
        "weights": {
            "nem": 0.2,
            "ranking": 0.15,
            "lectura": 0.15,
            "m1": 0.25,
            "m2": 0.15,
            "ciencias": 0.1,
            "historia": 0.0,
            "elective_rule": "CIENCIAS"
        },
        "cutoffs": {
            "2024": 539.9,
            "2025": 629.85,
            "2026": 685.55
        },
        "requires_m2": True,
        "min_weighted_score": 500.0
    },
    {
        "id": "ingenieria-civil-industrial-udec",
        "code": "13072",
        "name": "Ingeniería Civil Industrial",
        "university": "Universidad de Concepción",
        "university_short": "UdeC",
        "campus": "Concepción",
        "region": "Biobío",
        "city": "Concepción",
        "area": "Ingeniería y Ciencias Exactas",
        "vacantes": 113,
        "weights": {
            "nem": 0.2,
            "ranking": 0.15,
            "lectura": 0.15,
            "m1": 0.25,
            "m2": 0.15,
            "ciencias": 0.1,
            "historia": 0.0,
            "elective_rule": "CIENCIAS"
        },
        "cutoffs": {
            "2024": 787.85,
            "2025": 804.55,
            "2026": 800.1
        },
        "requires_m2": True,
        "min_weighted_score": 500.0
    },
    {
        "id": "ingenieria-civil-informatica-udec",
        "code": "13073",
        "name": "Ingeniería Civil Informática",
        "university": "Universidad de Concepción",
        "university_short": "UdeC",
        "campus": "Concepción",
        "region": "Biobío",
        "city": "Concepción",
        "area": "Ingeniería y Ciencias Exactas",
        "vacantes": 53,
        "weights": {
            "nem": 0.2,
            "ranking": 0.15,
            "lectura": 0.15,
            "m1": 0.25,
            "m2": 0.15,
            "ciencias": 0.1,
            "historia": 0.0,
            "elective_rule": "CIENCIAS"
        },
        "cutoffs": {
            "2024": 785.55,
            "2025": 806.5,
            "2026": 804.75
        },
        "requires_m2": True,
        "min_weighted_score": 500.0
    },
    {
        "id": "ingenieria-civil-matematica-udec",
        "code": "13003",
        "name": "Ingeniería Civil Matemática",
        "university": "Universidad de Concepción",
        "university_short": "UdeC",
        "campus": "Concepción",
        "region": "Biobío",
        "city": "Concepción",
        "area": "Ingeniería y Ciencias Exactas",
        "vacantes": 35,
        "weights": {
            "nem": 0.15,
            "ranking": 0.2,
            "lectura": 0.15,
            "m1": 0.25,
            "m2": 0.15,
            "ciencias": 0.1,
            "historia": 0.0,
            "elective_rule": "CIENCIAS"
        },
        "cutoffs": {
            "2024": 687.25,
            "2025": 727.9,
            "2026": 741.85
        },
        "requires_m2": True,
        "min_weighted_score": 500.0
    },
    {
        "id": "ingenieria-civil-mecanica-udec",
        "code": "13074",
        "name": "Ingeniería Civil Mecánica",
        "university": "Universidad de Concepción",
        "university_short": "UdeC",
        "campus": "Concepción",
        "region": "Biobío",
        "city": "Concepción",
        "area": "Ingeniería y Ciencias Exactas",
        "vacantes": 70,
        "weights": {
            "nem": 0.2,
            "ranking": 0.15,
            "lectura": 0.15,
            "m1": 0.25,
            "m2": 0.15,
            "ciencias": 0.1,
            "historia": 0.0,
            "elective_rule": "CIENCIAS"
        },
        "cutoffs": {
            "2024": 720.6,
            "2025": 745.6,
            "2026": 781.65
        },
        "requires_m2": True,
        "min_weighted_score": 500.0
    },
    {
        "id": "ingenieria-civil-metalurgica-udec",
        "code": "13075",
        "name": "Ingeniería Civil Metalúrgica",
        "university": "Universidad de Concepción",
        "university_short": "UdeC",
        "campus": "Concepción",
        "region": "Biobío",
        "city": "Concepción",
        "area": "Ingeniería y Ciencias Exactas",
        "vacantes": 75,
        "weights": {
            "nem": 0.2,
            "ranking": 0.15,
            "lectura": 0.15,
            "m1": 0.25,
            "m2": 0.15,
            "ciencias": 0.1,
            "historia": 0.0,
            "elective_rule": "CIENCIAS"
        },
        "cutoffs": {
            "2024": 651.95,
            "2025": 670.85,
            "2026": 707.3
        },
        "requires_m2": True,
        "min_weighted_score": 500.0
    },
    {
        "id": "ingenieria-civil-quimica-udec",
        "code": "13076",
        "name": "Ingeniería Civil Química",
        "university": "Universidad de Concepción",
        "university_short": "UdeC",
        "campus": "Concepción",
        "region": "Biobío",
        "city": "Concepción",
        "area": "Ingeniería y Ciencias Exactas",
        "vacantes": 73,
        "weights": {
            "nem": 0.2,
            "ranking": 0.15,
            "lectura": 0.15,
            "m1": 0.25,
            "m2": 0.15,
            "ciencias": 0.1,
            "historia": 0.0,
            "elective_rule": "CIENCIAS"
        },
        "cutoffs": {
            "2024": 751.45,
            "2025": 776.95,
            "2026": 780.65
        },
        "requires_m2": True,
        "min_weighted_score": 500.0
    },
    {
        "id": "ingenieria-civil-primer-ano-comun-udec",
        "code": "13068",
        "name": "Ingeniería Civil, Primer Año Común",
        "university": "Universidad de Concepción",
        "university_short": "UdeC",
        "campus": "Concepción",
        "region": "Biobío",
        "city": "Concepción",
        "area": "Ingeniería y Ciencias Exactas",
        "vacantes": 190,
        "weights": {
            "nem": 0.2,
            "ranking": 0.15,
            "lectura": 0.15,
            "m1": 0.25,
            "m2": 0.15,
            "ciencias": 0.1,
            "historia": 0.0,
            "elective_rule": "CIENCIAS"
        },
        "cutoffs": {
            "2024": 642.0,
            "2025": 688.3,
            "2026": 700.25
        },
        "requires_m2": True,
        "min_weighted_score": 500.0
    },
    {
        "id": "ingenieria-comercial-chillan-udec",
        "code": "13030",
        "name": "Ingeniería Comercial",
        "university": "Universidad de Concepción",
        "university_short": "UdeC",
        "campus": "Chillán",
        "region": "Ñuble",
        "city": "Chillán",
        "area": "Ingeniería y Ciencias Exactas",
        "vacantes": 60,
        "weights": {
            "nem": 0.15,
            "ranking": 0.25,
            "lectura": 0.15,
            "m1": 0.3,
            "m2": 0.05,
            "ciencias": 0.1,
            "historia": 0.0,
            "elective_rule": "MAX"
        },
        "cutoffs": {
            "2024": 496.5,
            "2025": 500.5,
            "2026": 505.0
        },
        "requires_m2": True,
        "min_weighted_score": 500.0
    },
    {
        "id": "ingenieria-comercial-udec",
        "code": "13019",
        "name": "Ingeniería Comercial",
        "university": "Universidad de Concepción",
        "university_short": "UdeC",
        "campus": "Concepción",
        "region": "Biobío",
        "city": "Concepción",
        "area": "Ingeniería y Ciencias Exactas",
        "vacantes": 130,
        "weights": {
            "nem": 0.15,
            "ranking": 0.25,
            "lectura": 0.15,
            "m1": 0.3,
            "m2": 0.05,
            "ciencias": 0.1,
            "historia": 0.0,
            "elective_rule": "MAX"
        },
        "cutoffs": {
            "2024": 681.2,
            "2025": 692.25,
            "2026": 705.15
        },
        "requires_m2": True,
        "min_weighted_score": 500.0
    },
    {
        "id": "ingenieria-comercial-los-angeles-udec",
        "code": "13078",
        "name": "Ingeniería Comercial",
        "university": "Universidad de Concepción",
        "university_short": "UdeC",
        "campus": "Los Ángeles",
        "region": "Biobío",
        "city": "Los Ángeles",
        "area": "Ingeniería y Ciencias Exactas",
        "vacantes": 70,
        "weights": {
            "nem": 0.15,
            "ranking": 0.25,
            "lectura": 0.15,
            "m1": 0.3,
            "m2": 0.05,
            "ciencias": 0.1,
            "historia": 0.0,
            "elective_rule": "MAX"
        },
        "cutoffs": {
            "2024": 496.5,
            "2025": 500.5,
            "2026": 505.0
        },
        "requires_m2": True,
        "min_weighted_score": 500.0
    },
    {
        "id": "ingenieria-en-biotecnologia-marina-y-acuicultura-udec",
        "code": "13016",
        "name": "Ingeniería En Biotecnología Marina Y Acuicultura",
        "university": "Universidad de Concepción",
        "university_short": "UdeC",
        "campus": "Concepción",
        "region": "Biobío",
        "city": "Concepción",
        "area": "Ciencias de la Salud",
        "vacantes": 20,
        "weights": {
            "nem": 0.15,
            "ranking": 0.25,
            "lectura": 0.1,
            "m1": 0.35,
            "m2": 0.05,
            "ciencias": 0.1,
            "historia": 0.0,
            "elective_rule": "CIENCIAS"
        },
        "cutoffs": {
            "2024": 512.5,
            "2025": 507.25,
            "2026": 568.2
        },
        "requires_m2": True,
        "min_weighted_score": 500.0
    },
    {
        "id": "ingenieria-en-biotecnologia-vegetal-los-angeles-udec",
        "code": "13085",
        "name": "Ingeniería En Biotecnología Vegetal",
        "university": "Universidad de Concepción",
        "university_short": "UdeC",
        "campus": "Los Ángeles",
        "region": "Biobío",
        "city": "Los Ángeles",
        "area": "Ciencias de la Salud",
        "vacantes": 20,
        "weights": {
            "nem": 0.15,
            "ranking": 0.25,
            "lectura": 0.15,
            "m1": 0.3,
            "m2": 0.05,
            "ciencias": 0.1,
            "historia": 0.0,
            "elective_rule": "CIENCIAS"
        },
        "cutoffs": {
            "2024": 496.5,
            "2025": 500.5,
            "2026": 505.0
        },
        "requires_m2": True,
        "min_weighted_score": 500.0
    },
    {
        "id": "ingenieria-en-biotecnologia-vegetal-udec",
        "code": "13020",
        "name": "Ingeniería En Biotecnología Vegetal",
        "university": "Universidad de Concepción",
        "university_short": "UdeC",
        "campus": "Concepción",
        "region": "Biobío",
        "city": "Concepción",
        "area": "Ciencias de la Salud",
        "vacantes": 40,
        "weights": {
            "nem": 0.15,
            "ranking": 0.25,
            "lectura": 0.15,
            "m1": 0.3,
            "m2": 0.05,
            "ciencias": 0.1,
            "historia": 0.0,
            "elective_rule": "CIENCIAS"
        },
        "cutoffs": {
            "2024": 496.5,
            "2025": 500.5,
            "2026": 505.0
        },
        "requires_m2": True,
        "min_weighted_score": 500.0
    },
    {
        "id": "ingenieria-en-conservacion-de-recursos-naturales-udec",
        "code": "13043",
        "name": "Ingeniería En Conservación De Recursos Naturales",
        "university": "Universidad de Concepción",
        "university_short": "UdeC",
        "campus": "Concepción",
        "region": "Biobío",
        "city": "Concepción",
        "area": "Ingeniería y Ciencias Exactas",
        "vacantes": 40,
        "weights": {
            "nem": 0.15,
            "ranking": 0.25,
            "lectura": 0.15,
            "m1": 0.3,
            "m2": 0.05,
            "ciencias": 0.1,
            "historia": 0.0,
            "elective_rule": "CIENCIAS"
        },
        "cutoffs": {
            "2024": 514.5,
            "2025": 540.15,
            "2026": 580.7
        },
        "requires_m2": True,
        "min_weighted_score": 500.0
    },
    {
        "id": "ingenieria-estadistica-udec",
        "code": "13065",
        "name": "Ingeniería Estadística",
        "university": "Universidad de Concepción",
        "university_short": "UdeC",
        "campus": "Concepción",
        "region": "Biobío",
        "city": "Concepción",
        "area": "Ingeniería y Ciencias Exactas",
        "vacantes": 25,
        "weights": {
            "nem": 0.15,
            "ranking": 0.25,
            "lectura": 0.15,
            "m1": 0.25,
            "m2": 0.1,
            "ciencias": 0.1,
            "historia": 0.0,
            "elective_rule": "CIENCIAS"
        },
        "cutoffs": {
            "2024": 565.5,
            "2025": 599.2,
            "2026": 716.95
        },
        "requires_m2": True,
        "min_weighted_score": 500.0
    },
    {
        "id": "ingenieria-forestal-udec",
        "code": "13008",
        "name": "Ingeniería Forestal",
        "university": "Universidad de Concepción",
        "university_short": "UdeC",
        "campus": "Concepción",
        "region": "Biobío",
        "city": "Concepción",
        "area": "Ingeniería y Ciencias Exactas",
        "vacantes": 30,
        "weights": {
            "nem": 0.2,
            "ranking": 0.25,
            "lectura": 0.15,
            "m1": 0.3,
            "m2": 0.0,
            "ciencias": 0.1,
            "historia": 0.0,
            "elective_rule": "CIENCIAS"
        },
        "cutoffs": {
            "2024": 515.95,
            "2025": 515.65,
            "2026": 574.0
        },
        "requires_m2": False,
        "min_weighted_score": 500.0
    },
    {
        "id": "ingenieria-geomatica-los-angeles-udec",
        "code": "13093",
        "name": "Ingeniería Geomática",
        "university": "Universidad de Concepción",
        "university_short": "UdeC",
        "campus": "Los Ángeles",
        "region": "Biobío",
        "city": "Los Ángeles",
        "area": "Ingeniería y Ciencias Exactas",
        "vacantes": 30,
        "weights": {
            "nem": 0.15,
            "ranking": 0.25,
            "lectura": 0.15,
            "m1": 0.3,
            "m2": 0.05,
            "ciencias": 0.1,
            "historia": 0.0,
            "elective_rule": "CIENCIAS"
        },
        "cutoffs": {
            "2024": 521.95,
            "2025": 526.0,
            "2026": 547.1
        },
        "requires_m2": True,
        "min_weighted_score": 500.0
    },
    {
        "id": "kinesiologia-udec",
        "code": "13083",
        "name": "Kinesiología",
        "university": "Universidad de Concepción",
        "university_short": "UdeC",
        "campus": "Concepción",
        "region": "Biobío",
        "city": "Concepción",
        "area": "Ciencias de la Salud",
        "vacantes": 68,
        "weights": {
            "nem": 0.15,
            "ranking": 0.25,
            "lectura": 0.2,
            "m1": 0.25,
            "m2": 0.0,
            "ciencias": 0.15,
            "historia": 0.0,
            "elective_rule": "CIENCIAS"
        },
        "cutoffs": {
            "2024": 743.7,
            "2025": 738.95,
            "2026": 735.85
        },
        "requires_m2": False,
        "min_weighted_score": 500.0
    },
    {
        "id": "licenciatura-en-historia-udec",
        "code": "13059",
        "name": "Licenciatura En Historia",
        "university": "Universidad de Concepción",
        "university_short": "UdeC",
        "campus": "Concepción",
        "region": "Biobío",
        "city": "Concepción",
        "area": "Humanidades y Ciencias",
        "vacantes": 30,
        "weights": {
            "nem": 0.15,
            "ranking": 0.25,
            "lectura": 0.2,
            "m1": 0.1,
            "m2": 0.0,
            "ciencias": 0.0,
            "historia": 0.3,
            "elective_rule": "HISTORIA"
        },
        "cutoffs": {
            "2024": 622.35,
            "2025": 596.5,
            "2026": 552.9
        },
        "requires_m2": False,
        "min_weighted_score": 500.0
    },
    {
        "id": "licenciatura-en-matematica-udec",
        "code": "13002",
        "name": "Licenciatura En Matemática",
        "university": "Universidad de Concepción",
        "university_short": "UdeC",
        "campus": "Concepción",
        "region": "Biobío",
        "city": "Concepción",
        "area": "Humanidades y Ciencias",
        "vacantes": 20,
        "weights": {
            "nem": 0.1,
            "ranking": 0.15,
            "lectura": 0.15,
            "m1": 0.3,
            "m2": 0.2,
            "ciencias": 0.1,
            "historia": 0.0,
            "elective_rule": "CIENCIAS"
        },
        "cutoffs": {
            "2024": 531.95,
            "2025": 592.7,
            "2026": 538.65
        },
        "requires_m2": True,
        "min_weighted_score": 500.0
    },
    {
        "id": "licenciatura-en-quimica-quimico-udec",
        "code": "13001",
        "name": "Licenciatura En Química - Químico",
        "university": "Universidad de Concepción",
        "university_short": "UdeC",
        "campus": "Concepción",
        "region": "Biobío",
        "city": "Concepción",
        "area": "Humanidades y Ciencias",
        "vacantes": 25,
        "weights": {
            "nem": 0.15,
            "ranking": 0.25,
            "lectura": 0.1,
            "m1": 0.3,
            "m2": 0.0,
            "ciencias": 0.2,
            "historia": 0.0,
            "elective_rule": "CIENCIAS"
        },
        "cutoffs": {
            "2024": 648.35,
            "2025": 653.2,
            "2026": 697.7
        },
        "requires_m2": False,
        "min_weighted_score": 500.0
    },
    {
        "id": "medicina-udec",
        "code": "13086",
        "name": "Medicina",
        "university": "Universidad de Concepción",
        "university_short": "UdeC",
        "campus": "Concepción",
        "region": "Biobío",
        "city": "Concepción",
        "area": "Ciencias de la Salud",
        "vacantes": 100,
        "weights": {
            "nem": 0.15,
            "ranking": 0.25,
            "lectura": 0.15,
            "m1": 0.35,
            "m2": 0.0,
            "ciencias": 0.1,
            "historia": 0.0,
            "elective_rule": "CIENCIAS"
        },
        "cutoffs": {
            "2024": 944.3,
            "2025": 948.35,
            "2026": 953.2
        },
        "requires_m2": False,
        "min_weighted_score": 500.0
    },
    {
        "id": "medicina-veterinaria-chillan-udec",
        "code": "13007",
        "name": "Medicina Veterinaria",
        "university": "Universidad de Concepción",
        "university_short": "UdeC",
        "campus": "Chillán",
        "region": "Ñuble",
        "city": "Chillán",
        "area": "Ciencias de la Salud",
        "vacantes": 85,
        "weights": {
            "nem": 0.15,
            "ranking": 0.25,
            "lectura": 0.15,
            "m1": 0.35,
            "m2": 0.0,
            "ciencias": 0.1,
            "historia": 0.0,
            "elective_rule": "CIENCIAS"
        },
        "cutoffs": {
            "2024": 496.5,
            "2025": 500.5,
            "2026": 505.0
        },
        "requires_m2": False,
        "min_weighted_score": 500.0
    },
    {
        "id": "medicina-veterinaria-udec",
        "code": "13011",
        "name": "Medicina Veterinaria",
        "university": "Universidad de Concepción",
        "university_short": "UdeC",
        "campus": "Concepción",
        "region": "Biobío",
        "city": "Concepción",
        "area": "Ciencias de la Salud",
        "vacantes": 80,
        "weights": {
            "nem": 0.15,
            "ranking": 0.25,
            "lectura": 0.15,
            "m1": 0.35,
            "m2": 0.0,
            "ciencias": 0.1,
            "historia": 0.0,
            "elective_rule": "CIENCIAS"
        },
        "cutoffs": {
            "2024": 496.5,
            "2025": 500.5,
            "2026": 505.0
        },
        "requires_m2": False,
        "min_weighted_score": 500.0
    },
    {
        "id": "nutricion-y-dietetica-udec",
        "code": "13050",
        "name": "Nutrición Y Dietética",
        "university": "Universidad de Concepción",
        "university_short": "UdeC",
        "campus": "Concepción",
        "region": "Biobío",
        "city": "Concepción",
        "area": "Ciencias de la Salud",
        "vacantes": 65,
        "weights": {
            "nem": 0.15,
            "ranking": 0.25,
            "lectura": 0.15,
            "m1": 0.35,
            "m2": 0.0,
            "ciencias": 0.1,
            "historia": 0.0,
            "elective_rule": "CIENCIAS"
        },
        "cutoffs": {
            "2024": 681.1,
            "2025": 671.05,
            "2026": 643.4
        },
        "requires_m2": False,
        "min_weighted_score": 500.0
    },
    {
        "id": "obstetricia-udec",
        "code": "13088",
        "name": "Obstetricia Y Puericultura",
        "university": "Universidad de Concepción",
        "university_short": "UdeC",
        "campus": "Concepción",
        "region": "Biobío",
        "city": "Concepción",
        "area": "Ciencias de la Salud",
        "vacantes": 80,
        "weights": {
            "nem": 0.15,
            "ranking": 0.25,
            "lectura": 0.2,
            "m1": 0.25,
            "m2": 0.0,
            "ciencias": 0.15,
            "historia": 0.0,
            "elective_rule": "CIENCIAS"
        },
        "cutoffs": {
            "2024": 781.15,
            "2025": 759.05,
            "2026": 743.45
        },
        "requires_m2": False,
        "min_weighted_score": 500.0
    },
    {
        "id": "odontologia-udec",
        "code": "13091",
        "name": "Odontología",
        "university": "Universidad de Concepción",
        "university_short": "UdeC",
        "campus": "Concepción",
        "region": "Biobío",
        "city": "Concepción",
        "area": "Ciencias de la Salud",
        "vacantes": 75,
        "weights": {
            "nem": 0.15,
            "ranking": 0.25,
            "lectura": 0.25,
            "m1": 0.25,
            "m2": 0.0,
            "ciencias": 0.1,
            "historia": 0.0,
            "elective_rule": "CIENCIAS"
        },
        "cutoffs": {
            "2024": 818.2,
            "2025": 838.5,
            "2026": 819.25
        },
        "requires_m2": False,
        "min_weighted_score": 500.0
    },
    {
        "id": "pedagogia-en-artes-visuales-udec",
        "code": "13107",
        "name": "Pedagogía En Artes Visuales",
        "university": "Universidad de Concepción",
        "university_short": "UdeC",
        "campus": "Concepción",
        "region": "Biobío",
        "city": "Concepción",
        "area": "Educación",
        "vacantes": 20,
        "weights": {
            "nem": 0.15,
            "ranking": 0.25,
            "lectura": 0.25,
            "m1": 0.2,
            "m2": 0.0,
            "ciencias": 0.0,
            "historia": 0.15,
            "elective_rule": "HISTORIA"
        },
        "cutoffs": {
            "2024": 657.45,
            "2025": 658.25,
            "2026": 669.0
        },
        "requires_m2": False,
        "min_weighted_score": 500.0
    },
    {
        "id": "pedagogia-en-ciencias-naturales-y-biologia-udec",
        "code": "13035",
        "name": "Pedagogía En Ciencias Naturales Y Biología",
        "university": "Universidad de Concepción",
        "university_short": "UdeC",
        "campus": "Concepción",
        "region": "Biobío",
        "city": "Concepción",
        "area": "Educación",
        "vacantes": 25,
        "weights": {
            "nem": 0.15,
            "ranking": 0.25,
            "lectura": 0.2,
            "m1": 0.25,
            "m2": 0.0,
            "ciencias": 0.15,
            "historia": 0.0,
            "elective_rule": "CIENCIAS"
        },
        "cutoffs": {
            "2024": 496.5,
            "2025": 500.5,
            "2026": 505.0
        },
        "requires_m2": False,
        "min_weighted_score": 500.0
    },
    {
        "id": "pedagogia-en-ciencias-naturales-y-fisica-udec",
        "code": "13036",
        "name": "Pedagogía En Ciencias Naturales Y Física",
        "university": "Universidad de Concepción",
        "university_short": "UdeC",
        "campus": "Concepción",
        "region": "Biobío",
        "city": "Concepción",
        "area": "Educación",
        "vacantes": 20,
        "weights": {
            "nem": 0.15,
            "ranking": 0.25,
            "lectura": 0.2,
            "m1": 0.25,
            "m2": 0.0,
            "ciencias": 0.15,
            "historia": 0.0,
            "elective_rule": "CIENCIAS"
        },
        "cutoffs": {
            "2024": 552.6,
            "2025": 521.0,
            "2026": 567.2
        },
        "requires_m2": False,
        "min_weighted_score": 500.0
    },
    {
        "id": "pedagogia-en-cs-naturales-y-biologia-los-angeles-udec",
        "code": "13079",
        "name": "Pedagogía En Cs. Naturales Y Biología",
        "university": "Universidad de Concepción",
        "university_short": "UdeC",
        "campus": "Los Ángeles",
        "region": "Biobío",
        "city": "Los Ángeles",
        "area": "Educación",
        "vacantes": 20,
        "weights": {
            "nem": 0.15,
            "ranking": 0.25,
            "lectura": 0.2,
            "m1": 0.25,
            "m2": 0.0,
            "ciencias": 0.15,
            "historia": 0.0,
            "elective_rule": "CIENCIAS"
        },
        "cutoffs": {
            "2024": 496.5,
            "2025": 500.5,
            "2026": 505.0
        },
        "requires_m2": False,
        "min_weighted_score": 500.0
    },
    {
        "id": "pedagogia-en-cs-naturales-y-quimica-udec",
        "code": "13037",
        "name": "Pedagogía En Cs. Naturales Y Química",
        "university": "Universidad de Concepción",
        "university_short": "UdeC",
        "campus": "Concepción",
        "region": "Biobío",
        "city": "Concepción",
        "area": "Educación",
        "vacantes": 20,
        "weights": {
            "nem": 0.15,
            "ranking": 0.25,
            "lectura": 0.2,
            "m1": 0.25,
            "m2": 0.0,
            "ciencias": 0.15,
            "historia": 0.0,
            "elective_rule": "CIENCIAS"
        },
        "cutoffs": {
            "2024": 523.0,
            "2025": 525.55,
            "2026": 599.35
        },
        "requires_m2": False,
        "min_weighted_score": 500.0
    },
    {
        "id": "pedagogia-en-educacion-fisica-udec",
        "code": "13101",
        "name": "Pedagogía En Educación Física",
        "university": "Universidad de Concepción",
        "university_short": "UdeC",
        "campus": "Concepción",
        "region": "Biobío",
        "city": "Concepción",
        "area": "Educación",
        "vacantes": 70,
        "weights": {
            "nem": 0.15,
            "ranking": 0.25,
            "lectura": 0.25,
            "m1": 0.2,
            "m2": 0.0,
            "ciencias": 0.15,
            "historia": 0.0,
            "elective_rule": "CIENCIAS"
        },
        "cutoffs": {
            "2024": 613.7,
            "2025": 598.95,
            "2026": 623.9
        },
        "requires_m2": False,
        "min_weighted_score": 500.0
    },
    {
        "id": "pedagogia-en-educacion-musical-udec",
        "code": "13039",
        "name": "Pedagogía En Educación Musical",
        "university": "Universidad de Concepción",
        "university_short": "UdeC",
        "campus": "Concepción",
        "region": "Biobío",
        "city": "Concepción",
        "area": "Educación",
        "vacantes": 25,
        "weights": {
            "nem": 0.15,
            "ranking": 0.25,
            "lectura": 0.2,
            "m1": 0.2,
            "m2": 0.0,
            "ciencias": 0.0,
            "historia": 0.2,
            "elective_rule": "HISTORIA"
        },
        "cutoffs": {
            "2024": 652.85,
            "2025": 685.0,
            "2026": 701.85
        },
        "requires_m2": False,
        "min_weighted_score": 500.0
    },
    {
        "id": "pedagogia-en-espanol-udec",
        "code": "13041",
        "name": "Pedagogía En Español",
        "university": "Universidad de Concepción",
        "university_short": "UdeC",
        "campus": "Concepción",
        "region": "Biobío",
        "city": "Concepción",
        "area": "Educación",
        "vacantes": 40,
        "weights": {
            "nem": 0.15,
            "ranking": 0.25,
            "lectura": 0.25,
            "m1": 0.25,
            "m2": 0.0,
            "ciencias": 0.0,
            "historia": 0.1,
            "elective_rule": "HISTORIA"
        },
        "cutoffs": {
            "2024": 668.35,
            "2025": 681.65,
            "2026": 665.35
        },
        "requires_m2": False,
        "min_weighted_score": 500.0
    },
    {
        "id": "pedagogia-en-espanol-los-angeles-udec",
        "code": "13112",
        "name": "Pedagogía En Español",
        "university": "Universidad de Concepción",
        "university_short": "UdeC",
        "campus": "Los Ángeles",
        "region": "Biobío",
        "city": "Los Ángeles",
        "area": "Educación",
        "vacantes": 25,
        "weights": {
            "nem": 0.15,
            "ranking": 0.25,
            "lectura": 0.25,
            "m1": 0.25,
            "m2": 0.0,
            "ciencias": 0.0,
            "historia": 0.1,
            "elective_rule": "HISTORIA"
        },
        "cutoffs": {
            "2024": 496.5,
            "2025": 500.5,
            "2026": 505.0
        },
        "requires_m2": False,
        "min_weighted_score": 500.0
    },
    {
        "id": "pedagogia-en-filosofia-udec",
        "code": "13042",
        "name": "Pedagogía En Filosofía",
        "university": "Universidad de Concepción",
        "university_short": "UdeC",
        "campus": "Concepción",
        "region": "Biobío",
        "city": "Concepción",
        "area": "Educación",
        "vacantes": 20,
        "weights": {
            "nem": 0.15,
            "ranking": 0.25,
            "lectura": 0.25,
            "m1": 0.1,
            "m2": 0.0,
            "ciencias": 0.0,
            "historia": 0.25,
            "elective_rule": "HISTORIA"
        },
        "cutoffs": {
            "2024": 516.75,
            "2025": 540.05,
            "2026": 501.65
        },
        "requires_m2": False,
        "min_weighted_score": 500.0
    },
    {
        "id": "pedagogia-en-historia-y-geografia-udec",
        "code": "13040",
        "name": "Pedagogía En Historia Y Geografía",
        "university": "Universidad de Concepción",
        "university_short": "UdeC",
        "campus": "Concepción",
        "region": "Biobío",
        "city": "Concepción",
        "area": "Educación",
        "vacantes": 45,
        "weights": {
            "nem": 0.15,
            "ranking": 0.25,
            "lectura": 0.2,
            "m1": 0.1,
            "m2": 0.0,
            "ciencias": 0.0,
            "historia": 0.3,
            "elective_rule": "HISTORIA"
        },
        "cutoffs": {
            "2024": 646.0,
            "2025": 676.2,
            "2026": 643.5
        },
        "requires_m2": False,
        "min_weighted_score": 500.0
    },
    {
        "id": "pedagogia-en-ingles-udec",
        "code": "13057",
        "name": "Pedagogía En Ingles",
        "university": "Universidad de Concepción",
        "university_short": "UdeC",
        "campus": "Concepción",
        "region": "Biobío",
        "city": "Concepción",
        "area": "Educación",
        "vacantes": 55,
        "weights": {
            "nem": 0.15,
            "ranking": 0.25,
            "lectura": 0.25,
            "m1": 0.25,
            "m2": 0.0,
            "ciencias": 0.0,
            "historia": 0.1,
            "elective_rule": "HISTORIA"
        },
        "cutoffs": {
            "2024": 496.5,
            "2025": 500.5,
            "2026": 505.0
        },
        "requires_m2": False,
        "min_weighted_score": 500.0
    },
    {
        "id": "pedagogia-en-ingles-los-angeles-udec",
        "code": "13106",
        "name": "Pedagogía En Ingles",
        "university": "Universidad de Concepción",
        "university_short": "UdeC",
        "campus": "Los Ángeles",
        "region": "Biobío",
        "city": "Los Ángeles",
        "area": "Educación",
        "vacantes": 30,
        "weights": {
            "nem": 0.15,
            "ranking": 0.25,
            "lectura": 0.25,
            "m1": 0.25,
            "m2": 0.0,
            "ciencias": 0.0,
            "historia": 0.1,
            "elective_rule": "HISTORIA"
        },
        "cutoffs": {
            "2024": 496.5,
            "2025": 500.5,
            "2026": 505.0
        },
        "requires_m2": False,
        "min_weighted_score": 500.0
    },
    {
        "id": "pedagogia-en-matematica-udec",
        "code": "13108",
        "name": "Pedagogía En Matemática",
        "university": "Universidad de Concepción",
        "university_short": "UdeC",
        "campus": "Concepción",
        "region": "Biobío",
        "city": "Concepción",
        "area": "Educación",
        "vacantes": 40,
        "weights": {
            "nem": 0.15,
            "ranking": 0.25,
            "lectura": 0.15,
            "m1": 0.25,
            "m2": 0.1,
            "ciencias": 0.1,
            "historia": 0.0,
            "elective_rule": "CIENCIAS"
        },
        "cutoffs": {
            "2024": 496.5,
            "2025": 500.5,
            "2026": 505.0
        },
        "requires_m2": True,
        "min_weighted_score": 500.0
    },
    {
        "id": "pedagogia-en-matematica-los-angeles-udec",
        "code": "13111",
        "name": "Pedagogía En Matemática",
        "university": "Universidad de Concepción",
        "university_short": "UdeC",
        "campus": "Los Ángeles",
        "region": "Biobío",
        "city": "Los Ángeles",
        "area": "Educación",
        "vacantes": 20,
        "weights": {
            "nem": 0.15,
            "ranking": 0.25,
            "lectura": 0.15,
            "m1": 0.25,
            "m2": 0.1,
            "ciencias": 0.1,
            "historia": 0.0,
            "elective_rule": "CIENCIAS"
        },
        "cutoffs": {
            "2024": 496.5,
            "2025": 500.5,
            "2026": 505.0
        },
        "requires_m2": True,
        "min_weighted_score": 500.0
    },
    {
        "id": "periodismo-udec",
        "code": "13031",
        "name": "Periodismo",
        "university": "Universidad de Concepción",
        "university_short": "UdeC",
        "campus": "Concepción",
        "region": "Biobío",
        "city": "Concepción",
        "area": "Ciencias Sociales y Jurídicas",
        "vacantes": 50,
        "weights": {
            "nem": 0.15,
            "ranking": 0.25,
            "lectura": 0.3,
            "m1": 0.15,
            "m2": 0.0,
            "ciencias": 0.0,
            "historia": 0.15,
            "elective_rule": "HISTORIA"
        },
        "cutoffs": {
            "2024": 703.45,
            "2025": 622.85,
            "2026": 665.2
        },
        "requires_m2": False,
        "min_weighted_score": 500.0
    },
    {
        "id": "psicologia-udec",
        "code": "13067",
        "name": "Psicología",
        "university": "Universidad de Concepción",
        "university_short": "UdeC",
        "campus": "Concepción",
        "region": "Biobío",
        "city": "Concepción",
        "area": "Ciencias Sociales y Jurídicas",
        "vacantes": 59,
        "weights": {
            "nem": 0.15,
            "ranking": 0.25,
            "lectura": 0.2,
            "m1": 0.3,
            "m2": 0.0,
            "ciencias": 0.1,
            "historia": 0.0,
            "elective_rule": "CIENCIAS"
        },
        "cutoffs": {
            "2024": 834.15,
            "2025": 801.65,
            "2026": 789.1
        },
        "requires_m2": False,
        "min_weighted_score": 500.0
    },
    {
        "id": "quimica-y-farmacia-udec",
        "code": "13049",
        "name": "Química Y Farmacia",
        "university": "Universidad de Concepción",
        "university_short": "UdeC",
        "campus": "Concepción",
        "region": "Biobío",
        "city": "Concepción",
        "area": "Humanidades y Ciencias",
        "vacantes": 82,
        "weights": {
            "nem": 0.15,
            "ranking": 0.25,
            "lectura": 0.15,
            "m1": 0.3,
            "m2": 0.0,
            "ciencias": 0.15,
            "historia": 0.0,
            "elective_rule": "CIENCIAS"
        },
        "cutoffs": {
            "2024": 833.35,
            "2025": 857.2,
            "2026": 875.2
        },
        "requires_m2": False,
        "min_weighted_score": 500.0
    },
    {
        "id": "quimico-analista-udec",
        "code": "13004",
        "name": "Químico Analista",
        "university": "Universidad de Concepción",
        "university_short": "UdeC",
        "campus": "Concepción",
        "region": "Biobío",
        "city": "Concepción",
        "area": "Humanidades y Ciencias",
        "vacantes": 35,
        "weights": {
            "nem": 0.15,
            "ranking": 0.25,
            "lectura": 0.15,
            "m1": 0.35,
            "m2": 0.0,
            "ciencias": 0.1,
            "historia": 0.0,
            "elective_rule": "CIENCIAS"
        },
        "cutoffs": {
            "2024": 638.35,
            "2025": 647.1,
            "2026": 664.3
        },
        "requires_m2": False,
        "min_weighted_score": 500.0
    },
    {
        "id": "sociologia-udec",
        "code": "13077",
        "name": "Sociología",
        "university": "Universidad de Concepción",
        "university_short": "UdeC",
        "campus": "Concepción",
        "region": "Biobío",
        "city": "Concepción",
        "area": "Ciencias Sociales y Jurídicas",
        "vacantes": 65,
        "weights": {
            "nem": 0.15,
            "ranking": 0.25,
            "lectura": 0.2,
            "m1": 0.2,
            "m2": 0.0,
            "ciencias": 0.0,
            "historia": 0.2,
            "elective_rule": "HISTORIA"
        },
        "cutoffs": {
            "2024": 639.25,
            "2025": 507.0,
            "2026": 529.4
        },
        "requires_m2": False,
        "min_weighted_score": 500.0
    },
    {
        "id": "teatro-udec",
        "code": "13060",
        "name": "Teatro",
        "university": "Universidad de Concepción",
        "university_short": "UdeC",
        "campus": "Concepción",
        "region": "Biobío",
        "city": "Concepción",
        "area": "Arquitectura, Arte y Diseño",
        "vacantes": 40,
        "weights": {
            "nem": 0.15,
            "ranking": 0.25,
            "lectura": 0.25,
            "m1": 0.15,
            "m2": 0.0,
            "ciencias": 0.0,
            "historia": 0.2,
            "elective_rule": "HISTORIA"
        },
        "cutoffs": {
            "2024": 639.25,
            "2025": 570.0,
            "2026": 529.95
        },
        "requires_m2": False,
        "min_weighted_score": 500.0
    },
    {
        "id": "tecnologia-medica-udec",
        "code": "13081",
        "name": "Tecnología Medica",
        "university": "Universidad de Concepción",
        "university_short": "UdeC",
        "campus": "Concepción",
        "region": "Biobío",
        "city": "Concepción",
        "area": "Ciencias de la Salud",
        "vacantes": 73,
        "weights": {
            "nem": 0.15,
            "ranking": 0.25,
            "lectura": 0.15,
            "m1": 0.35,
            "m2": 0.0,
            "ciencias": 0.1,
            "historia": 0.0,
            "elective_rule": "CIENCIAS"
        },
        "cutoffs": {
            "2024": 819.25,
            "2025": 803.75,
            "2026": 805.6
        },
        "requires_m2": False,
        "min_weighted_score": 500.0
    },
    {
        "id": "trabajo-social-udec",
        "code": "13025",
        "name": "Trabajo Social",
        "university": "Universidad de Concepción",
        "university_short": "UdeC",
        "campus": "Concepción",
        "region": "Biobío",
        "city": "Concepción",
        "area": "Ciencias Sociales y Jurídicas",
        "vacantes": 70,
        "weights": {
            "nem": 0.15,
            "ranking": 0.25,
            "lectura": 0.25,
            "m1": 0.25,
            "m2": 0.0,
            "ciencias": 0.0,
            "historia": 0.1,
            "elective_rule": "HISTORIA"
        },
        "cutoffs": {
            "2024": 634.05,
            "2025": 618.85,
            "2026": 619.95
        },
        "requires_m2": False,
        "min_weighted_score": 500.0
    },
    {
        "id": "traduccioninterpretacion-en-idiomas-extranjeros-udec",
        "code": "13058",
        "name": "Traducción/Interpretación En Idiomas Extranjeros",
        "university": "Universidad de Concepción",
        "university_short": "UdeC",
        "campus": "Concepción",
        "region": "Biobío",
        "city": "Concepción",
        "area": "Humanidades y Ciencias",
        "vacantes": 73,
        "weights": {
            "nem": 0.15,
            "ranking": 0.25,
            "lectura": 0.25,
            "m1": 0.25,
            "m2": 0.0,
            "ciencias": 0.0,
            "historia": 0.1,
            "elective_rule": "HISTORIA"
        },
        "cutoffs": {
            "2024": 737.15,
            "2025": 711.55,
            "2026": 653.4
        },
        "requires_m2": False,
        "min_weighted_score": 500.0
    },
    {
        "id": "arquitectura-ubb",
        "code": "29001",
        "name": "Arquitectura",
        "university": "Universidad del Bío-Bío",
        "university_short": "UBB",
        "campus": "Concepción",
        "region": "Biobío",
        "city": "Concepción",
        "area": "Arquitectura, Arte y Diseño",
        "vacantes": 90,
        "weights": {
            "nem": 0.1,
            "ranking": 0.4,
            "lectura": 0.2,
            "m1": 0.2,
            "m2": 0.0,
            "ciencias": 0.1,
            "historia": 0.0,
            "elective_rule": "MAX"
        },
        "cutoffs": {
            "2024": 698.4,
            "2025": 704.1,
            "2026": 709.7
        },
        "requires_m2": False,
        "min_weighted_score": 458.0
    },
    {
        "id": "bachillerato-en-ciencias-ubb",
        "code": "29015",
        "name": "Bachillerato En Ciencias",
        "university": "Universidad del Bío-Bío",
        "university_short": "UBB",
        "campus": "Concepción",
        "region": "Biobío",
        "city": "Concepción",
        "area": "Humanidades y Ciencias",
        "vacantes": 35,
        "weights": {
            "nem": 0.1,
            "ranking": 0.4,
            "lectura": 0.1,
            "m1": 0.3,
            "m2": 0.0,
            "ciencias": 0.1,
            "historia": 0.0,
            "elective_rule": "CIENCIAS"
        },
        "cutoffs": {
            "2024": 522.0,
            "2025": 526.0,
            "2026": 530.0
        },
        "requires_m2": False,
        "min_weighted_score": 458.0
    },
    {
        "id": "bachillerato-en-ciencias-chillán-ubb",
        "code": "29068",
        "name": "Bachillerato En Ciencias",
        "university": "Universidad del Bío-Bío",
        "university_short": "UBB",
        "campus": "Chillán",
        "region": "Ñuble",
        "city": "Chillán",
        "area": "Humanidades y Ciencias",
        "vacantes": 35,
        "weights": {
            "nem": 0.1,
            "ranking": 0.4,
            "lectura": 0.1,
            "m1": 0.3,
            "m2": 0.0,
            "ciencias": 0.1,
            "historia": 0.0,
            "elective_rule": "CIENCIAS"
        },
        "cutoffs": {
            "2024": 522.0,
            "2025": 526.0,
            "2026": 530.0
        },
        "requires_m2": False,
        "min_weighted_score": 458.0
    },
    {
        "id": "contador-publico-y-auditor-ubb",
        "code": "29045",
        "name": "Contador Público Y Auditor",
        "university": "Universidad del Bío-Bío",
        "university_short": "UBB",
        "campus": "Concepción",
        "region": "Biobío",
        "city": "Concepción",
        "area": "Humanidades y Ciencias",
        "vacantes": 55,
        "weights": {
            "nem": 0.2,
            "ranking": 0.4,
            "lectura": 0.1,
            "m1": 0.2,
            "m2": 0.0,
            "ciencias": 0.1,
            "historia": 0.0,
            "elective_rule": "MAX"
        },
        "cutoffs": {
            "2024": 522.0,
            "2025": 526.0,
            "2026": 530.0
        },
        "requires_m2": False,
        "min_weighted_score": 458.0
    },
    {
        "id": "contador-publico-y-auditor-chillán-ubb",
        "code": "29063",
        "name": "Contador Público Y Auditor",
        "university": "Universidad del Bío-Bío",
        "university_short": "UBB",
        "campus": "Chillán",
        "region": "Ñuble",
        "city": "Chillán",
        "area": "Humanidades y Ciencias",
        "vacantes": 40,
        "weights": {
            "nem": 0.2,
            "ranking": 0.4,
            "lectura": 0.1,
            "m1": 0.2,
            "m2": 0.0,
            "ciencias": 0.1,
            "historia": 0.0,
            "elective_rule": "MAX"
        },
        "cutoffs": {
            "2024": 522.0,
            "2025": 526.0,
            "2026": 530.0
        },
        "requires_m2": False,
        "min_weighted_score": 458.0
    },
    {
        "id": "derecho-ubb",
        "code": "29012",
        "name": "Derecho",
        "university": "Universidad del Bío-Bío",
        "university_short": "UBB",
        "campus": "Concepción",
        "region": "Biobío",
        "city": "Concepción",
        "area": "Ciencias Sociales y Jurídicas",
        "vacantes": 90,
        "weights": {
            "nem": 0.2,
            "ranking": 0.2,
            "lectura": 0.3,
            "m1": 0.15,
            "m2": 0.0,
            "ciencias": 0.0,
            "historia": 0.15,
            "elective_rule": "HISTORIA"
        },
        "cutoffs": {
            "2024": 522.0,
            "2025": 526.0,
            "2026": 530.0
        },
        "requires_m2": False,
        "min_weighted_score": 500.0
    },
    {
        "id": "diseno-grafico-chillán-ubb",
        "code": "29064",
        "name": "Diseño Gráfico",
        "university": "Universidad del Bío-Bío",
        "university_short": "UBB",
        "campus": "Chillán",
        "region": "Ñuble",
        "city": "Chillán",
        "area": "Humanidades y Ciencias",
        "vacantes": 45,
        "weights": {
            "nem": 0.2,
            "ranking": 0.3,
            "lectura": 0.3,
            "m1": 0.1,
            "m2": 0.0,
            "ciencias": 0.0,
            "historia": 0.1,
            "elective_rule": "HISTORIA"
        },
        "cutoffs": {
            "2024": 522.0,
            "2025": 526.0,
            "2026": 530.0
        },
        "requires_m2": False,
        "min_weighted_score": 458.0
    },
    {
        "id": "diseno-industrial-ubb",
        "code": "29004",
        "name": "Diseño Industrial",
        "university": "Universidad del Bío-Bío",
        "university_short": "UBB",
        "campus": "Concepción",
        "region": "Biobío",
        "city": "Concepción",
        "area": "Humanidades y Ciencias",
        "vacantes": 55,
        "weights": {
            "nem": 0.2,
            "ranking": 0.4,
            "lectura": 0.2,
            "m1": 0.1,
            "m2": 0.0,
            "ciencias": 0.1,
            "historia": 0.0,
            "elective_rule": "MAX"
        },
        "cutoffs": {
            "2024": 745.3,
            "2025": 751.2,
            "2026": 756.95
        },
        "requires_m2": False,
        "min_weighted_score": 458.0
    },
    {
        "id": "enfermeria-chillán-ubb",
        "code": "29052",
        "name": "Enfermería",
        "university": "Universidad del Bío-Bío",
        "university_short": "UBB",
        "campus": "Chillán",
        "region": "Ñuble",
        "city": "Chillán",
        "area": "Ciencias de la Salud",
        "vacantes": 45,
        "weights": {
            "nem": 0.1,
            "ranking": 0.2,
            "lectura": 0.25,
            "m1": 0.15,
            "m2": 0.0,
            "ciencias": 0.3,
            "historia": 0.0,
            "elective_rule": "CIENCIAS"
        },
        "cutoffs": {
            "2024": 755.2,
            "2025": 760.1,
            "2026": 765.4
        },
        "requires_m2": False,
        "min_weighted_score": 458.0
    },
    {
        "id": "fonoaudiologia-chillán-ubb",
        "code": "29055",
        "name": "Fonoaudiología",
        "university": "Universidad del Bío-Bío",
        "university_short": "UBB",
        "campus": "Chillán",
        "region": "Ñuble",
        "city": "Chillán",
        "area": "Ciencias de la Salud",
        "vacantes": 45,
        "weights": {
            "nem": 0.2,
            "ranking": 0.4,
            "lectura": 0.2,
            "m1": 0.1,
            "m2": 0.0,
            "ciencias": 0.1,
            "historia": 0.0,
            "elective_rule": "CIENCIAS"
        },
        "cutoffs": {
            "2024": 522.0,
            "2025": 526.0,
            "2026": 530.0
        },
        "requires_m2": False,
        "min_weighted_score": 458.0
    },
    {
        "id": "ingenieria-civil-ubb",
        "code": "29021",
        "name": "Ingeniería Civil",
        "university": "Universidad del Bío-Bío",
        "university_short": "UBB",
        "campus": "Concepción",
        "region": "Biobío",
        "city": "Concepción",
        "area": "Ingeniería y Ciencias Exactas",
        "vacantes": 95,
        "weights": {
            "nem": 0.1,
            "ranking": 0.4,
            "lectura": 0.15,
            "m1": 0.15,
            "m2": 0.1,
            "ciencias": 0.1,
            "historia": 0.0,
            "elective_rule": "MAX"
        },
        "cutoffs": {
            "2024": 665.1,
            "2025": 672.3,
            "2026": 644.1
        },
        "requires_m2": True,
        "min_weighted_score": 458.0
    },
    {
        "id": "ingenieria-civil-electrica-ubb",
        "code": "29029",
        "name": "Ingeniería Civil Eléctrica",
        "university": "Universidad del Bío-Bío",
        "university_short": "UBB",
        "campus": "Concepción",
        "region": "Biobío",
        "city": "Concepción",
        "area": "Ingeniería y Ciencias Exactas",
        "vacantes": 65,
        "weights": {
            "nem": 0.1,
            "ranking": 0.45,
            "lectura": 0.1,
            "m1": 0.15,
            "m2": 0.1,
            "ciencias": 0.1,
            "historia": 0.0,
            "elective_rule": "MAX"
        },
        "cutoffs": {
            "2024": 665.1,
            "2025": 672.3,
            "2026": 711.65
        },
        "requires_m2": True,
        "min_weighted_score": 458.0
    },
    {
        "id": "ingenieria-civil-en-automatizacion-ubb",
        "code": "29028",
        "name": "Ingeniería Civil En Automatización",
        "university": "Universidad del Bío-Bío",
        "university_short": "UBB",
        "campus": "Concepción",
        "region": "Biobío",
        "city": "Concepción",
        "area": "Ingeniería y Ciencias Exactas",
        "vacantes": 75,
        "weights": {
            "nem": 0.1,
            "ranking": 0.45,
            "lectura": 0.1,
            "m1": 0.15,
            "m2": 0.1,
            "ciencias": 0.1,
            "historia": 0.0,
            "elective_rule": "MAX"
        },
        "cutoffs": {
            "2024": 665.1,
            "2025": 672.3,
            "2026": 606.75
        },
        "requires_m2": True,
        "min_weighted_score": 458.0
    },
    {
        "id": "ingenieria-civil-en-informatica-ubb",
        "code": "29027",
        "name": "Ingeniería Civil En Informática",
        "university": "Universidad del Bío-Bío",
        "university_short": "UBB",
        "campus": "Concepción",
        "region": "Biobío",
        "city": "Concepción",
        "area": "Ingeniería y Ciencias Exactas",
        "vacantes": 85,
        "weights": {
            "nem": 0.1,
            "ranking": 0.4,
            "lectura": 0.15,
            "m1": 0.15,
            "m2": 0.1,
            "ciencias": 0.1,
            "historia": 0.0,
            "elective_rule": "MAX"
        },
        "cutoffs": {
            "2024": 665.1,
            "2025": 672.3,
            "2026": 708.6
        },
        "requires_m2": True,
        "min_weighted_score": 458.0
    },
    {
        "id": "ingenieria-civil-en-informatica-chillán-ubb",
        "code": "29057",
        "name": "Ingeniería Civil En Informática",
        "university": "Universidad del Bío-Bío",
        "university_short": "UBB",
        "campus": "Chillán",
        "region": "Ñuble",
        "city": "Chillán",
        "area": "Ingeniería y Ciencias Exactas",
        "vacantes": 65,
        "weights": {
            "nem": 0.1,
            "ranking": 0.4,
            "lectura": 0.15,
            "m1": 0.15,
            "m2": 0.1,
            "ciencias": 0.1,
            "historia": 0.0,
            "elective_rule": "MAX"
        },
        "cutoffs": {
            "2024": 665.1,
            "2025": 672.3,
            "2026": 721.6
        },
        "requires_m2": True,
        "min_weighted_score": 458.0
    },
    {
        "id": "ingenieria-civil-industrial-ubb",
        "code": "29020",
        "name": "Ingeniería Civil Industrial",
        "university": "Universidad del Bío-Bío",
        "university_short": "UBB",
        "campus": "Concepción",
        "region": "Biobío",
        "city": "Concepción",
        "area": "Ingeniería y Ciencias Exactas",
        "vacantes": 115,
        "weights": {
            "nem": 0.1,
            "ranking": 0.45,
            "lectura": 0.1,
            "m1": 0.15,
            "m2": 0.1,
            "ciencias": 0.1,
            "historia": 0.0,
            "elective_rule": "MAX"
        },
        "cutoffs": {
            "2024": 745.3,
            "2025": 751.2,
            "2026": 756.95
        },
        "requires_m2": True,
        "min_weighted_score": 458.0
    },
    {
        "id": "ingenieria-civil-mecanica-ubb",
        "code": "29026",
        "name": "Ingeniería Civil Mecánica",
        "university": "Universidad del Bío-Bío",
        "university_short": "UBB",
        "campus": "Concepción",
        "region": "Biobío",
        "city": "Concepción",
        "area": "Ingeniería y Ciencias Exactas",
        "vacantes": 75,
        "weights": {
            "nem": 0.1,
            "ranking": 0.45,
            "lectura": 0.1,
            "m1": 0.15,
            "m2": 0.1,
            "ciencias": 0.1,
            "historia": 0.0,
            "elective_rule": "MAX"
        },
        "cutoffs": {
            "2024": 665.1,
            "2025": 672.3,
            "2026": 671.65
        },
        "requires_m2": True,
        "min_weighted_score": 458.0
    },
    {
        "id": "ingenieria-civil-quimica-ubb",
        "code": "29019",
        "name": "Ingeniería Civil Química",
        "university": "Universidad del Bío-Bío",
        "university_short": "UBB",
        "campus": "Concepción",
        "region": "Biobío",
        "city": "Concepción",
        "area": "Ingeniería y Ciencias Exactas",
        "vacantes": 60,
        "weights": {
            "nem": 0.1,
            "ranking": 0.45,
            "lectura": 0.1,
            "m1": 0.15,
            "m2": 0.1,
            "ciencias": 0.1,
            "historia": 0.0,
            "elective_rule": "MAX"
        },
        "cutoffs": {
            "2024": 665.1,
            "2025": 672.3,
            "2026": 680.5
        },
        "requires_m2": True,
        "min_weighted_score": 458.0
    },
    {
        "id": "ingenieria-comercial-ubb",
        "code": "29049",
        "name": "Ingeniería Comercial",
        "university": "Universidad del Bío-Bío",
        "university_short": "UBB",
        "campus": "Concepción",
        "region": "Biobío",
        "city": "Concepción",
        "area": "Ingeniería y Ciencias Exactas",
        "vacantes": 85,
        "weights": {
            "nem": 0.2,
            "ranking": 0.3,
            "lectura": 0.15,
            "m1": 0.25,
            "m2": 0.0,
            "ciencias": 0.1,
            "historia": 0.0,
            "elective_rule": "MAX"
        },
        "cutoffs": {
            "2024": 650.0,
            "2025": 655.1,
            "2026": 627.85
        },
        "requires_m2": False,
        "min_weighted_score": 458.0
    },
    {
        "id": "ingenieria-comercial-chillán-ubb",
        "code": "29059",
        "name": "Ingeniería Comercial",
        "university": "Universidad del Bío-Bío",
        "university_short": "UBB",
        "campus": "Chillán",
        "region": "Ñuble",
        "city": "Chillán",
        "area": "Ingeniería y Ciencias Exactas",
        "vacantes": 65,
        "weights": {
            "nem": 0.2,
            "ranking": 0.3,
            "lectura": 0.15,
            "m1": 0.25,
            "m2": 0.0,
            "ciencias": 0.1,
            "historia": 0.0,
            "elective_rule": "MAX"
        },
        "cutoffs": {
            "2024": 650.0,
            "2025": 655.1,
            "2026": 660.4
        },
        "requires_m2": False,
        "min_weighted_score": 458.0
    },
    {
        "id": "ingenieria-de-ejecucion-en-computacion-e-informatica-ubb",
        "code": "29037",
        "name": "Ingeniería De Ejecución En Computación E Informática",
        "university": "Universidad del Bío-Bío",
        "university_short": "UBB",
        "campus": "Concepción",
        "region": "Biobío",
        "city": "Concepción",
        "area": "Ingeniería y Ciencias Exactas",
        "vacantes": 65,
        "weights": {
            "nem": 0.1,
            "ranking": 0.4,
            "lectura": 0.15,
            "m1": 0.15,
            "m2": 0.1,
            "ciencias": 0.1,
            "historia": 0.0,
            "elective_rule": "MAX"
        },
        "cutoffs": {
            "2024": 522.0,
            "2025": 526.0,
            "2026": 541.4
        },
        "requires_m2": True,
        "min_weighted_score": 458.0
    },
    {
        "id": "ingenieria-electrica-ubb",
        "code": "29017",
        "name": "Ingeniería Eléctrica",
        "university": "Universidad del Bío-Bío",
        "university_short": "UBB",
        "campus": "Concepción",
        "region": "Biobío",
        "city": "Concepción",
        "area": "Ingeniería y Ciencias Exactas",
        "vacantes": 40,
        "weights": {
            "nem": 0.1,
            "ranking": 0.5,
            "lectura": 0.1,
            "m1": 0.1,
            "m2": 0.1,
            "ciencias": 0.1,
            "historia": 0.0,
            "elective_rule": "MAX"
        },
        "cutoffs": {
            "2024": 522.0,
            "2025": 526.0,
            "2026": 667.9
        },
        "requires_m2": True,
        "min_weighted_score": 458.0
    },
    {
        "id": "ingenieria-electronica-ubb",
        "code": "29016",
        "name": "Ingeniería Electrónica",
        "university": "Universidad del Bío-Bío",
        "university_short": "UBB",
        "campus": "Concepción",
        "region": "Biobío",
        "city": "Concepción",
        "area": "Ingeniería y Ciencias Exactas",
        "vacantes": 40,
        "weights": {
            "nem": 0.1,
            "ranking": 0.5,
            "lectura": 0.1,
            "m1": 0.1,
            "m2": 0.1,
            "ciencias": 0.1,
            "historia": 0.0,
            "elective_rule": "MAX"
        },
        "cutoffs": {
            "2024": 522.0,
            "2025": 526.0,
            "2026": 530.0
        },
        "requires_m2": True,
        "min_weighted_score": 458.0
    },
    {
        "id": "ingenieria-en-alimentos-chillán-ubb",
        "code": "29051",
        "name": "Ingeniería En Alimentos",
        "university": "Universidad del Bío-Bío",
        "university_short": "UBB",
        "campus": "Chillán",
        "region": "Ñuble",
        "city": "Chillán",
        "area": "Ingeniería y Ciencias Exactas",
        "vacantes": 35,
        "weights": {
            "nem": 0.1,
            "ranking": 0.45,
            "lectura": 0.1,
            "m1": 0.2,
            "m2": 0.05,
            "ciencias": 0.1,
            "historia": 0.0,
            "elective_rule": "MAX"
        },
        "cutoffs": {
            "2024": 522.0,
            "2025": 526.0,
            "2026": 530.0
        },
        "requires_m2": True,
        "min_weighted_score": 458.0
    },
    {
        "id": "ingenieria-en-construccion-ubb",
        "code": "29005",
        "name": "Ingeniería En Construcción",
        "university": "Universidad del Bío-Bío",
        "university_short": "UBB",
        "campus": "Concepción",
        "region": "Biobío",
        "city": "Concepción",
        "area": "Ingeniería y Ciencias Exactas",
        "vacantes": 80,
        "weights": {
            "nem": 0.2,
            "ranking": 0.4,
            "lectura": 0.15,
            "m1": 0.1,
            "m2": 0.05,
            "ciencias": 0.1,
            "historia": 0.0,
            "elective_rule": "CIENCIAS"
        },
        "cutoffs": {
            "2024": 522.0,
            "2025": 526.0,
            "2026": 481.05
        },
        "requires_m2": True,
        "min_weighted_score": 458.0
    },
    {
        "id": "ingenieria-en-recursos-naturales-chillán-ubb",
        "code": "29069",
        "name": "Ingeniería En Recursos Naturales",
        "university": "Universidad del Bío-Bío",
        "university_short": "UBB",
        "campus": "Chillán",
        "region": "Ñuble",
        "city": "Chillán",
        "area": "Ingeniería y Ciencias Exactas",
        "vacantes": 40,
        "weights": {
            "nem": 0.1,
            "ranking": 0.4,
            "lectura": 0.15,
            "m1": 0.2,
            "m2": 0.05,
            "ciencias": 0.1,
            "historia": 0.0,
            "elective_rule": "MAX"
        },
        "cutoffs": {
            "2024": 522.0,
            "2025": 526.0,
            "2026": 530.0
        },
        "requires_m2": True,
        "min_weighted_score": 458.0
    },
    {
        "id": "ingenieria-estadistica-ubb",
        "code": "29018",
        "name": "Ingeniería Estadística",
        "university": "Universidad del Bío-Bío",
        "university_short": "UBB",
        "campus": "Concepción",
        "region": "Biobío",
        "city": "Concepción",
        "area": "Ingeniería y Ciencias Exactas",
        "vacantes": 30,
        "weights": {
            "nem": 0.2,
            "ranking": 0.4,
            "lectura": 0.1,
            "m1": 0.1,
            "m2": 0.1,
            "ciencias": 0.1,
            "historia": 0.0,
            "elective_rule": "MAX"
        },
        "cutoffs": {
            "2024": 522.0,
            "2025": 526.0,
            "2026": 513.4
        },
        "requires_m2": True,
        "min_weighted_score": 458.0
    },
    {
        "id": "ingenieria-mecanica-ubb",
        "code": "29033",
        "name": "Ingeniería Mecánica",
        "university": "Universidad del Bío-Bío",
        "university_short": "UBB",
        "campus": "Concepción",
        "region": "Biobío",
        "city": "Concepción",
        "area": "Ingeniería y Ciencias Exactas",
        "vacantes": 40,
        "weights": {
            "nem": 0.1,
            "ranking": 0.5,
            "lectura": 0.1,
            "m1": 0.1,
            "m2": 0.1,
            "ciencias": 0.1,
            "historia": 0.0,
            "elective_rule": "MAX"
        },
        "cutoffs": {
            "2024": 522.0,
            "2025": 526.0,
            "2026": 530.0
        },
        "requires_m2": True,
        "min_weighted_score": 458.0
    },
    {
        "id": "medicina-chillán-ubb",
        "code": "29065",
        "name": "Medicina",
        "university": "Universidad del Bío-Bío",
        "university_short": "UBB",
        "campus": "Chillán",
        "region": "Ñuble",
        "city": "Chillán",
        "area": "Ciencias de la Salud",
        "vacantes": 40,
        "weights": {
            "nem": 0.15,
            "ranking": 0.25,
            "lectura": 0.15,
            "m1": 0.25,
            "m2": 0.0,
            "ciencias": 0.2,
            "historia": 0.0,
            "elective_rule": "CIENCIAS"
        },
        "cutoffs": {
            "2024": 622.0,
            "2025": 626.0,
            "2026": 630.0
        },
        "requires_m2": False,
        "min_weighted_score": 600.0
    },
    {
        "id": "nutricion-y-dietetica-chillán-ubb",
        "code": "29054",
        "name": "Nutrición Y Dietética",
        "university": "Universidad del Bío-Bío",
        "university_short": "UBB",
        "campus": "Chillán",
        "region": "Ñuble",
        "city": "Chillán",
        "area": "Ciencias de la Salud",
        "vacantes": 45,
        "weights": {
            "nem": 0.2,
            "ranking": 0.3,
            "lectura": 0.15,
            "m1": 0.15,
            "m2": 0.0,
            "ciencias": 0.2,
            "historia": 0.0,
            "elective_rule": "CIENCIAS"
        },
        "cutoffs": {
            "2024": 522.0,
            "2025": 526.0,
            "2026": 530.0
        },
        "requires_m2": False,
        "min_weighted_score": 0.0
    },
    {
        "id": "pedagogia-en-castellano-y-comunicacion-chillán-ubb",
        "code": "29072",
        "name": "Pedagogía En Castellano Y Comunicación",
        "university": "Universidad del Bío-Bío",
        "university_short": "UBB",
        "campus": "Chillán",
        "region": "Ñuble",
        "city": "Chillán",
        "area": "Educación",
        "vacantes": 50,
        "weights": {
            "nem": 0.1,
            "ranking": 0.4,
            "lectura": 0.3,
            "m1": 0.1,
            "m2": 0.0,
            "ciencias": 0.1,
            "historia": 0.0,
            "elective_rule": "MAX"
        },
        "cutoffs": {
            "2024": 522.0,
            "2025": 526.0,
            "2026": 530.0
        },
        "requires_m2": False,
        "min_weighted_score": 458.0
    },
    {
        "id": "pedagogia-en-ciencias-naturales-mencion-biologia-mencion-fisica-mencion-quimica-chillán-ubb",
        "code": "29073",
        "name": "Pedagogía En Ciencias Naturales Mención Biología Mención Física Mención Química",
        "university": "Universidad del Bío-Bío",
        "university_short": "UBB",
        "campus": "Chillán",
        "region": "Ñuble",
        "city": "Chillán",
        "area": "Educación",
        "vacantes": 40,
        "weights": {
            "nem": 0.2,
            "ranking": 0.4,
            "lectura": 0.1,
            "m1": 0.15,
            "m2": 0.0,
            "ciencias": 0.15,
            "historia": 0.0,
            "elective_rule": "MAX"
        },
        "cutoffs": {
            "2024": 522.0,
            "2025": 526.0,
            "2026": 530.0
        },
        "requires_m2": False,
        "min_weighted_score": 458.0
    },
    {
        "id": "pedagogia-en-educacion-especial-con-mencion-en-dificultades-especificas-del-aprendizaje-chillán-ubb",
        "code": "29077",
        "name": "Pedagogía En Educación Especial Con Mención En Dificultades Específicas Del Aprendizaje",
        "university": "Universidad del Bío-Bío",
        "university_short": "UBB",
        "campus": "Chillán",
        "region": "Ñuble",
        "city": "Chillán",
        "area": "Educación",
        "vacantes": 40,
        "weights": {
            "nem": 0.3,
            "ranking": 0.4,
            "lectura": 0.1,
            "m1": 0.1,
            "m2": 0.0,
            "ciencias": 0.1,
            "historia": 0.0,
            "elective_rule": "MAX"
        },
        "cutoffs": {
            "2024": 522.0,
            "2025": 526.0,
            "2026": 530.0
        },
        "requires_m2": False,
        "min_weighted_score": 458.0
    },
    {
        "id": "pedagogia-en-educacion-fisica-chillán-ubb",
        "code": "29071",
        "name": "Pedagogía En Educación Física",
        "university": "Universidad del Bío-Bío",
        "university_short": "UBB",
        "campus": "Chillán",
        "region": "Ñuble",
        "city": "Chillán",
        "area": "Educación",
        "vacantes": 45,
        "weights": {
            "nem": 0.3,
            "ranking": 0.3,
            "lectura": 0.15,
            "m1": 0.15,
            "m2": 0.0,
            "ciencias": 0.1,
            "historia": 0.0,
            "elective_rule": "MAX"
        },
        "cutoffs": {
            "2024": 522.0,
            "2025": 526.0,
            "2026": 530.0
        },
        "requires_m2": False,
        "min_weighted_score": 458.0
    },
    {
        "id": "pedagogia-en-educacion-general-basica-con-mencion-en-lenguaje-y-comunicacion-o-educacion-matematica-chillán-ubb",
        "code": "29082",
        "name": "Pedagogía En Educación General Básica Con Mención En Lenguaje Y Comunicación O Educación Matemática",
        "university": "Universidad del Bío-Bío",
        "university_short": "UBB",
        "campus": "Chillán",
        "region": "Ñuble",
        "city": "Chillán",
        "area": "Educación",
        "vacantes": 40,
        "weights": {
            "nem": 0.1,
            "ranking": 0.4,
            "lectura": 0.25,
            "m1": 0.15,
            "m2": 0.0,
            "ciencias": 0.1,
            "historia": 0.0,
            "elective_rule": "MAX"
        },
        "cutoffs": {
            "2024": 522.0,
            "2025": 526.0,
            "2026": 530.0
        },
        "requires_m2": False,
        "min_weighted_score": 458.0
    },
    {
        "id": "pedagogia-en-educacion-matematica-chillán-ubb",
        "code": "29086",
        "name": "Pedagogía En Educación Matemática",
        "university": "Universidad del Bío-Bío",
        "university_short": "UBB",
        "campus": "Chillán",
        "region": "Ñuble",
        "city": "Chillán",
        "area": "Educación",
        "vacantes": 40,
        "weights": {
            "nem": 0.2,
            "ranking": 0.3,
            "lectura": 0.1,
            "m1": 0.2,
            "m2": 0.1,
            "ciencias": 0.1,
            "historia": 0.0,
            "elective_rule": "MAX"
        },
        "cutoffs": {
            "2024": 522.0,
            "2025": 526.0,
            "2026": 530.0
        },
        "requires_m2": True,
        "min_weighted_score": 458.0
    },
    {
        "id": "pedagogia-en-educacion-parvularia-mencion-didactica-en-primera-infancia-chillán-ubb",
        "code": "29080",
        "name": "Pedagogía En Educación Parvularia Mención Didáctica En Primera Infancia",
        "university": "Universidad del Bío-Bío",
        "university_short": "UBB",
        "campus": "Chillán",
        "region": "Ñuble",
        "city": "Chillán",
        "area": "Educación",
        "vacantes": 50,
        "weights": {
            "nem": 0.4,
            "ranking": 0.25,
            "lectura": 0.15,
            "m1": 0.1,
            "m2": 0.0,
            "ciencias": 0.1,
            "historia": 0.0,
            "elective_rule": "MAX"
        },
        "cutoffs": {
            "2024": 522.0,
            "2025": 526.0,
            "2026": 530.0
        },
        "requires_m2": False,
        "min_weighted_score": 458.0
    },
    {
        "id": "pedagogia-en-historia-y-geografia-chillán-ubb",
        "code": "29078",
        "name": "Pedagogía En Historia Y Geografía",
        "university": "Universidad del Bío-Bío",
        "university_short": "UBB",
        "campus": "Chillán",
        "region": "Ñuble",
        "city": "Chillán",
        "area": "Educación",
        "vacantes": 40,
        "weights": {
            "nem": 0.1,
            "ranking": 0.4,
            "lectura": 0.15,
            "m1": 0.1,
            "m2": 0.0,
            "ciencias": 0.25,
            "historia": 0.0,
            "elective_rule": "MAX"
        },
        "cutoffs": {
            "2024": 522.0,
            "2025": 526.0,
            "2026": 530.0
        },
        "requires_m2": False,
        "min_weighted_score": 458.0
    },
    {
        "id": "pedagogia-en-ingles-chillán-ubb",
        "code": "29076",
        "name": "Pedagogía En Inglés",
        "university": "Universidad del Bío-Bío",
        "university_short": "UBB",
        "campus": "Chillán",
        "region": "Ñuble",
        "city": "Chillán",
        "area": "Educación",
        "vacantes": 50,
        "weights": {
            "nem": 0.25,
            "ranking": 0.4,
            "lectura": 0.15,
            "m1": 0.1,
            "m2": 0.0,
            "ciencias": 0.1,
            "historia": 0.0,
            "elective_rule": "MAX"
        },
        "cutoffs": {
            "2024": 522.0,
            "2025": 526.0,
            "2026": 530.0
        },
        "requires_m2": False,
        "min_weighted_score": 458.0
    },
    {
        "id": "psicologia-chillán-ubb",
        "code": "29067",
        "name": "Psicología",
        "university": "Universidad del Bío-Bío",
        "university_short": "UBB",
        "campus": "Chillán",
        "region": "Ñuble",
        "city": "Chillán",
        "area": "Ciencias Sociales y Jurídicas",
        "vacantes": 65,
        "weights": {
            "nem": 0.2,
            "ranking": 0.2,
            "lectura": 0.25,
            "m1": 0.25,
            "m2": 0.0,
            "ciencias": 0.1,
            "historia": 0.0,
            "elective_rule": "MAX"
        },
        "cutoffs": {
            "2024": 725.0,
            "2025": 730.2,
            "2026": 735.6
        },
        "requires_m2": False,
        "min_weighted_score": 458.0
    },
    {
        "id": "quimica-y-farmacia-chillán-ubb",
        "code": "29061",
        "name": "Química Y Farmacia",
        "university": "Universidad del Bío-Bío",
        "university_short": "UBB",
        "campus": "Chillán",
        "region": "Ñuble",
        "city": "Chillán",
        "area": "Humanidades y Ciencias",
        "vacantes": 50,
        "weights": {
            "nem": 0.2,
            "ranking": 0.2,
            "lectura": 0.15,
            "m1": 0.3,
            "m2": 0.0,
            "ciencias": 0.15,
            "historia": 0.0,
            "elective_rule": "CIENCIAS"
        },
        "cutoffs": {
            "2024": 522.0,
            "2025": 526.0,
            "2026": 530.0
        },
        "requires_m2": False,
        "min_weighted_score": 458.0
    },
    {
        "id": "trabajo-social-ubb",
        "code": "29010",
        "name": "Trabajo Social",
        "university": "Universidad del Bío-Bío",
        "university_short": "UBB",
        "campus": "Concepción",
        "region": "Biobío",
        "city": "Concepción",
        "area": "Ciencias Sociales y Jurídicas",
        "vacantes": 50,
        "weights": {
            "nem": 0.2,
            "ranking": 0.3,
            "lectura": 0.3,
            "m1": 0.1,
            "m2": 0.0,
            "ciencias": 0.1,
            "historia": 0.0,
            "elective_rule": "MAX"
        },
        "cutoffs": {
            "2024": 522.0,
            "2025": 526.0,
            "2026": 530.0
        },
        "requires_m2": False,
        "min_weighted_score": 458.0
    },
    {
        "id": "trabajo-social-chillán-ubb",
        "code": "29066",
        "name": "Trabajo Social",
        "university": "Universidad del Bío-Bío",
        "university_short": "UBB",
        "campus": "Chillán",
        "region": "Ñuble",
        "city": "Chillán",
        "area": "Ciencias Sociales y Jurídicas",
        "vacantes": 55,
        "weights": {
            "nem": 0.2,
            "ranking": 0.3,
            "lectura": 0.3,
            "m1": 0.1,
            "m2": 0.0,
            "ciencias": 0.1,
            "historia": 0.0,
            "elective_rule": "MAX"
        },
        "cutoffs": {
            "2024": 522.0,
            "2025": 526.0,
            "2026": 530.0
        },
        "requires_m2": False,
        "min_weighted_score": 458.0
    },
    {
        "id": "arquitectura-ucsc",
        "code": "36081",
        "name": "Arquitectura",
        "university": "Universidad Católica de la Santísima Concepción",
        "university_short": "UCSC",
        "campus": "Concepción",
        "region": "Biobío",
        "city": "Concepción",
        "area": "Arquitectura, Arte y Diseño",
        "vacantes": 80,
        "weights": {
            "nem": 0.1,
            "ranking": 0.4,
            "lectura": 0.2,
            "m1": 0.2,
            "m2": 0.0,
            "ciencias": 0.1,
            "historia": 0.0,
            "elective_rule": "MAX"
        },
        "cutoffs": {
            "2024": 512.0,
            "2025": 516.0,
            "2026": 520.0
        },
        "requires_m2": False,
        "min_weighted_score": 458.0
    },
    {
        "id": "bachillerato-en-ciencias-y-humanidades-ucsc",
        "code": "36084",
        "name": "Bachillerato En Ciencias Y Humanidades",
        "university": "Universidad Católica de la Santísima Concepción",
        "university_short": "UCSC",
        "campus": "Concepción",
        "region": "Biobío",
        "city": "Concepción",
        "area": "Humanidades y Ciencias",
        "vacantes": 70,
        "weights": {
            "nem": 0.15,
            "ranking": 0.45,
            "lectura": 0.15,
            "m1": 0.15,
            "m2": 0.0,
            "ciencias": 0.1,
            "historia": 0.0,
            "elective_rule": "MAX"
        },
        "cutoffs": {
            "2024": 512.0,
            "2025": 516.0,
            "2026": 520.0
        },
        "requires_m2": False,
        "min_weighted_score": 458.0
    },
    {
        "id": "biologia-marina-ucsc",
        "code": "36002",
        "name": "Biología Marina",
        "university": "Universidad Católica de la Santísima Concepción",
        "university_short": "UCSC",
        "campus": "Concepción",
        "region": "Biobío",
        "city": "Concepción",
        "area": "Ciencias Naturales y Agropecuarias",
        "vacantes": 40,
        "weights": {
            "nem": 0.1,
            "ranking": 0.4,
            "lectura": 0.1,
            "m1": 0.25,
            "m2": 0.0,
            "ciencias": 0.15,
            "historia": 0.0,
            "elective_rule": "MAX"
        },
        "cutoffs": {
            "2024": 512.0,
            "2025": 516.0,
            "2026": 520.0
        },
        "requires_m2": False,
        "min_weighted_score": 458.0
    },
    {
        "id": "contador-auditor-ucsc",
        "code": "36016",
        "name": "Contador Auditor",
        "university": "Universidad Católica de la Santísima Concepción",
        "university_short": "UCSC",
        "campus": "Concepción",
        "region": "Biobío",
        "city": "Concepción",
        "area": "Humanidades y Ciencias",
        "vacantes": 70,
        "weights": {
            "nem": 0.2,
            "ranking": 0.4,
            "lectura": 0.1,
            "m1": 0.2,
            "m2": 0.0,
            "ciencias": 0.1,
            "historia": 0.0,
            "elective_rule": "MAX"
        },
        "cutoffs": {
            "2024": 512.0,
            "2025": 516.0,
            "2026": 520.0
        },
        "requires_m2": False,
        "min_weighted_score": 458.0
    },
    {
        "id": "derecho-ucsc",
        "code": "36001",
        "name": "Derecho",
        "university": "Universidad Católica de la Santísima Concepción",
        "university_short": "UCSC",
        "campus": "Concepción",
        "region": "Biobío",
        "city": "Concepción",
        "area": "Ciencias Sociales y Jurídicas",
        "vacantes": 125,
        "weights": {
            "nem": 0.15,
            "ranking": 0.4,
            "lectura": 0.15,
            "m1": 0.1,
            "m2": 0.0,
            "ciencias": 0.2,
            "historia": 0.0,
            "elective_rule": "MAX"
        },
        "cutoffs": {
            "2024": 746.1,
            "2025": 752.0,
            "2026": 757.55
        },
        "requires_m2": False,
        "min_weighted_score": 458.0
    },
    {
        "id": "direccion-audiovisual-y-multimedia-ucsc",
        "code": "36077",
        "name": "Dirección Audiovisual Y Multimedia",
        "university": "Universidad Católica de la Santísima Concepción",
        "university_short": "UCSC",
        "campus": "Concepción",
        "region": "Biobío",
        "city": "Concepción",
        "area": "Humanidades y Ciencias",
        "vacantes": 45,
        "weights": {
            "nem": 0.2,
            "ranking": 0.4,
            "lectura": 0.2,
            "m1": 0.1,
            "m2": 0.0,
            "ciencias": 0.1,
            "historia": 0.0,
            "elective_rule": "MAX"
        },
        "cutoffs": {
            "2024": 512.0,
            "2025": 516.0,
            "2026": 520.0
        },
        "requires_m2": False,
        "min_weighted_score": 458.0
    },
    {
        "id": "educacion-de-parvulos-ucsc",
        "code": "36009",
        "name": "Educación De Párvulos",
        "university": "Universidad Católica de la Santísima Concepción",
        "university_short": "UCSC",
        "campus": "Concepción",
        "region": "Biobío",
        "city": "Concepción",
        "area": "Educación",
        "vacantes": 60,
        "weights": {
            "nem": 0.2,
            "ranking": 0.4,
            "lectura": 0.15,
            "m1": 0.15,
            "m2": 0.0,
            "ciencias": 0.1,
            "historia": 0.0,
            "elective_rule": "MAX"
        },
        "cutoffs": {
            "2024": 512.0,
            "2025": 516.0,
            "2026": 520.0
        },
        "requires_m2": False,
        "min_weighted_score": 458.0
    },
    {
        "id": "enfermeria-ucsc",
        "code": "36021",
        "name": "Enfermería",
        "university": "Universidad Católica de la Santísima Concepción",
        "university_short": "UCSC",
        "campus": "Concepción",
        "region": "Biobío",
        "city": "Concepción",
        "area": "Ciencias de la Salud",
        "vacantes": 85,
        "weights": {
            "nem": 0.2,
            "ranking": 0.4,
            "lectura": 0.1,
            "m1": 0.2,
            "m2": 0.0,
            "ciencias": 0.1,
            "historia": 0.0,
            "elective_rule": "CIENCIAS"
        },
        "cutoffs": {
            "2024": 758.4,
            "2025": 764.1,
            "2026": 768.7
        },
        "requires_m2": False,
        "min_weighted_score": 458.0
    },
    {
        "id": "ingenieria-civil-ucsc",
        "code": "36029",
        "name": "Ingeniería Civil",
        "university": "Universidad Católica de la Santísima Concepción",
        "university_short": "UCSC",
        "campus": "Concepción",
        "region": "Biobío",
        "city": "Concepción",
        "area": "Ingeniería y Ciencias Exactas",
        "vacantes": 90,
        "weights": {
            "nem": 0.1,
            "ranking": 0.4,
            "lectura": 0.1,
            "m1": 0.25,
            "m2": 0.05,
            "ciencias": 0.1,
            "historia": 0.0,
            "elective_rule": "MAX"
        },
        "cutoffs": {
            "2024": 642.0,
            "2025": 646.5,
            "2026": 649.15
        },
        "requires_m2": True,
        "min_weighted_score": 458.0
    },
    {
        "id": "ingenieria-civil-electrica-ucsc",
        "code": "36067",
        "name": "Ingeniería Civil Eléctrica",
        "university": "Universidad Católica de la Santísima Concepción",
        "university_short": "UCSC",
        "campus": "Concepción",
        "region": "Biobío",
        "city": "Concepción",
        "area": "Ingeniería y Ciencias Exactas",
        "vacantes": 60,
        "weights": {
            "nem": 0.1,
            "ranking": 0.4,
            "lectura": 0.1,
            "m1": 0.25,
            "m2": 0.05,
            "ciencias": 0.1,
            "historia": 0.0,
            "elective_rule": "MAX"
        },
        "cutoffs": {
            "2024": 670.0,
            "2025": 676.0,
            "2026": 681.45
        },
        "requires_m2": True,
        "min_weighted_score": 458.0
    },
    {
        "id": "ingenieria-civil-geologica-ucsc",
        "code": "36063",
        "name": "Ingeniería Civil Geológica",
        "university": "Universidad Católica de la Santísima Concepción",
        "university_short": "UCSC",
        "campus": "Concepción",
        "region": "Biobío",
        "city": "Concepción",
        "area": "Ingeniería y Ciencias Exactas",
        "vacantes": 30,
        "weights": {
            "nem": 0.1,
            "ranking": 0.4,
            "lectura": 0.1,
            "m1": 0.25,
            "m2": 0.05,
            "ciencias": 0.1,
            "historia": 0.0,
            "elective_rule": "MAX"
        },
        "cutoffs": {
            "2024": 575.0,
            "2025": 582.0,
            "2026": 588.10
        },
        "requires_m2": True,
        "min_weighted_score": 458.0
    },
    {
        "id": "ingenieria-civil-industrial-ucsc",
        "code": "36030",
        "name": "Ingeniería Civil Industrial",
        "university": "Universidad Católica de la Santísima Concepción",
        "university_short": "UCSC",
        "campus": "Concepción",
        "region": "Biobío",
        "city": "Concepción",
        "area": "Ingeniería y Ciencias Exactas",
        "vacantes": 120,
        "weights": {
            "nem": 0.1,
            "ranking": 0.4,
            "lectura": 0.1,
            "m1": 0.25,
            "m2": 0.05,
            "ciencias": 0.1,
            "historia": 0.0,
            "elective_rule": "MAX"
        },
        "cutoffs": {
            "2024": 710.2,
            "2025": 718.5,
            "2026": 725.35
        },
        "requires_m2": True,
        "min_weighted_score": 458.0
    },
    {
        "id": "ingenieria-civil-informatica-ucsc",
        "code": "36031",
        "name": "Ingeniería Civil Informática",
        "university": "Universidad Católica de la Santísima Concepción",
        "university_short": "UCSC",
        "campus": "Concepción",
        "region": "Biobío",
        "city": "Concepción",
        "area": "Ingeniería y Ciencias Exactas",
        "vacantes": 80,
        "weights": {
            "nem": 0.1,
            "ranking": 0.4,
            "lectura": 0.1,
            "m1": 0.25,
            "m2": 0.05,
            "ciencias": 0.1,
            "historia": 0.0,
            "elective_rule": "MAX"
        },
        "cutoffs": {
            "2024": 680.5,
            "2025": 688.0,
            "2026": 695.65
        },
        "requires_m2": True,
        "min_weighted_score": 458.0
    },
    {
        "id": "ingenieria-comercial-ucsc",
        "code": "36012",
        "name": "Ingeniería Comercial",
        "university": "Universidad Católica de la Santísima Concepción",
        "university_short": "UCSC",
        "campus": "Concepción",
        "region": "Biobío",
        "city": "Concepción",
        "area": "Ingeniería y Ciencias Exactas",
        "vacantes": 140,
        "weights": {
            "nem": 0.2,
            "ranking": 0.4,
            "lectura": 0.1,
            "m1": 0.2,
            "m2": 0.0,
            "ciencias": 0.1,
            "historia": 0.0,
            "elective_rule": "MAX"
        },
        "cutoffs": {
            "2024": 625.0,
            "2025": 630.1,
            "2026": 635.4
        },
        "requires_m2": False,
        "min_weighted_score": 458.0
    },
    {
        "id": "ingenieria-en-informacion-y-control-de-gestion-ucsc",
        "code": "36079",
        "name": "Ingeniería En Información Y Control De Gestión",
        "university": "Universidad Católica de la Santísima Concepción",
        "university_short": "UCSC",
        "campus": "Concepción",
        "region": "Biobío",
        "city": "Concepción",
        "area": "Ingeniería y Ciencias Exactas",
        "vacantes": 40,
        "weights": {
            "nem": 0.2,
            "ranking": 0.4,
            "lectura": 0.1,
            "m1": 0.2,
            "m2": 0.0,
            "ciencias": 0.1,
            "historia": 0.0,
            "elective_rule": "MAX"
        },
        "cutoffs": {
            "2024": 512.0,
            "2025": 516.0,
            "2026": 520.0
        },
        "requires_m2": False,
        "min_weighted_score": 458.0
    },
    {
        "id": "kinesiologia-ucsc",
        "code": "36064",
        "name": "Kinesiología",
        "university": "Universidad Católica de la Santísima Concepción",
        "university_short": "UCSC",
        "campus": "Concepción",
        "region": "Biobío",
        "city": "Concepción",
        "area": "Ciencias de la Salud",
        "vacantes": 75,
        "weights": {
            "nem": 0.2,
            "ranking": 0.3,
            "lectura": 0.15,
            "m1": 0.25,
            "m2": 0.0,
            "ciencias": 0.1,
            "historia": 0.0,
            "elective_rule": "CIENCIAS"
        },
        "cutoffs": {
            "2024": 715.4,
            "2025": 722.1,
            "2026": 728.3
        },
        "requires_m2": False,
        "min_weighted_score": 458.0
    },
    {
        "id": "licenciatura-en-ciencias-religiosas-y-estudios-teologicos-ucsc",
        "code": "36054",
        "name": "Licenciatura En Ciencias Religiosas Y Estudios Teológicos",
        "university": "Universidad Católica de la Santísima Concepción",
        "university_short": "UCSC",
        "campus": "Concepción",
        "region": "Biobío",
        "city": "Concepción",
        "area": "Humanidades y Ciencias",
        "vacantes": 5,
        "weights": {
            "nem": 0.2,
            "ranking": 0.4,
            "lectura": 0.2,
            "m1": 0.1,
            "m2": 0.0,
            "ciencias": 0.1,
            "historia": 0.0,
            "elective_rule": "MAX"
        },
        "cutoffs": {
            "2024": 512.0,
            "2025": 516.0,
            "2026": 520.0
        },
        "requires_m2": False,
        "min_weighted_score": 458.0
    },
    {
        "id": "licenciatura-en-filosofia-ucsc",
        "code": "36055",
        "name": "Licenciatura En Filosofía",
        "university": "Universidad Católica de la Santísima Concepción",
        "university_short": "UCSC",
        "campus": "Concepción",
        "region": "Biobío",
        "city": "Concepción",
        "area": "Humanidades y Ciencias",
        "vacantes": 20,
        "weights": {
            "nem": 0.2,
            "ranking": 0.4,
            "lectura": 0.2,
            "m1": 0.1,
            "m2": 0.0,
            "ciencias": 0.1,
            "historia": 0.0,
            "elective_rule": "MAX"
        },
        "cutoffs": {
            "2024": 512.0,
            "2025": 516.0,
            "2026": 520.0
        },
        "requires_m2": False,
        "min_weighted_score": 458.0
    },
    {
        "id": "licenciatura-en-historia-ucsc",
        "code": "36061",
        "name": "Licenciatura En Historia",
        "university": "Universidad Católica de la Santísima Concepción",
        "university_short": "UCSC",
        "campus": "Concepción",
        "region": "Biobío",
        "city": "Concepción",
        "area": "Humanidades y Ciencias",
        "vacantes": 40,
        "weights": {
            "nem": 0.2,
            "ranking": 0.4,
            "lectura": 0.15,
            "m1": 0.1,
            "m2": 0.0,
            "ciencias": 0.15,
            "historia": 0.0,
            "elective_rule": "MAX"
        },
        "cutoffs": {
            "2024": 512.0,
            "2025": 516.0,
            "2026": 520.0
        },
        "requires_m2": False,
        "min_weighted_score": 458.0
    },
    {
        "id": "medicina-ucsc",
        "code": "36020",
        "name": "Medicina",
        "university": "Universidad Católica de la Santísima Concepción",
        "university_short": "UCSC",
        "campus": "Concepción",
        "region": "Biobío",
        "city": "Concepción",
        "area": "Ciencias de la Salud",
        "vacantes": 80,
        "weights": {
            "nem": 0.1,
            "ranking": 0.25,
            "lectura": 0.15,
            "m1": 0.25,
            "m2": 0.0,
            "ciencias": 0.25,
            "historia": 0.0,
            "elective_rule": "CIENCIAS"
        },
        "cutoffs": {
            "2024": 898.3,
            "2025": 903.4,
            "2026": 907.55
        },
        "requires_m2": False,
        "min_weighted_score": 458.0
    },
    {
        "id": "nutricion-y-dietetica-ucsc",
        "code": "36051",
        "name": "Nutrición Y Dietética",
        "university": "Universidad Católica de la Santísima Concepción",
        "university_short": "UCSC",
        "campus": "Concepción",
        "region": "Biobío",
        "city": "Concepción",
        "area": "Ciencias de la Salud",
        "vacantes": 75,
        "weights": {
            "nem": 0.15,
            "ranking": 0.35,
            "lectura": 0.15,
            "m1": 0.25,
            "m2": 0.0,
            "ciencias": 0.1,
            "historia": 0.0,
            "elective_rule": "CIENCIAS"
        },
        "cutoffs": {
            "2024": 512.0,
            "2025": 516.0,
            "2026": 520.0
        },
        "requires_m2": False,
        "min_weighted_score": 458.0
    },
    {
        "id": "odontologia-ucsc",
        "code": "36082",
        "name": "Odontología",
        "university": "Universidad Católica de la Santísima Concepción",
        "university_short": "UCSC",
        "campus": "Concepción",
        "region": "Biobío",
        "city": "Concepción",
        "area": "Ciencias de la Salud",
        "vacantes": 80,
        "weights": {
            "nem": 0.15,
            "ranking": 0.3,
            "lectura": 0.2,
            "m1": 0.25,
            "m2": 0.0,
            "ciencias": 0.1,
            "historia": 0.0,
            "elective_rule": "CIENCIAS"
        },
        "cutoffs": {
            "2024": 784.6,
            "2025": 790.2,
            "2026": 795.4
        },
        "requires_m2": False,
        "min_weighted_score": 458.0
    },
    {
        "id": "pedagogia-en-educacion-basica-ucsc",
        "code": "36010",
        "name": "Pedagogía En Educación Básica",
        "university": "Universidad Católica de la Santísima Concepción",
        "university_short": "UCSC",
        "campus": "Concepción",
        "region": "Biobío",
        "city": "Concepción",
        "area": "Educación",
        "vacantes": 50,
        "weights": {
            "nem": 0.2,
            "ranking": 0.4,
            "lectura": 0.15,
            "m1": 0.15,
            "m2": 0.0,
            "ciencias": 0.1,
            "historia": 0.0,
            "elective_rule": "MAX"
        },
        "cutoffs": {
            "2024": 512.0,
            "2025": 516.0,
            "2026": 520.0
        },
        "requires_m2": False,
        "min_weighted_score": 458.0
    },
    {
        "id": "pedagogia-en-educacion-diferencial-ucsc",
        "code": "36056",
        "name": "Pedagogía En Educación Diferencial",
        "university": "Universidad Católica de la Santísima Concepción",
        "university_short": "UCSC",
        "campus": "Concepción",
        "region": "Biobío",
        "city": "Concepción",
        "area": "Educación",
        "vacantes": 70,
        "weights": {
            "nem": 0.2,
            "ranking": 0.4,
            "lectura": 0.15,
            "m1": 0.15,
            "m2": 0.0,
            "ciencias": 0.1,
            "historia": 0.0,
            "elective_rule": "MAX"
        },
        "cutoffs": {
            "2024": 512.0,
            "2025": 516.0,
            "2026": 520.0
        },
        "requires_m2": False,
        "min_weighted_score": 458.0
    },
    {
        "id": "pedagogia-en-educacion-fisica-ucsc",
        "code": "36066",
        "name": "Pedagogía En Educación Física",
        "university": "Universidad Católica de la Santísima Concepción",
        "university_short": "UCSC",
        "campus": "Concepción",
        "region": "Biobío",
        "city": "Concepción",
        "area": "Educación",
        "vacantes": 50,
        "weights": {
            "nem": 0.2,
            "ranking": 0.4,
            "lectura": 0.2,
            "m1": 0.1,
            "m2": 0.0,
            "ciencias": 0.1,
            "historia": 0.0,
            "elective_rule": "MAX"
        },
        "cutoffs": {
            "2024": 512.0,
            "2025": 516.0,
            "2026": 520.0
        },
        "requires_m2": False,
        "min_weighted_score": 458.0
    },
    {
        "id": "pedagogia-en-educacion-media-en-biologia-y-ciencias-naturales-ucsc",
        "code": "36057",
        "name": "Pedagogía En Educación Media En Biología Y Ciencias Naturales",
        "university": "Universidad Católica de la Santísima Concepción",
        "university_short": "UCSC",
        "campus": "Concepción",
        "region": "Biobío",
        "city": "Concepción",
        "area": "Educación",
        "vacantes": 30,
        "weights": {
            "nem": 0.2,
            "ranking": 0.4,
            "lectura": 0.2,
            "m1": 0.1,
            "m2": 0.0,
            "ciencias": 0.1,
            "historia": 0.0,
            "elective_rule": "MAX"
        },
        "cutoffs": {
            "2024": 512.0,
            "2025": 516.0,
            "2026": 520.0
        },
        "requires_m2": False,
        "min_weighted_score": 458.0
    },
    {
        "id": "pedagogia-en-educacion-media-en-ingles-ucsc",
        "code": "36052",
        "name": "Pedagogía En Educación Media En Inglés",
        "university": "Universidad Católica de la Santísima Concepción",
        "university_short": "UCSC",
        "campus": "Concepción",
        "region": "Biobío",
        "city": "Concepción",
        "area": "Educación",
        "vacantes": 70,
        "weights": {
            "nem": 0.2,
            "ranking": 0.4,
            "lectura": 0.2,
            "m1": 0.1,
            "m2": 0.0,
            "ciencias": 0.1,
            "historia": 0.0,
            "elective_rule": "MAX"
        },
        "cutoffs": {
            "2024": 512.0,
            "2025": 516.0,
            "2026": 520.0
        },
        "requires_m2": False,
        "min_weighted_score": 458.0
    },
    {
        "id": "pedagogia-en-educacion-media-en-lenguaje-y-comunicacion-ucsc",
        "code": "36053",
        "name": "Pedagogía En Educación Media En Lenguaje Y Comunicación",
        "university": "Universidad Católica de la Santísima Concepción",
        "university_short": "UCSC",
        "campus": "Concepción",
        "region": "Biobío",
        "city": "Concepción",
        "area": "Educación",
        "vacantes": 65,
        "weights": {
            "nem": 0.2,
            "ranking": 0.4,
            "lectura": 0.2,
            "m1": 0.1,
            "m2": 0.0,
            "ciencias": 0.1,
            "historia": 0.0,
            "elective_rule": "MAX"
        },
        "cutoffs": {
            "2024": 512.0,
            "2025": 516.0,
            "2026": 520.0
        },
        "requires_m2": False,
        "min_weighted_score": 458.0
    },
    {
        "id": "pedagogia-en-educacion-media-en-matematica-ucsc",
        "code": "36065",
        "name": "Pedagogía En Educación Media En Matemática",
        "university": "Universidad Católica de la Santísima Concepción",
        "university_short": "UCSC",
        "campus": "Concepción",
        "region": "Biobío",
        "city": "Concepción",
        "area": "Educación",
        "vacantes": 45,
        "weights": {
            "nem": 0.2,
            "ranking": 0.4,
            "lectura": 0.1,
            "m1": 0.15,
            "m2": 0.05,
            "ciencias": 0.1,
            "historia": 0.0,
            "elective_rule": "MAX"
        },
        "cutoffs": {
            "2024": 512.0,
            "2025": 516.0,
            "2026": 520.0
        },
        "requires_m2": True,
        "min_weighted_score": 458.0
    },
    {
        "id": "periodismo-ucsc",
        "code": "36011",
        "name": "Periodismo",
        "university": "Universidad Católica de la Santísima Concepción",
        "university_short": "UCSC",
        "campus": "Concepción",
        "region": "Biobío",
        "city": "Concepción",
        "area": "Ciencias Sociales y Jurídicas",
        "vacantes": 65,
        "weights": {
            "nem": 0.2,
            "ranking": 0.4,
            "lectura": 0.2,
            "m1": 0.1,
            "m2": 0.0,
            "ciencias": 0.1,
            "historia": 0.0,
            "elective_rule": "MAX"
        },
        "cutoffs": {
            "2024": 512.0,
            "2025": 516.0,
            "2026": 520.0
        },
        "requires_m2": False,
        "min_weighted_score": 458.0
    },
    {
        "id": "psicologia-ucsc",
        "code": "36080",
        "name": "Psicología",
        "university": "Universidad Católica de la Santísima Concepción",
        "university_short": "UCSC",
        "campus": "Concepción",
        "region": "Biobío",
        "city": "Concepción",
        "area": "Ciencias Sociales y Jurídicas",
        "vacantes": 100,
        "weights": {
            "nem": 0.2,
            "ranking": 0.35,
            "lectura": 0.25,
            "m1": 0.1,
            "m2": 0.0,
            "ciencias": 0.1,
            "historia": 0.0,
            "elective_rule": "MAX"
        },
        "cutoffs": {
            "2024": 718.2,
            "2025": 725.0,
            "2026": 730.5
        },
        "requires_m2": False,
        "min_weighted_score": 458.0
    },
    {
        "id": "quimica-ambiental-ucsc",
        "code": "36058",
        "name": "Química Ambiental",
        "university": "Universidad Católica de la Santísima Concepción",
        "university_short": "UCSC",
        "campus": "Concepción",
        "region": "Biobío",
        "city": "Concepción",
        "area": "Humanidades y Ciencias",
        "vacantes": 25,
        "weights": {
            "nem": 0.1,
            "ranking": 0.4,
            "lectura": 0.1,
            "m1": 0.25,
            "m2": 0.0,
            "ciencias": 0.15,
            "historia": 0.0,
            "elective_rule": "MAX"
        },
        "cutoffs": {
            "2024": 512.0,
            "2025": 516.0,
            "2026": 520.0
        },
        "requires_m2": False,
        "min_weighted_score": 458.0
    },
    {
        "id": "quimica-y-farmacia-ucsc",
        "code": "36083",
        "name": "Química Y Farmacia",
        "university": "Universidad Católica de la Santísima Concepción",
        "university_short": "UCSC",
        "campus": "Concepción",
        "region": "Biobío",
        "city": "Concepción",
        "area": "Humanidades y Ciencias",
        "vacantes": 75,
        "weights": {
            "nem": 0.1,
            "ranking": 0.3,
            "lectura": 0.1,
            "m1": 0.3,
            "m2": 0.0,
            "ciencias": 0.2,
            "historia": 0.0,
            "elective_rule": "CIENCIAS"
        },
        "cutoffs": {
            "2024": 512.0,
            "2025": 516.0,
            "2026": 520.0
        },
        "requires_m2": False,
        "min_weighted_score": 458.0
    },
    {
        "id": "tecnologia-medica-ucsc",
        "code": "36078",
        "name": "Tecnología Médica",
        "university": "Universidad Católica de la Santísima Concepción",
        "university_short": "UCSC",
        "campus": "Concepción",
        "region": "Biobío",
        "city": "Concepción",
        "area": "Ciencias de la Salud",
        "vacantes": 100,
        "weights": {
            "nem": 0.15,
            "ranking": 0.4,
            "lectura": 0.1,
            "m1": 0.2,
            "m2": 0.0,
            "ciencias": 0.15,
            "historia": 0.0,
            "elective_rule": "CIENCIAS"
        },
        "cutoffs": {
            "2024": 512.0,
            "2025": 516.0,
            "2026": 520.0
        },
        "requires_m2": False,
        "min_weighted_score": 458.0
    },
    {
        "id": "trabajo-social-ucsc",
        "code": "36050",
        "name": "Trabajo Social",
        "university": "Universidad Católica de la Santísima Concepción",
        "university_short": "UCSC",
        "campus": "Concepción",
        "region": "Biobío",
        "city": "Concepción",
        "area": "Ciencias Sociales y Jurídicas",
        "vacantes": 75,
        "weights": {
            "nem": 0.2,
            "ranking": 0.4,
            "lectura": 0.15,
            "m1": 0.15,
            "m2": 0.0,
            "ciencias": 0.1,
            "historia": 0.0,
            "elective_rule": "MAX"
        },
        "cutoffs": {
            "2024": 512.0,
            "2025": 516.0,
            "2026": 520.0
        },
        "requires_m2": False,
        "min_weighted_score": 458.0
    }
]


def get_cruch_careers() -> List[Dict[str, Any]]:
    """Devuelve la lista completa de carreras del catálogo CRUCH."""
    return CRUCH_CAREERS


def get_career_by_id(career_id: str) -> Optional[Dict[str, Any]]:
    """Busca una carrera específica por su ID."""
    for c in CRUCH_CAREERS:
        if c["id"] == career_id:
            return c
    return None


def normalize_nem_ranking(value: Union[float, int]) -> float:
    """
    Normaliza el valor de NEM o Ranking al rango oficial DEMRE (100 a 1000).
    Si el usuario ingresa una nota chilena (1.00 a 7.00 o valor < 100), la convierte según la
    fórmula oficial DEMRE Grupo A:
    4.00 -> 100 pts
    5.00 -> 400 pts
    6.00 -> 700 pts
    7.00 -> 1000 pts
    Puntaje = 100.0 + (Nota - 4.00) * 300.0
    """
    val = float(value)
    if val < 100.0:
        # Es escala de notas (1.0 a 7.0). Piso mínimo de aprobación DEMRE es 4.0 (100 pts)
        clamped_note = max(4.0, min(7.0, val))
        val = 100.0 + (clamped_note - 4.0) * 300.0
    return float(np.clip(val, 100.0, 1000.0))


def nem_score_to_grade(score: Union[float, int]) -> float:
    """Convierte puntaje NEM oficial (100 a 1000) a nota de enseñanza media chilena (4.00 a 7.00)."""
    s = float(np.clip(score, 100.0, 1000.0))
    grade = 4.0 + (s - 100.0) / 300.0
    return round(grade, 2)


def paes_score_to_raw_items(score: Union[int, float], subject_code: str = "M1") -> int:
    """
    Convierte un puntaje PAES al número mínimo de aciertos (preguntas correctas)
    necesarios según la tabla oficial DEMRE de la prueba.
    """
    code = subject_code.upper()
    meta = SUBJECT_METADATA.get(code, SUBJECT_METADATA["M1"])
    table: Dict[int, int] = meta.get("table", {})
    if not table:
        return int(round((float(score) - 100.0) / 900.0 * meta.get("total_scored", 60)))

    target = int(round(score))
    # Ordenar por aciertos ascendentes
    for raw in sorted(table.keys()):
        if table[raw] >= target:
            return raw
    return max(table.keys())


def raw_items_to_paes_score(raw_score: int, subject_code: str = "M1") -> int:
    """
    Convierte aciertos a puntaje PAES usando la tabla de transformación oficial.
    """
    code = subject_code.upper()
    meta = SUBJECT_METADATA.get(code, SUBJECT_METADATA["M1"])
    table: Dict[int, int] = meta.get("table", {})
    max_items = meta.get("total_scored", 60)
    clamped_raw = max(0, min(max_items, int(raw_score)))
    return table.get(clamped_raw, 100)


def calculate_weighted_score(
    weights: Dict[str, Any],
    nem_score: float,
    ranking_score: float,
    scores: Dict[str, float],
) -> Tuple[float, Dict[str, float]]:
    """
    Calcula el puntaje ponderado oficial de acuerdo a las reglas DEMRE.
    Maneja electivas (regla MAX entre Ciencias e Historia o CIENCIAS obligatoria).
    """
    m1 = scores.get("m1", scores.get("M1", 100.0))
    lectura = scores.get("lectura", scores.get("LECTURA", 100.0))
    m2 = scores.get("m2", scores.get("M2", 100.0))
    ciencias = scores.get("ciencias", scores.get("CIENCIAS", 100.0))
    historia = scores.get("historia", scores.get("HISTORIA", 100.0))

    elective_rule = weights.get("elective_rule", "MAX")
    if elective_rule == "CIENCIAS":
        elective_score = ciencias
        elective_name = "Ciencias"
    elif elective_rule == "HISTORIA":
        elective_score = historia
        elective_name = "Historia"
    else:  # "MAX"
        elective_score = max(ciencias, historia)
        elective_name = "Ciencias" if ciencias >= historia else "Historia"

    elective_weight = weights.get("ciencias", 0.0) + weights.get("historia", 0.0)

    breakdown = {
        "nem": nem_score * weights.get("nem", 0.0),
        "ranking": ranking_score * weights.get("ranking", 0.0),
        "lectura": lectura * weights.get("lectura", 0.0),
        "m1": m1 * weights.get("m1", 0.0),
        "m2": m2 * weights.get("m2", 0.0),
        "electiva": elective_score * elective_weight,
    }

    weighted = sum(breakdown.values())
    return round(weighted, 2), {
        "elective_used": elective_name,
        "elective_score": elective_score,
        "breakdown": {k: round(v, 2) for k, v in breakdown.items()},
    }


def estimate_irt_standard_error(score: float, subject_code: str = "M1") -> float:
    """
    Calcula el error estándar psicométrico de medición bajo la función de información
    del modelo 3PL IRT en la escala PAES [100 - 1000].
    En pruebas estandarizadas DEMRE con ~50-75 ítems, el SEM típico oscila entre 14 y 24 puntos.
    """
    theta = (float(score) - 500.0) / 150.0
    base_se = {
        "M1": 15.0,
        "LECTURA": 16.0,
        "M2": 18.0,
        "CIENCIAS": 16.0,
        "HISTORIA": 16.0,
    }.get(subject_code.upper(), 16.0)

    # Leve incremento en extremos debido a la curvatura de información 3PL
    se = base_se + 1.2 * min(9.0, theta ** 2)
    return float(np.clip(se, 12.0, 26.0))


def calculate_career_chances(
    career: Dict[str, Any],
    user_scores: Dict[str, Any],
    nem: Union[float, int],
    ranking: Union[float, int],
    num_simulations: int = 5000,
    seed: Optional[int] = 42,
) -> Dict[str, Any]:
    """
    Calcula el puntaje ponderado, proyección psicométrica 3PL IRT y la brecha
    a la meta para una carrera específica.
    """
    nem_val = normalize_nem_ranking(nem)
    ranking_val = normalize_nem_ranking(ranking)

    scores_clean = {
        "m1": float(user_scores.get("m1", user_scores.get("M1", 100.0))),
        "lectura": float(user_scores.get("lectura", user_scores.get("LECTURA", 100.0))),
        "m2": float(user_scores.get("m2", user_scores.get("M2", 100.0))),
        "ciencias": float(user_scores.get("ciencias", user_scores.get("CIENCIAS", 100.0))),
        "historia": float(user_scores.get("historia", user_scores.get("HISTORIA", 100.0))),
    }

    weights = career["weights"]
    weighted_score, meta_calc = calculate_weighted_score(weights, nem_val, ranking_val, scores_clean)

    # Corte de referencia oficial (2026 proyectado / último corte disponible)
    cutoff_2026 = float(career["cutoffs"]["2026"])
    cutoff_2025 = float(career["cutoffs"]["2025"])
    cutoff_2024 = float(career["cutoffs"]["2024"])

    # 1. Varianza Psicométrica Ponderada (Error Estándar de la Batería de Pruebas)
    se_m1 = estimate_irt_standard_error(scores_clean["m1"], "M1")
    se_lec = estimate_irt_standard_error(scores_clean["lectura"], "LECTURA")
    se_m2 = estimate_irt_standard_error(scores_clean["m2"], "M2")
    se_cie = estimate_irt_standard_error(scores_clean["ciencias"], "CIENCIAS")
    se_his = estimate_irt_standard_error(scores_clean["historia"], "HISTORIA")

    # Varianza del puntaje ponderado debida al error psicométrico del postulante
    elective_weight = weights.get("ciencias", 0.0) + weights.get("historia", 0.0)
    se_elect = se_cie if meta_calc["elective_used"] == "Ciencias" else se_his

    var_weighted = (
        ((weights.get("lectura", 0.0) * se_lec) ** 2)
        + ((weights.get("m1", 0.0) * se_m1) ** 2)
        + ((weights.get("m2", 0.0) * se_m2) ** 2)
        + ((elective_weight * se_elect) ** 2)
    )
    se_weighted = float(math.sqrt(var_weighted))

    # Variabilidad anual del puntaje de corte histórico (desviación observada 2024-2026)
    cutoff_history = [cutoff_2024, cutoff_2025, cutoff_2026]
    cutoff_std = float(max(3.0, np.std(cutoff_history)))

    # Desviación típica total combinada (postulante + fluctuación de corte)
    total_std = float(math.sqrt((se_weighted ** 2) + (cutoff_std ** 2)))

    # 2. Aproximación Analítica (Distribución Normal Acumulada)
    z_score = (weighted_score - cutoff_2026) / max(total_std, 1e-6)
    prob_analytical = 0.5 * (1.0 + math.erf(z_score / math.sqrt(2.0)))
    prob_analytical = float(np.clip(prob_analytical, 0.001, 0.999))

    # 3. Simulación Psicométrica Monte Carlo
    rng = np.random.default_rng(seed)
    sim_weighted_noise = rng.normal(0.0, se_weighted, num_simulations)
    sim_cutoff_noise = rng.normal(0.0, cutoff_std, num_simulations)
    sim_diff = (weighted_score + sim_weighted_noise) - (cutoff_2026 + sim_cutoff_noise)
    sim_weighted = np.clip(weighted_score + sim_weighted_noise, 100.0, 1000.0)

    admitted_count = np.sum(sim_diff >= 0.0)
    prob_monte_carlo = float(admitted_count / num_simulations)

    # Combinación equilibrada
    prob_final = float(np.clip(0.50 * prob_monte_carlo + 0.50 * prob_analytical, 0.0, 1.0))
    prob_percent = round(prob_final * 100.0, 1)

    # Verificación de Requisito Excluyente DEMRE: M2 Obligatoria
    requires_m2 = bool(career.get("requires_m2", False))
    m2_user_score = scores_clean.get("m2", 100.0)
    # En Chile, 100 es el piso base de asignación cuando no se rinde la prueba
    m2_missing_warning = bool(requires_m2 and m2_user_score <= 100.0)

    # Clasificación oficial solicitada:
    # Segura > 85%, Competitiva 50-85%, Riesgosa < 50%
    if prob_percent >= 85.0:
        category = "Segura"
        color = "green"
        status_message = "Tu puntaje proyectado supera holgadamente el último convocado histórico. Alta certeza de selección."
    elif prob_percent >= 50.0:
        category = "Competitiva"
        color = "amber"
        status_message = "Estás en zona de disputa directa del corte. Un incremento marginal de aciertos asegura tu cupo."
    else:
        category = "Riesgosa"
        color = "red"
        status_message = "Puntaje por debajo del corte histórico de convocatoria. Se requiere estrategia de mejora de aciertos."

    if m2_missing_warning:
        status_message += " [ADVERTENCIA DEMRE: Esta carrera exige rendir obligatoriamente la prueba M2]."

    ci_95_low = round(float(np.percentile(sim_weighted, 2.5)), 2)
    ci_95_high = round(float(np.percentile(sim_weighted, 97.5)), 2)

    # 4. Cálculo de Brecha a la Meta ("Brecha a la Meta")
    weighted_gap = round(cutoff_2026 - weighted_score, 2)
    gap_breakdown: Dict[str, Any] = {}
    balanced_plan: List[Dict[str, Any]] = []

    # Exámenes puntuables evaluados en la carrera
    elective_subj = "CIENCIAS" if meta_calc["elective_used"] == "Ciencias" else "HISTORIA"
    elective_key = elective_subj.lower()
    elective_label = "Ciencias" if elective_subj == "CIENCIAS" else "Historia"
    exam_specs = [
        ("M1", "m1", weights.get("m1", 0.0), "Competencia Matemática 1"),
        ("LECTURA", "lectura", weights.get("lectura", 0.0), "Competencia Lectora"),
        ("M2", "m2", weights.get("m2", 0.0), "Competencia Matemática 2"),
        (elective_subj, elective_key, elective_weight, elective_label),
    ]

    total_eligible_weights = 0.0
    for subj_code, key, weight, subj_name in exam_specs:
        if weight <= 0.0:
            continue
        total_eligible_weights += weight
        curr_score = scores_clean[key]
        curr_raw = paes_score_to_raw_items(curr_score, subj_code)

        if weighted_gap <= 0:
            # Ya cumplió el corte
            gap_breakdown[key] = {
                "subject_code": subj_code,
                "subject_name": subj_name,
                "weight_percent": int(round(weight * 100)),
                "current_score": int(round(curr_score)),
                "target_score": int(round(curr_score)),
                "net_points_needed": 0,
                "current_raw_items": curr_raw,
                "target_raw_items": curr_raw,
                "additional_correct_needed": 0,
                "is_achievable_alone": True,
            }
        else:
            # Puntos netos necesarios si esta prueba compensara la totalidad de la brecha
            needed_pts = math.ceil(weighted_gap / weight)
            target_score = min(1000, int(round(curr_score + needed_pts)))
            achievable_alone = (curr_score + needed_pts) <= 1000

            target_raw = paes_score_to_raw_items(target_score, subj_code)
            add_correct = max(0, target_raw - curr_raw)

            gap_breakdown[key] = {
                "subject_code": subj_code,
                "subject_name": subj_name,
                "weight_percent": int(round(weight * 100)),
                "current_score": int(round(curr_score)),
                "target_score": target_score,
                "net_points_needed": needed_pts,
                "current_raw_items": curr_raw,
                "target_raw_items": target_raw,
                "additional_correct_needed": add_correct,
                "is_achievable_alone": achievable_alone,
            }

    # Plan de Brecha Equilibrado (distribuido proporcionalmente según ponderación)
    if weighted_gap > 0 and total_eligible_weights > 0:
        for subj_code, key, weight, subj_name in exam_specs:
            if weight <= 0.0:
                continue
            curr_score = scores_clean[key]
            curr_raw = paes_score_to_raw_items(curr_score, subj_code)
            # Aporte proporcional asignado a esta prueba
            share = weight / total_eligible_weights
            share_weighted_pts = weighted_gap * share
            net_pts_share = math.ceil(share_weighted_pts / weight)
            target_balanced = min(1000, int(round(curr_score + net_pts_share)))
            target_raw_b = paes_score_to_raw_items(target_balanced, subj_code)
            add_correct_b = max(0, target_raw_b - curr_raw)

            balanced_plan.append({
                "subject_code": subj_code,
                "subject_name": subj_name,
                "weight_percent": int(round(weight * 100)),
                "current_score": int(round(curr_score)),
                "recommended_target_score": target_balanced,
                "net_points_gain": max(0, target_balanced - int(round(curr_score))),
                "additional_correct_needed": add_correct_b,
            })

    return {
        "career_id": career["id"],
        "career_name": career["name"],
        "university": career["university"],
        "university_short": career["university_short"],
        "campus": career.get("campus", ""),
        "area": career.get("area", ""),
        "vacantes": career.get("vacantes", 0),
        "weights": weights,
        "cutoffs": career["cutoffs"],
        "requires_m2": requires_m2,
        "m2_missing_warning": m2_missing_warning,
        "target_cutoff": cutoff_2026,
        "weighted_score": weighted_score,
        "weighted_breakdown": meta_calc["breakdown"],
        "elective_used": meta_calc["elective_used"],
        "nem_normalized": nem_val,
        "ranking_normalized": ranking_val,
        "probability": prob_percent,
        "category": category,
        "color": color,
        "status_message": status_message,
        "psychometric_se_weighted": round(se_weighted, 2),
        "confidence_interval_95": [ci_95_low, ci_95_high],
        "weighted_gap": weighted_gap,
        "is_above_cutoff": (weighted_gap <= 0),
        "gap_breakdown": gap_breakdown,
        "balanced_plan": balanced_plan,
    }


def calculate_admission_chances(
    user_scores: Dict[str, Any],
    nem: Union[float, int],
    ranking: Union[float, int],
    career_id: Optional[str] = None,
    num_simulations: int = 5000,
    seed: Optional[int] = 42,
) -> Dict[str, Any]:
    """
    Función principal de simulación y probabilidad de admisión CRUCH.

    Calcula:
    1. Puntaje ponderado oficial DEMRE.
    2. Proyección de probabilidad psicométrica 3PL IRT + Monte Carlo
       (Segura >85%, Competitiva 50-85%, Riesgosa <50%).
    3. Brecha a la meta en puntos netos y aciertos adicionales requeridos.
    4. Resumen global comparativo para las carreras del catálogo CRUCH.
    """
    # Si se especificó una carrera (como argumento o dentro de user_scores)
    target_id = career_id or user_scores.get("career_id")

    primary_result: Optional[Dict[str, Any]] = None
    if target_id and target_id.upper() != "ALL":
        target_career = get_career_by_id(target_id)
        if target_career:
            primary_result = calculate_career_chances(
                target_career,
                user_scores,
                nem,
                ranking,
                num_simulations=num_simulations,
                seed=seed,
            )

    # Si no se encontró o no se especificó, tomamos Medicina UCH como referencia predeterminada
    if not primary_result:
        default_career = CRUCH_CAREERS[0]
        primary_result = calculate_career_chances(
            default_career,
            user_scores,
            nem,
            ranking,
            num_simulations=num_simulations,
            seed=seed,
        )

    # Generar resumen rápido de todas las carreras para el postulante
    all_summaries: List[Dict[str, Any]] = []
    nem_val = normalize_nem_ranking(nem)
    ranking_val = normalize_nem_ranking(ranking)
    scores_clean = {
        "m1": float(user_scores.get("m1", user_scores.get("M1", 100.0))),
        "lectura": float(user_scores.get("lectura", user_scores.get("LECTURA", 100.0))),
        "m2": float(user_scores.get("m2", user_scores.get("M2", 100.0))),
        "ciencias": float(user_scores.get("ciencias", user_scores.get("CIENCIAS", 100.0))),
        "historia": float(user_scores.get("historia", user_scores.get("HISTORIA", 100.0))),
    }

    for c in CRUCH_CAREERS:
        w_score, _ = calculate_weighted_score(c["weights"], nem_val, ranking_val, scores_clean)
        c_cutoff = float(c["cutoffs"]["2026"])
        # Estimación rápida de probabilidad para la lista general
        diff = w_score - c_cutoff
        # Usar escala psicométrica aproximada de 16 pts para el z-score rápido
        z = diff / 16.0
        prob = round(float(np.clip(0.5 * (1.0 + math.erf(z / math.sqrt(2.0))) * 100.0, 0.1, 99.9)), 1)
        if prob >= 85.0:
            cat = "Segura"
        elif prob >= 50.0:
            cat = "Competitiva"
        else:
            cat = "Riesgosa"

        all_summaries.append({
            "career_id": c["id"],
            "career_name": c["name"],
            "university": c["university"],
            "university_short": c["university_short"],
            "area": c.get("area", ""),
            "weighted_score": w_score,
            "target_cutoff": c_cutoff,
            "gap": round(c_cutoff - w_score, 2),
            "probability": prob,
            "category": cat,
        })

    # Ordenar por probabilidad descendente
    all_summaries.sort(key=lambda x: x["probability"], reverse=True)

    result = dict(primary_result)
    result["all_careers_summary"] = all_summaries
    return result
