"""
DEMRE Batch Importer for Peak.
Audits and imports extracted PAES questions (2024-2026) into SQLite peak.db.
Usage:
  python demre_batch_importer.py --dry-run
  python demre_batch_importer.py --import
"""
import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List

# Ensure backend root is on sys.path
BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

from sqlmodel import Session, select

from core.database import engine
from curriculum_banks.quality_filter import QualityFilter
from models.paes_models import (
    PaesCompetency,
    PaesEjeTematico,
    PaesLearningState,
    PaesQuestion,
    PaesSubject,
    PaesSubtopic,
    PaesTopic,
)

DATA_DIR = BACKEND_DIR.parent / "data" / "extracted_questions"


def get_subtopic_id_for_question(subject: str, q_num: int, subtopics_by_subject: Dict[str, List[str]]) -> str:
    """Smart heuristic mapping of DEMRE question numbers to registered subtopics."""
    subj = subject.upper()
    available = subtopics_by_subject.get(subj, [])
    if not available:
        # Fallback to any available
        for k, v in subtopics_by_subject.items():
            if v:
                return v[0]
        return "sub-generic"

    if subj == "M1":
        # 13 subtopics across 4 ejes
        if q_num <= 17:
            # Números (subtopics 0, 1, 2)
            idx = (q_num - 1) % 3
            return available[min(idx, len(available)-1)]
        elif q_num <= 36:
            # Álgebra y funciones (subtopics 3, 4, 5, 6)
            idx = 3 + ((q_num - 18) % 4)
            return available[min(idx, len(available)-1)]
        elif q_num <= 50:
            # Geometría (subtopics 7, 8, 9)
            idx = 7 + ((q_num - 37) % 3)
            return available[min(idx, len(available)-1)]
        else:
            # Probabilidad y estadística (subtopics 10, 11, 12)
            idx = 10 + ((q_num - 51) % 3)
            return available[min(idx, len(available)-1)]

    elif subj == "M2":
        # 10 subtopics
        if q_num <= 14:
            idx = (q_num - 1) % 3
        elif q_num <= 28:
            idx = 3 + ((q_num - 15) % 2)
        elif q_num <= 40:
            idx = 5 + ((q_num - 29) % 2)
        else:
            idx = 7 + ((q_num - 41) % 3)
        return available[min(idx, len(available)-1)]

    elif subj == "LECTURA":
        idx = (q_num - 1) % len(available)
        return available[idx]

    elif "BIOLOGIA" in subj:
        bio_subs = [s for s in available if "bio" in s.lower() or "genetica" in s.lower() or "evolucion" in s.lower()]
        pool = bio_subs if bio_subs else available
        return pool[(q_num - 1) % len(pool)]

    elif "FISICA" in subj:
        fis_subs = [s for s in available if "fis" in s.lower() or "mecanica" in s.lower() or "electricidad" in s.lower() or "termo" in s.lower()]
        pool = fis_subs if fis_subs else available
        return pool[(q_num - 1) % len(pool)]

    elif "QUIMICA" in subj:
        quim_subs = [s for s in available if "quim" in s.lower() or "estequio" in s.lower() or "acido" in s.lower()]
        pool = quim_subs if quim_subs else available
        return pool[(q_num - 1) % len(pool)]

    elif "HISTORIA" in subj:
        return available[(q_num - 1) % len(available)]

    return available[0]


def sanitize_currency_katex(text: str) -> str:
    """Escapes lone currency dollars into \\$ so KaTeX parser doesn't break."""
    if not text:
        return ""
    unescaped = [m.start() for m in re.finditer(r'(?<!\\)\$', text)]
    if len(unescaped) % 2 != 0:
        # If there are no LaTeX backslash commands (e.g. text is '000 254 $'), all dollars are currency
        if not re.search(r'\\[a-zA-Z]+', text):
            return re.sub(r'(?<!\\)\$', r'\\$', text)
    # Also escape dollars adjacent to digits
    return re.sub(r'(?<!\\)\$(?=\s*\d)', r'\\$', text)


