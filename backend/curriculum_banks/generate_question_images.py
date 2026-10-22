"""
Batch Question Image Cropper for DEMRE PAES Exams.
Crops each official question directly from the original DEMRE PDFs as high-resolution PNGs
and assigns `image_url` to the corresponding `PaesQuestion` records in peak.db.
"""
import re
import sqlite3
from pathlib import Path
from typing import List, Tuple

import pymupdf

BASE_DIR = Path(__file__).resolve().parent.parent.parent
PRUEBAS_DIR = BASE_DIR / "data" / "demre_official" / "pruebas"
UPLOADS_DIR = BASE_DIR / "backend" / "uploads" / "questions"
DB_PATH = BASE_DIR / "backend" / "peak.db"

EXAMS_CATALOG = [
    # --- 2026 ---
    ("paes-2026-m1", "prueba_oficial_paes_2026_m1.pdf"),
    ("paes-2026-m2", "prueba_oficial_paes_2026_m2.pdf"),
    ("paes-2026-lectura", "prueba_oficial_paes_2026_competencia_lectora.pdf"),
    ("paes-2026-historia", "prueba_oficial_paes_2026_historia.pdf"),
    ("paes-2026-ciencias_biologia", "prueba_oficial_paes_2026_ciencias_biologia.pdf"),
    ("paes-2026-ciencias_fisica", "prueba_oficial_paes_2026_ciencias_fisica.pdf"),
    ("paes-2026-ciencias_quimica", "prueba_oficial_paes_2026_ciencias_quimica.pdf"),

    # --- 2025 ---
    ("paes-2025-m1", "prueba_oficial_paes_2025_m1.pdf"),
    ("paes-2025-m2", "prueba_oficial_paes_2025_m2.pdf"),
    ("paes-2025-lectura", "prueba_oficial_paes_2025_competencia_lectora.pdf"),
    ("paes-2025-historia", "prueba_oficial_paes_2025_historia.pdf"),
    ("paes-2025-ciencias_biologia", "prueba_oficial_paes_2025_ciencias_biologia.pdf"),
    ("paes-2025-ciencias_fisica", "prueba_oficial_paes_2025_ciencias_fisica.pdf"),
    ("paes-2025-ciencias_quimica", "prueba_oficial_paes_2025_ciencias_quimica.pdf"),

    # --- 2024 ---
    ("paes-2024-m1", "prueba_oficial_paes_2024_m1.pdf"),
    ("paes-2024-m2", "prueba_oficial_paes_2024_m2.pdf"),
    ("paes-2024-lectura", "prueba_oficial_paes_2024_competencia_lectora.pdf"),
    ("paes-2024-historia", "prueba_oficial_paes_2024_historia.pdf"),
    ("paes-2024-ciencias_biologia", "prueba_oficial_paes_2024_ciencias_biologia.pdf"),
    ("paes-2024-ciencias_fisica", "prueba_oficial_paes_2024_ciencias_fisica.pdf"),
    ("paes-2024-ciencias_quimica", "prueba_oficial_paes_2024_ciencias_quimica.pdf"),
]


def crop_exam_questions(exam_prefix: str, pdf_filename: str) -> List[Tuple[str, str]]:
    pdf_path = PRUEBAS_DIR / pdf_filename
    if not pdf_path.exists():
        print(f"Warning: {pdf_path} not found.")
        return []

    doc = pymupdf.open(pdf_path)
    exam_dir = UPLOADS_DIR / exam_prefix.replace("-", "_")
    exam_dir.mkdir(parents=True, exist_ok=True)

    cropped_records = []

    # Iterate through pages skipping instructions/cover
    for pno in range(2, len(doc) - 1):
        page = doc[pno]
        blocks = page.get_text("blocks")

        # Detect question numbers on this page using robust word-level scanning
        q_raw = []
        words = page.get_text("words")
        for w in words:
            m = re.match(r"^(\d{1,2})\.$", w[4].strip())
            if m:
                q_num = int(m.group(1))
                # DEMRE questions are left-aligned (x0 < 120) and not in header (y0 > 45)
                if 1 <= q_num <= 80 and w[0] < 120 and w[1] > 45:
                    q_raw.append((q_num, w[1], w[3]))

        if not q_raw:
            continue

        # Deduplicate by question number and sort vertically
        q_map = {q[0]: q for q in q_raw}
        q_on_page = sorted(list(q_map.values()), key=lambda x: x[1])

        for idx, (q_num, y0, y1) in enumerate(q_on_page):
            top = max(55, y0 - 12)
            if idx + 1 < len(q_on_page):
                next_q_y0 = q_on_page[idx + 1][1]
            else:
                next_q_y0 = page.rect.height - 40

            # Gather all content blocks and drawings belonging to this question
            content_y1_list = [y1]
            for b in blocks:
                b_y0, b_y1, b_txt = b[1], b[3], b[4].strip()
                if b_y1 < top or b_y0 >= next_q_y0:
                    continue
                # Exclude footer page number e.g. "- 7 -"
                if re.match(r"^\s*-\s*\d+\s*-\s*$", b_txt) or (b_y0 > page.rect.height - 55 and re.match(r"^\d+$", b_txt)):
                    continue
                content_y1_list.append(b_y1)

            try:
                for d in page.get_drawings():
                    dr = d["rect"]
                    if dr.y0 >= top - 5 and dr.y1 <= next_q_y0 + 5 and dr.y1 < page.rect.height - 45:
                        content_y1_list.append(dr.y1)
            except Exception:
                pass

            max_content_y1 = max(content_y1_list)
            bottom = min(max_content_y1 + 14, next_q_y0 - 4 if idx + 1 < len(q_on_page) else page.rect.height - 40)

            clip_rect = pymupdf.Rect(35, top, page.rect.width - 35, bottom)
            if clip_rect.height > 50:
                pix = page.get_pixmap(clip=clip_rect, dpi=135)
                img_name = f"q{q_num:02d}.png"
                img_path = exam_dir / img_name
                pix.save(str(img_path))

                q_id = f"{exam_prefix}-q{q_num:02d}"
                rel_url = f"/uploads/questions/{exam_dir.name}/{img_name}"
                cropped_records.append((q_id, rel_url))

    return cropped_records


def main():
    print("=== DEMRE Question Image Crop Pipeline ===")
    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

    total_cropped = 0
    all_mappings = []

    for prefix, fname in EXAMS_CATALOG:
        print(f"Cropping: {prefix} ({fname})...")
        records = crop_exam_questions(prefix, fname)
        all_mappings.extend(records)
        total_cropped += len(records)
        print(f"  -> Generated {len(records)} question crops.")

    print(f"\nTotal question crops generated: {total_cropped}")

    # Update peak.db
    print("\nUpdating peak.db with image_url references...")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    updated = 0
    for q_id, url in all_mappings:
        cursor.execute("UPDATE paes_questions SET image_url = ? WHERE id = ?;", (url, q_id))
        if cursor.rowcount > 0:
            updated += 1

    conn.commit()
    conn.close()
    print(f"Successfully linked {updated} question images in peak.db!")


if __name__ == "__main__":
    main()
