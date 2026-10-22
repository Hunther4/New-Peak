"""
CLI Importer y Filtro de Calidad para Bancos de Preguntas PAES.
Uso:
  python bank_importer.py --dry-run   # Audita y valida sin modificar la BD
  python bank_importer.py --import    # Inserta en SQLite solo los ítems validados
"""
import argparse
import json
import random
import sys
from datetime import datetime, timezone
from pathlib import Path

# Add backend directory to sys.path
BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

from sqlmodel import Session, select

from core.database import engine
from curriculum_banks.demre_quality_bank import QUALITY_QUESTIONS
from curriculum_banks.quality_filter import QualityFilter
from models.paes_models import (
    PaesCompetency,
    PaesLearningState,
    PaesQuestion,
    PaesSubtopic,
)


def run_pipeline(dry_run: bool = True):
    print("=" * 70)
    print("PEAK DATA PIPELINE: IMPORTADOR Y FILTRO DE CALIDAD PAES")
    print(f"Modo: {'🔍 AUDITORÍA (DRY-RUN - Sin cambios)' if dry_run else '🚀 IMPORTACIÓN ACTIVA'}")
    print("=" * 70)

    with Session(engine) as session:
        # 1. Cargar subtemas válidos
        subtopics = session.exec(select(PaesSubtopic)).all()
        valid_subtopic_ids = {s.id for s in subtopics}
        print(f"Subtemas registrados en DB: {len(valid_subtopic_ids)}")

        # 2. Cargar competencias registradas
        competencies = session.exec(select(PaesCompetency)).all()
        comp_map = {c.code: c.id for c in competencies}

        # Si faltan competencias de lectura, crearlas dinámicamente si no existen
        missing_comps = {
            "RASTREAR_LOCALIZAR": ("Rastrear y Localizar", "Capacidad de identificar y extraer información explícita."),
            "RELACIONAR_INTERPRETAR": ("Relacionar e Interpretar", "Capacidad de inferir, relacionar párrafos y sintetizar."),
            "EVALUAR_REFLEXIONAR": ("Evaluar y Reflexionar", "Capacidad de juzgar la forma, contenido y propósito del texto."),
        }
        for code, (name, desc) in missing_comps.items():
            if code not in comp_map:
                new_c = PaesCompetency(
                    id=f"comp-{code.lower().replace('_', '-')}",
                    code=code,
                    name=name,
                    description=desc,
                )
                session.add(new_c)
                session.commit()
                comp_map[code] = new_c.id
                print(f"  + Competencia registrada: {code}")

        # Fallback competency si alguna no existe
        default_comp_id = list(comp_map.values())[0] if comp_map else "comp-resolver-problemas"

        # 3. Filtrado de Calidad
        passed_items = []
        failed_items = []

        print(f"\nAuditando {len(QUALITY_QUESTIONS)} ítems contra la rúbrica de calidad...")
        for q in QUALITY_QUESTIONS:
            is_valid, errors = QualityFilter.validate_item(q, valid_subtopic_ids)
            if is_valid:
                passed_items.append(q)
                print(f"  ✅ [PASS] {q['id']} ({q.get('subtopic_id')})")
            else:
                failed_items.append((q['id'], errors))
                print(f"  ❌ [REJECT] {q['id']}: {', '.join(errors)}")

        print("\n" + "-" * 70)
        print("RESUMEN DEL FILTRADO:")
        print(f"  - Aprobados (Calidad Verificada): {len(passed_items)}")
        print(f"  - Rechazados:                    {len(failed_items)}")
        print("-" * 70)

        if dry_run:
            print("\n[DRY-RUN] No se realizaron modificaciones en la base de datos.")
            print("Para importar a SQLite, ejecuta: python bank_importer.py --import")
            return

        # 4. Importación a SQLite
        imported_count = 0
        updated_count = 0
        now = datetime.now(timezone.utc)

        for i, q_data in enumerate(passed_items):
            raw_options = q_data["options"]
            target_pos = i % 4
            correct_opt = [o for o in raw_options if o.get("is_correct")][0]
            distractors = [o for o in raw_options if not o.get("is_correct")]

            rng = random.Random(q_data["id"])
            rng.shuffle(distractors)

            balanced_opts = []
            d_idx = 0
            for p in range(4):
                if p == target_pos:
                    balanced_opts.append(dict(correct_opt))
                else:
                    balanced_opts.append(dict(distractors[d_idx]))
                    d_idx += 1
            for p, letter in enumerate(["A", "B", "C", "D"]):
                balanced_opts[p]["id"] = letter
                balanced_opts[p]["key"] = letter

            skill_code = q_data.get("skill_code", "RESOLVER_PROBLEMAS")
            skill_id = comp_map.get(skill_code, default_comp_id)

            existing = session.get(PaesQuestion, q_data["id"])
            if not existing:
                new_q = PaesQuestion(
                    id=q_data["id"],
                    subtopic_id=q_data["subtopic_id"],
                    skill_id=skill_id,
                    provenance_type="CURATED_DEMRE",
                    stem=q_data["stem"],
                    stimulus_title=q_data.get("stimulus_title"),
                    stimulus_text=q_data.get("stimulus_text"),
                    options_json=json.dumps(balanced_opts, ensure_ascii=False),
                    explanation_json=json.dumps(q_data["explanation"], ensure_ascii=False),
                    difficulty_estimate=q_data.get("difficulty_estimate", 0.5),
                    difficulty_source="DEMRE_CURATED",
                    created_at=now,
                    updated_at=now,
                )
                session.add(new_q)
                imported_count += 1
            else:
                existing.stem = q_data["stem"]
                existing.stimulus_title = q_data.get("stimulus_title")
                existing.stimulus_text = q_data.get("stimulus_text")
                existing.options_json = json.dumps(balanced_opts, ensure_ascii=False)
                existing.explanation_json = json.dumps(q_data["explanation"], ensure_ascii=False)
                existing.updated_at = now
                session.add(existing)
                updated_count += 1

            # Asegurar que el usuario 1 tenga learning state para este subtema
            sub_id = q_data["subtopic_id"]
            ls = session.exec(
                select(PaesLearningState).where(
                    PaesLearningState.user_id == 1,
                    PaesLearningState.subtopic_id == sub_id
                )
            ).first()
            if not ls:
                new_ls = PaesLearningState(
                    id=f"ls-1-{sub_id[:12]}",
                    user_id=1,
                    subtopic_id=sub_id,
                    mastery_score=0.0,
                    confidence_score=0.0,
                    leitner_box=1,
                    next_review_at=now,
                    fsrs_stability=1.0,
                    fsrs_difficulty=5.0,
                    recent_accuracy=0.0,
                    total_attempts=0,
                    total_successes=0,
                    last_practiced_at=now,
                )
                session.add(new_ls)

        session.commit()
        print("\n🎉 IMPORTACIÓN EXITOSA:")
        print(f"  - Nuevas preguntas añadidas:   {imported_count}")
        print(f"  - Preguntas actualizadas:       {updated_count}")
        print("=" * 70)


def main():
    parser = argparse.ArgumentParser(description="Peak PAES Quality Importer")
    parser.add_argument("--import", dest="do_import", action="store_true", help="Ejecutar importación real en DB")
    parser.add_argument("--dry-run", dest="dry_run", action="store_true", default=True, help="Auditoría sin cambios")
    args = parser.parse_args()

    is_dry_run = not args.do_import
    run_pipeline(dry_run=is_dry_run)


if __name__ == "__main__":
    main()
