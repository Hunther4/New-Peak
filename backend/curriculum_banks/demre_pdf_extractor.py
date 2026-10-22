"""
DEMRE PDF Question Extractor and Cataloger.
Extracts questions, reading stimuli, options (A-D/E), and matches them with official Clavijero answers.
Outputs structured JSON validated for the Peak question engine.
"""
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

import pymupdf

BASE_DIR = Path(__file__).resolve().parent.parent.parent
PRUEBAS_DIR = BASE_DIR / "data" / "demre_official" / "pruebas"
CLAVIJEROS_DIR = BASE_DIR / "data" / "demre_official" / "clavijeros"
OUTPUT_DIR = BASE_DIR / "data" / "extracted_questions"


def parse_clavijero(pdf_path: Path) -> Dict[int, str]:
    """Parse answer key mapping from a DEMRE clavijero PDF."""
    if not pdf_path.exists():
        return {}

    doc = pymupdf.open(pdf_path)
    text = ""
    for page in doc:
        page_text = page.get_text("text")
        if any(h in page_text.upper() for h in ["CLAVES", "CLAVIJERO"]):
            text += page_text + "\n"

    # Match pairs like "1\nB" or "24*\nC" across multi-column tables
    matches = re.findall(r'(\b\d{1,2}\*?)\s*\n\s*([A-E])\b', text)
    answers = {}
    for q_str, key in matches:
        q_num = int(q_str.replace("*", ""))
        answers[q_num] = key.upper()
    return answers


def extract_reading_passages(full_text: str) -> List[Dict[str, Any]]:
    """Detect reading passages like 'Lectura 2: preguntas 10 a 19' and their text."""
    matches = list(re.finditer(r'(?:^|\n)\s*Lectura\s+(\d+):\s*preguntas\s+(\d+)\s+a\s+(\d+)', full_text, re.I))
    passages = []

    for idx, match in enumerate(matches):
        lec_num = int(match.group(1))
        start_q = int(match.group(2))
        end_q = int(match.group(3))

        # Passage text is between this marker and the start of the first question (or next passage)
        start_pos = match.end()
        # Find first question number after this point
        q_match = re.search(r'(?:^|\n)\s*' + str(start_q) + r'\.\s+', full_text[start_pos:])
        if q_match:
            end_pos = start_pos + q_match.start()
        else:
            end_pos = matches[idx + 1].start() if idx + 1 < len(matches) else len(full_text)

        passage_text = full_text[start_pos:end_pos].strip()
        # Clean extra whitespace
        passage_text = re.sub(r'\n{3,}', '\n\n', passage_text)

        passages.append({
            "lectura_num": lec_num,
            "start_q": start_q,
            "end_q": end_q,
            "text": passage_text
        })
    return passages


def clean_pdf_text(doc: pymupdf.Document) -> str:
    """Extract clean text across pages, omitting running headers and footers."""
    full_text = ""
    for page_num in range(1, len(doc)):  # skip cover
        page_text = doc[page_num].get_text("text")
        lines = page_text.split("\n")
        clean_lines = []
        for line in lines:
            # Skip DEMRE header lines like 'FORMA 113 – 2026' or page markers like '- 3 -'
            if re.match(r'^\s*FORMA\s+\d+', line, re.I):
                continue
            if re.match(r'^\s*-\s*\d+\s*-\s*$', line):
                continue
            if re.match(r'^\s*•\s*\d+\s*•\s*$', line):
                continue
            clean_lines.append(line)
        full_text += "\n" + "\n".join(clean_lines)
    return full_text