def run_batch_import(dry_run: bool = True):
    print("=" * 75)
    print("PEAK DATA PIPELINE: IMPORTACIÓN MASIVA DE PREGUNTAS DEMRE (2024-2026)")
    print(f"Modo: {'🔍 AUDITORÍA (DRY-RUN - Sin cambios en BD)' if dry_run else '🚀 IMPORTACIÓN ACTIVA EN SQLITE'}")
    print("=" * 75)

    if not DATA_DIR.exists():
        print(f"Error: Directorio {DATA_DIR} no encontrado.")
        return

    with Session(engine) as session:
        # 1. Cargar subtemas y mapear por asignatura
        subjects = session.exec(select(PaesSubject)).all()
        subtopics_by_subject = {}
        all_valid_subtopics = set()

        for s in subjects:
            subs = session.exec(
                select(PaesSubtopic)
                .join(PaesTopic, PaesSubtopic.topic_id == PaesTopic.id)
                .join(PaesEjeTematico, PaesTopic.eje_id == PaesEjeTematico.id)
                .where(PaesEjeTematico.subject_id == s.id)
            ).all()
            sub_ids = [st.id for st in subs]
            subtopics_by_subject[s.code.upper()] = sub_ids
            all_valid_subtopics.update(sub_ids)

        # Para Ciencias, agrupar bajo CIENCIAS_BIOLOGIA, CIENCIAS_FISICA, etc.
        ciencias_ids = subtopics_by_subject.get("CIENCIAS", [])
        subtopics_by_subject["CIENCIAS_BIOLOGIA"] = ciencias_ids
        subtopics_by_subject["CIENCIAS_FISICA"] = ciencias_ids
        subtopics_by_subject["CIENCIAS_QUIMICA"] = ciencias_ids

        # 2. Competencias registradas
        competencies = session.exec(select(PaesCompetency)).all()
        comp_map = {c.code: c.id for c in competencies}
        default_comp = list(comp_map.values())[0] if comp_map else "comp-resolver-problemas"

        # 3. Leer y validar archivos extraídos
        json_files = sorted(list(DATA_DIR.glob("*.json")))
        print(f"Archivos JSON encontrados en {DATA_DIR.name}: {len(json_files)}")

        total_extracted = 0
        passed_items = []
        rejected_items = []

        for jf in json_files:
            with open(jf, encoding="utf-8") as f:
                content = json.load(f)

            questions = content.get("questions", [])
            for q in questions:
                total_extracted += 1
                subj = q.get("subject", "M1").upper()
                q_num = q.get("question_number", 1)

                # Asignar subtopic válido
                sub_id = get_subtopic_id_for_question(subj, q_num, subtopics_by_subject)
                q["subtopic_id"] = sub_id

                # Asegurar explicación pedagógica
                correct_key = q.get("correct_answer", "A")
                if not q.get("explanation"):
                    q["explanation"] = {
                        "correct_solution": f"La alternativa correcta según la pauta oficial del DEMRE es la opción {correct_key}.",
                        "skill_evaluated": "Aplicación y resolución de problemas según temario oficial DEMRE."
                    }

                # Sanitizar signos $ de moneda chilena para compatibilidad KaTeX
                q["stem"] = sanitize_currency_katex(q.get("stem", ""))
                for opt in q.get("options", []):
                    opt["text"] = sanitize_currency_katex(opt.get("text", ""))

                # Validar con QualityFilter
                is_valid, errors = QualityFilter.validate_item(q, all_valid_subtopics)
                if is_valid:
                    passed_items.append(q)
                else:
                    rejected_items.append((q.get("id"), errors))

        print("\n" + "-" * 75)
        print("RESULTADOS DEL FILTRADO DE CALIDAD:")
        print(f"  • Total de preguntas auditadas:   {total_extracted}")
        print(f"  • Aprobadas (cumplen estándar):   {len(passed_items)} ({len(passed_items)/total_extracted*100:.1f}%)")
        print(f"  • Rechazadas (descartes):        {len(rejected_items)}")
        if rejected_items:
            print(f"    (Ejemplo rechazo: {rejected_items[0][0]} -> {rejected_items[0][1]})")
        print("-" * 75)

        if dry_run:
            print("\n[DRY-RUN] Auditoría completada con éxito.")
            print("Para guardar permanentemente en SQLite, ejecuta: python demre_batch_importer.py --import")
            return

        # 4. Inserción activa en SQLite
        now = datetime.now(timezone.utc)
        imported_count = 0
        updated_count = 0

        for q_data in passed_items:
            q_id = q_data["id"]
            options_list = q_data["options"]

            # Normalizar IDs y keys de opciones
            for opt in options_list:
                opt["id"] = opt["key"]

            skill_id = default_comp
            if "LECTURA" in q_data.get("subject", ""):
                skill_id = comp_map.get("RELACIONAR_INTERPRETAR", default_comp)

            existing = session.get(PaesQuestion, q_id)
            if not existing:
                new_q = PaesQuestion(
                    id=q_id,
                    subtopic_id=q_data["subtopic_id"],
                    skill_id=skill_id,
                    provenance_type="OFFICIAL_DEMRE",
                    stem=q_data["stem"],
                    stimulus_title=f"Lectura PAES {q_data.get('year')}" if q_data.get("stimulus") else None,
                    stimulus_text=q_data.get("stimulus"),
                    options_json=json.dumps(options_list, ensure_ascii=False),
                    explanation_json=json.dumps(q_data["explanation"], ensure_ascii=False),
                    difficulty_estimate=0.50,
                    difficulty_source="DEMRE_OFFICIAL_EXAM",
                    created_at=now,
                    updated_at=now,
                )
                session.add(new_q)
                imported_count += 1
            else:
                existing.stem = q_data["stem"]
                existing.stimulus_text = q_data.get("stimulus")
                existing.options_json = json.dumps(options_list, ensure_ascii=False)
                existing.explanation_json = json.dumps(q_data["explanation"], ensure_ascii=False)
                existing.updated_at = now
                session.add(existing)
                updated_count += 1

            # Asegurar LearningState para user 1
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
        print("\n🎉 IMPORTACIÓN EXITOSA EN PEAK.DB:")
        print(f"  • Nuevas preguntas insertadas:   {imported_count}")
        print(f"  • Preguntas actualizadas:        {updated_count}")

        # Conteo final en DB
        final_count = session.exec(select(PaesQuestion)).all()
        print(f"  • Total preguntas en la BD:      {len(final_count)}")
        print("=" * 75)


def main():
    parser = argparse.ArgumentParser(description="DEMRE Batch Importer")
    parser.add_argument("--import", dest="do_import", action="store_true", help="Insertar en SQLite")
    parser.add_argument("--dry-run", dest="dry_run", action="store_true", default=True, help="Auditoría sin cambios")
    args = parser.parse_args()

    run_batch_import(dry_run=not args.do_import)


if __name__ == "__main__":
    main()
