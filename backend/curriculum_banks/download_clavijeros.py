"""
Downloader and cataloger for official DEMRE PAES answer keys (clavijeros).
Processes years 2024 through 2026 for all test subjects.
"""
import json
import time
import urllib.request
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
TARGET_DIR = BASE_DIR / "data" / "demre_official" / "clavijeros"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
}

CLAVIJEROS_CATALOG = [
    # --- 2026 ---
    {"year": 2026, "subject": "M1", "filename": "clavijero_paes_2026_m1.pdf", "url": "https://demre.cl/publicaciones/pdf/2026-26-01-05-clavijero-paes-regular-m1.pdf"},
    {"year": 2026, "subject": "M2", "filename": "clavijero_paes_2026_m2.pdf", "url": "https://demre.cl/publicaciones/pdf/2026-26-01-05-clavijero-paes-regular-m2.pdf"},
    {"year": 2026, "subject": "LECTURA", "filename": "clavijero_paes_2026_competencia_lectora.pdf", "url": "https://demre.cl/publicaciones/pdf/2026-26-01-05-clavijero-paes-regular-competencia-lectora.pdf"},
    {"year": 2026, "subject": "HISTORIA", "filename": "clavijero_paes_2026_historia.pdf", "url": "https://demre.cl/publicaciones/pdf/2026-26-01-05-clavijero-paes-regular-historia.pdf"},
    {"year": 2026, "subject": "CIENCIAS_BIOLOGIA", "filename": "clavijero_paes_2026_ciencias_biologia.pdf", "url": "https://demre.cl/publicaciones/pdf/2026-26-01-05-clavijero-paes-regular-ciencias-biologia.pdf"},
    {"year": 2026, "subject": "CIENCIAS_FISICA", "filename": "clavijero_paes_2026_ciencias_fisica.pdf", "url": "https://demre.cl/publicaciones/pdf/2026-26-01-05-clavijero-paes-regular-ciencias-fisica.pdf"},
    {"year": 2026, "subject": "CIENCIAS_QUIMICA", "filename": "clavijero_paes_2026_ciencias_quimica.pdf", "url": "https://demre.cl/publicaciones/pdf/2026-26-01-05-clavijero-paes-regular-ciencias-quimica.pdf"},
    {"year": 2026, "subject": "CIENCIAS_TP", "filename": "clavijero_paes_2026_ciencias_tp.pdf", "url": "https://demre.cl/publicaciones/pdf/2026-26-01-05-clavijero-paes-regular-ciencias-tp.pdf"},

    # --- 2025 ---
    {"year": 2025, "subject": "M1", "filename": "clavijero_paes_2025_m1.pdf", "url": "https://demre.cl/publicaciones/pdf/2025-25-01-06-clavijero-paes-regular-m1.pdf"},
    {"year": 2025, "subject": "M2", "filename": "clavijero_paes_2025_m2.pdf", "url": "https://demre.cl/publicaciones/pdf/2025-25-01-06-clavijero-paes-regular-m2.pdf"},
    {"year": 2025, "subject": "LECTURA", "filename": "clavijero_paes_2025_competencia_lectora.pdf", "url": "https://demre.cl/publicaciones/pdf/2025-25-01-06-clavijero-paes-regular-competencia-lectora.pdf"},
    {"year": 2025, "subject": "HISTORIA", "filename": "clavijero_paes_2025_historia.pdf", "url": "https://demre.cl/publicaciones/pdf/2025-25-01-06-clavijero-paes-regular-historia.pdf"},
    {"year": 2025, "subject": "CIENCIAS_BIOLOGIA", "filename": "clavijero_paes_2025_ciencias_biologia.pdf", "url": "https://demre.cl/publicaciones/pdf/2025-25-01-06-clavijero-paes-regular-ciencias-biologia.pdf"},
    {"year": 2025, "subject": "CIENCIAS_FISICA", "filename": "clavijero_paes_2025_ciencias_fisica.pdf", "url": "https://demre.cl/publicaciones/pdf/2025-25-01-06-clavijero-paes-regular-ciencias-fisica.pdf"},
    {"year": 2025, "subject": "CIENCIAS_QUIMICA", "filename": "clavijero_paes_2025_ciencias_quimica.pdf", "url": "https://demre.cl/publicaciones/pdf/2025-25-01-06-clavijero-paes-regular-ciencias-quimica.pdf"},
    {"year": 2025, "subject": "CIENCIAS_TP", "filename": "clavijero_paes_2025_ciencias_tp.pdf", "url": "https://demre.cl/publicaciones/pdf/2025-25-01-06-clavijero-paes-regular-ciencias-tp.pdf"},

    # --- 2024 ---
    {"year": 2024, "subject": "M1", "filename": "clavijero_paes_2024_m1.pdf", "url": "https://demre.cl/publicaciones/pdf/2024-23-12-28-clavijero-paes-regular-m1.pdf"},
    {"year": 2024, "subject": "M2", "filename": "clavijero_paes_2024_m2.pdf", "url": "https://demre.cl/publicaciones/pdf/2024-23-12-28-clavijero-paes-regular-m2.pdf"},
    {"year": 2024, "subject": "LECTURA", "filename": "clavijero_paes_2024_competencia_lectora.pdf", "url": "https://demre.cl/publicaciones/pdf/2024-23-12-28-clavijero-paes-regular-competencia-lectora.pdf"},
    {"year": 2024, "subject": "HISTORIA", "filename": "clavijero_paes_2024_historia.pdf", "url": "https://demre.cl/publicaciones/pdf/2024-23-12-28-clavijero-paes-regular-historia.pdf"},
    {"year": 2024, "subject": "CIENCIAS_BIOLOGIA", "filename": "clavijero_paes_2024_ciencias_biologia.pdf", "url": "https://demre.cl/publicaciones/pdf/2024-23-12-28-clavijero-paes-regular-ciencias-biologia.pdf"},
    {"year": 2024, "subject": "CIENCIAS_FISICA", "filename": "clavijero_paes_2024_ciencias_fisica.pdf", "url": "https://demre.cl/publicaciones/pdf/2024-23-12-28-clavijero-paes-regular-ciencias-fisica.pdf"},
    {"year": 2024, "subject": "CIENCIAS_QUIMICA", "filename": "clavijero_paes_2024_ciencias_quimica.pdf", "url": "https://demre.cl/publicaciones/pdf/2024-23-12-28-clavijero-paes-regular-ciencias-quimica.pdf"},
    {"year": 2024, "subject": "CIENCIAS_TP", "filename": "clavijero_paes_2024_ciencias_tp.pdf", "url": "https://demre.cl/publicaciones/pdf/2024-23-12-28-clavijero-paes-regular-ciencias-tp.pdf"},
]

