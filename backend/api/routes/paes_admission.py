import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from core.rate_limiter import get_rate_limit_str, limiter
from services.paes.cruch_data import (
    calculate_admission_chances,
    get_career_by_id,
    get_cruch_careers,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/paes/admission", tags=["PAES Admission"])


# --- Schemas ---

class ScoresInput(BaseModel):
    m1: Optional[float] = Field(default=500.0, ge=100.0, le=1000.0, description="Puntaje PAES Competencia Matemática 1 (100 - 1000)")
    lectura: Optional[float] = Field(default=500.0, ge=100.0, le=1000.0, description="Puntaje PAES Competencia Lectora (100 - 1000)")
    m2: Optional[float] = Field(default=100.0, ge=100.0, le=1000.0, description="Puntaje PAES Competencia Matemática 2 (100 - 1000)")
    ciencias: Optional[float] = Field(default=100.0, ge=100.0, le=1000.0, description="Puntaje PAES Ciencias (100 - 1000)")
    historia: Optional[float] = Field(default=100.0, ge=100.0, le=1000.0, description="Puntaje PAES Historia (100 - 1000)")


class SimulateAdmissionRequest(BaseModel):
    nem: float = Field(..., ge=1.0, le=1000.0, description="NEM en escala DEMRE (100-1000) o nota escolar chilena (1.0-7.0)")
    ranking: float = Field(..., ge=1.0, le=1000.0, description="Ranking DEMRE (100-1000) o nota escolar (1.0-7.0)")
    career_id: Optional[str] = Field(default=None, description="ID de la carrera objetivo (ej: 'medicina-uch', 'ing-civil-puc')")
    scores: Optional[ScoresInput] = Field(default=None, description="Puntajes en pruebas PAES")
    # Campos directos opcionales para máxima compatibilidad con payloads planos
    m1: Optional[float] = Field(default=None, ge=100.0, le=1000.0)
    lectura: Optional[float] = Field(default=None, ge=100.0, le=1000.0)
    m2: Optional[float] = Field(default=None, ge=100.0, le=1000.0)
    ciencias: Optional[float] = Field(default=None, ge=100.0, le=1000.0)
    historia: Optional[float] = Field(default=None, ge=100.0, le=1000.0)


# --- Endpoints ---

@router.get("/careers")
@limiter.limit(get_rate_limit_str())
def list_cruch_careers(request: Request) -> Dict[str, Any]:
    """
    Lista el catálogo oficial de carreras de alta demanda en universidades del CRUCH
    (UCH, PUC, USACH, UTFSM, UdeC) con ponderaciones oficiales y puntajes de corte históricos (2024-2026).
    """
    careers = get_cruch_careers()
    return {
        "status": "success",
        "total_careers": len(careers),
        "careers": careers,
    }


@router.post("/simulate")
@limiter.limit(get_rate_limit_str())
def simulate_admission(request: Request, body: SimulateAdmissionRequest) -> Dict[str, Any]:
    """
    Simula la postulación y calcula la probabilidad de quedar convocado en el sistema CRUCH.

    1. Calcula el puntaje ponderado oficial con las reglas DEMRE de la carrera seleccionada.
    2. Proyecta la probabilidad de admisión bajo la varianza psicométrica 3PL IRT y Monte Carlo.
    3. Categoriza la postulación:
       - Segura: > 85%
       - Competitiva: 50% - 85%
       - Riesgosa: < 50%
    4. Determina la 'Brecha a la meta': puntos netos y aciertos adicionales requeridos por prueba.
    """
    # Consolidar puntajes de entrada (acepta tanto objeto anidado `scores` como campos directos)
    scores_dict: Dict[str, float] = {}
    if body.scores:
        scores_dict = {
            "m1": body.scores.m1 or 500.0,
            "lectura": body.scores.lectura or 500.0,
            "m2": body.scores.m2 or 100.0,
            "ciencias": body.scores.ciencias or 100.0,
            "historia": body.scores.historia or 100.0,
        }

    # Sobrescribir con campos de primer nivel si fueron provistos
    if body.m1 is not None:
        scores_dict["m1"] = body.m1
    elif "m1" not in scores_dict:
        scores_dict["m1"] = 500.0

    if body.lectura is not None:
        scores_dict["lectura"] = body.lectura
    elif "lectura" not in scores_dict:
        scores_dict["lectura"] = 500.0

    if body.m2 is not None:
        scores_dict["m2"] = body.m2
    elif "m2" not in scores_dict:
        scores_dict["m2"] = 100.0

    if body.ciencias is not None:
        scores_dict["ciencias"] = body.ciencias
    elif "ciencias" not in scores_dict:
        scores_dict["ciencias"] = 100.0

    if body.historia is not None:
        scores_dict["historia"] = body.historia
    elif "historia" not in scores_dict:
        scores_dict["historia"] = 100.0

    # Validar carrera si fue indicada
    if body.career_id and body.career_id.upper() != "ALL":
        career = get_career_by_id(body.career_id)
        if not career:
            raise HTTPException(
                status_code=404,
                detail=f"Carrera con ID '{body.career_id}' no encontrada en el catálogo CRUCH.",
            )

    try:
        result = calculate_admission_chances(
            user_scores=scores_dict,
            nem=body.nem,
            ranking=body.ranking,
            career_id=body.career_id,
        )
        return {
            "status": "success",
            "simulation": result,
        }
    except Exception as exc:
        logger.error(f"Error calculando simulación de admisión CRUCH: {exc}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error interno procesando simulación de admisión: {str(exc)}",
        )