def extract_questions_from_text(full_text: str, subject: str, year: int, answers: Dict[int, str]) -> List[Dict[str, Any]]:
    """Parse question blocks with stem and options A-D/E."""
    passages = extract_reading_passages(full_text) if "LECTURA" in subject.upper() else []

    # Pattern to find start of question: e.g. '\n1.\n' or '\n1. En un juego...'
    q_matches = list(re.finditer(r'(?:^|\n)\s*(\d{1,2})\.\s*(?:\n|\s+(?=[A-Z¿¡"“\(\d\$\-]))', full_text))

    parsed_questions = []

    for idx in range(len(q_matches)):
        q_num = int(q_matches[idx].group(1))
        start = q_matches[idx].end()
        end = q_matches[idx + 1].start() if idx + 1 < len(q_matches) else len(full_text)
        q_body = full_text[start:end].strip()

        # Options detection (A, B, C, D, and optionally E)
        opt_matches = list(re.finditer(r'(?:^|\n)\s*([A-E])\)\s*', q_body))
        if len(opt_matches) < 4:
            continue

        stem = q_body[:opt_matches[0].start()].strip()
        stem = re.sub(r'\s+', ' ', stem)

        # Determine matching reading passage if any
        matching_stimulus = None
        for p in passages:
            if p["start_q"] <= q_num <= p["end_q"]:
                matching_stimulus = p["text"]
                break

        # Parse options
        correct_key = answers.get(q_num)
        options = []
        for o_idx in range(len(opt_matches)):
            key = opt_matches[o_idx].group(1).upper()
            opt_start = opt_matches[o_idx].end()
            opt_end = opt_matches[o_idx + 1].start() if o_idx + 1 < len(opt_matches) else len(q_body)
            opt_text = q_body[opt_start:opt_end].strip()
            opt_text = re.sub(r'\s+', ' ', opt_text)

            is_correct = (key == correct_key) if correct_key else False
            options.append({
                "key": key,
                "text": opt_text,
                "is_correct": is_correct,
                "distractor_type": "CORRECT" if is_correct else "DISTRACTOR"
            })

        parsed_questions.append({
            "id": f"paes-{year}-{subject.lower()}-q{q_num:02d}",
            "year": year,
            "subject": subject,
            "question_number": q_num,
            "stimulus": matching_stimulus,
            "stem": stem,
            "options": options,
            "correct_answer": correct_key,
            "official_status": "PILOT" if (correct_key is None and q_num in answers) else "SCORED"
        })

    return parsed_questions


def extract_test(year: int, subject: str, test_filename: str, clavijero_filename: str) -> Optional[Dict[str, Any]]:
    """Extract a complete exam and cross-reference with its answer key."""
    test_path = PRUEBAS_DIR / test_filename
    clav_path = CLAVIJEROS_DIR / clavijero_filename

    if not test_path.exists():
        print(f"Warning: Test file {test_path} not found.")
        return None

    print(f"\nProcessing: {year} - {subject}...")
    answers = parse_clavijero(clav_path)
    print(f"  Clavijero loaded: {len(answers)} keys found.")

    doc = pymupdf.open(test_path)
    text = clean_pdf_text(doc)
    questions = extract_questions_from_text(text, subject, year, answers)

    print(f"  Extracted {len(questions)} valid questions with 4-5 options.")
    with_correct = sum(1 for q in questions if q.get("correct_answer") is not None)
    print(f"  Matched with official answer key: {with_correct}/{len(questions)}")

    output_data = {
        "metadata": {
            "year": year,
            "subject": subject,
            "test_filename": test_filename,
            "clavijero_filename": clavijero_filename,
            "total_extracted": len(questions),
            "matched_keys": with_correct
        },
        "questions": questions
    }

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_file = OUTPUT_DIR / f"paes_{year}_{subject.lower()}.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)

    print(f"  Saved to: {out_file.relative_to(BASE_DIR)}")
    return output_data