def download_file(url: str, dest_path: Path, max_retries: int = 3) -> bool:
    req = urllib.request.Request(url, headers=HEADERS)
    for attempt in range(1, max_retries + 1):
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                if resp.status != 200:
                    time.sleep(1)
                    continue
                content = resp.read()
                if not content.startswith(b"%PDF-"):
                    time.sleep(1)
                    continue
                dest_path.write_bytes(content)
                return True
        except Exception:
            time.sleep(1)
    return False

def main():
    TARGET_DIR.mkdir(parents=True, exist_ok=True)
    print(f"=== Downloading DEMRE Official Clavijeros ({len(CLAVIJEROS_CATALOG)} items) ===")

    success = 0
    records = []
    for idx, item in enumerate(CLAVIJEROS_CATALOG, 1):
        dest_file = TARGET_DIR / item["filename"]
        print(f"[{idx:02d}/{len(CLAVIJEROS_CATALOG):02d}] {item['year']} - {item['subject']} ({item['filename']})...")
        ok = False
        if dest_file.exists() and dest_file.stat().st_size > 500:
            with open(dest_file, "rb") as f:
                if f.read(5) == b"%PDF-":
                    ok = True
                    print(f"  -> Already exists ({dest_file.stat().st_size // 1024} KB)")

        if not ok:
            ok = download_file(item["url"], dest_file)
            if ok:
                print(f"  -> Downloaded OK ({dest_file.stat().st_size // 1024} KB)")
            else:
                print(f"  -> FAILED: {item['url']}")

        if ok:
            success += 1
            records.append({
                "year": item["year"],
                "subject": item["subject"],
                "filename": item["filename"],
                "path": str(dest_file.relative_to(BASE_DIR)).replace("\\", "/"),
                "size_bytes": dest_file.stat().st_size,
                "url": item["url"]
            })

    manifest_path = TARGET_DIR / "manifest.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump({"total": len(CLAVIJEROS_CATALOG), "downloaded": success, "items": records}, f, indent=2)
    print(f"\nResult: {success}/{len(CLAVIJEROS_CATALOG)} clavijeros downloaded successfully.")
    print(f"Manifest: {manifest_path}")

if __name__ == "__main__":
    main()