def main():
    print("=== DEMRE PAES PDF Batch Extractor ===")

    all_targets = [
        # --- 2026 ---
        (2026, "M1", "prueba_oficial_paes_2026_m1.pdf", "clavijero_paes_2026_m1.pdf"),
        (2026, "M2", "prueba_oficial_paes_2026_m2.pdf", "clavijero_paes_2026_m2.pdf"),
        (2026, "LECTURA", "prueba_oficial_paes_2026_competencia_lectora.pdf", "clavijero_paes_2026_competencia_lectora.pdf"),
        (2026, "HISTORIA", "prueba_oficial_paes_2026_historia.pdf", "clavijero_paes_2026_historia.pdf"),
        (2026, "CIENCIAS_BIOLOGIA", "prueba_oficial_paes_2026_ciencias_biologia.pdf", "clavijero_paes_2026_ciencias_biologia.pdf"),
        (2026, "CIENCIAS_FISICA", "prueba_oficial_paes_2026_ciencias_fisica.pdf", "clavijero_paes_2026_ciencias_fisica.pdf"),
        (2026, "CIENCIAS_QUIMICA", "prueba_oficial_paes_2026_ciencias_quimica.pdf", "clavijero_paes_2026_ciencias_quimica.pdf"),

        # --- 2025 ---
        (2025, "M1", "prueba_oficial_paes_2025_m1.pdf", "clavijero_paes_2025_m1.pdf"),
        (2025, "M2", "prueba_oficial_paes_2025_m2.pdf", "clavijero_paes_2025_m2.pdf"),
        (2025, "LECTURA", "prueba_oficial_paes_2025_competencia_lectora.pdf", "clavijero_paes_2025_competencia_lectora.pdf"),
        (2025, "HISTORIA", "prueba_oficial_paes_2025_historia.pdf", "clavijero_paes_2025_historia.pdf"),
        (2025, "CIENCIAS_BIOLOGIA", "prueba_oficial_paes_2025_ciencias_biologia.pdf", "clavijero_paes_2025_ciencias_biologia.pdf"),
        (2025, "CIENCIAS_FISICA", "prueba_oficial_paes_2025_ciencias_fisica.pdf", "clavijero_paes_2025_ciencias_fisica.pdf"),
        (2025, "CIENCIAS_QUIMICA", "prueba_oficial_paes_2025_ciencias_quimica.pdf", "clavijero_paes_2025_ciencias_quimica.pdf"),

        # --- 2024 ---
        (2024, "M1", "prueba_oficial_paes_2024_m1.pdf", "clavijero_paes_2024_m1.pdf"),
        (2024, "M2", "prueba_oficial_paes_2024_m2.pdf", "clavijero_paes_2024_m2.pdf"),
        (2024, "LECTURA", "prueba_oficial_paes_2024_competencia_lectora.pdf", "clavijero_paes_2024_competencia_lectora.pdf"),
        (2024, "HISTORIA", "prueba_oficial_paes_2024_historia.pdf", "clavijero_paes_2024_historia.pdf"),
        (2024, "CIENCIAS_BIOLOGIA", "prueba_oficial_paes_2024_ciencias_biologia.pdf", "clavijero_paes_2024_ciencias_biologia.pdf"),
        (2024, "CIENCIAS_FISICA", "prueba_oficial_paes_2024_ciencias_fisica.pdf", "clavijero_paes_2024_ciencias_fisica.pdf"),
        (2024, "CIENCIAS_QUIMICA", "prueba_oficial_paes_2024_ciencias_quimica.pdf", "clavijero_paes_2024_ciencias_quimica.pdf"),
    ]

    total_q = 0
    total_matched = 0

    for year, subj, test_f, clav_f in all_targets:
        res = extract_test(year, subj, test_f, clav_f)
        if res:
            total_q += res["metadata"]["total_extracted"]
            total_matched += res["metadata"]["matched_keys"]

    print("\n" + "=" * 50)
    print("BATCH EXTRACTION COMPLETE:")
    print(f"Total Questions Extracted: {total_q}")
    print(f"Total Matched with Official DEMRE Key: {total_matched} ({total_matched/total_q*100:.1f}%)")
    print(f"Output Directory: {OUTPUT_DIR}")
    print("=" * 50)


if __name__ == "__main__":
    main()
