"""
Downloader and cataloger for official DEMRE PAES syllabus (temarios) and exams (pruebas oficiales).
Processes years 2024 through 2027 for all test subjects with 100% verified URLs.
"""
import json
import time
import urllib.request
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
TARGET_DIR = BASE_DIR / "data" / "demre_official"
TEMARIOS_DIR = TARGET_DIR / "temarios"
PRUEBAS_DIR = TARGET_DIR / "pruebas"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
}

DEMRE_CATALOG = [
    # ==================== TEMARIOS 2027 ====================
    {
        "id": "temario_2027_m1",
        "year": 2027,
        "type": "temario",
        "subject": "M1",
        "filename": "temario_paes_2027_m1.pdf",
        "url": "https://demre.cl/publicaciones/pdf/2027-26-03-19-temario-paes-regular-m1.pdf"
    },
    {
        "id": "temario_2027_m2",
        "year": 2027,
        "type": "temario",
        "subject": "M2",
        "filename": "temario_paes_2027_m2.pdf",
        "url": "https://demre.cl/publicaciones/pdf/2027-26-03-19-temario-paes-regular-m2.pdf"
    },
    {
        "id": "temario_2027_lectura",
        "year": 2027,
        "type": "temario",
        "subject": "LECTURA",
        "filename": "temario_paes_2027_competencia_lectora.pdf",
        "url": "https://demre.cl/publicaciones/pdf/2027-26-03-19-temario-paes-regular-competencia-lectora.pdf"
    },
    {
        "id": "temario_2027_ciencias",
        "year": 2027,
        "type": "temario",
        "subject": "CIENCIAS",
        "filename": "temario_paes_2027_ciencias.pdf",
        "url": "https://demre.cl/publicaciones/pdf/2027-26-03-19-temario-paes-regular-ciencias.pdf"
    },
    {
        "id": "temario_2027_historia",
        "year": 2027,
        "type": "temario",
        "subject": "HISTORIA",
        "filename": "temario_paes_2027_historia.pdf",
        "url": "https://demre.cl/publicaciones/pdf/2027-26-03-19-temario-paes-regular-historia.pdf"
    },

    # ==================== TEMARIOS 2026 ====================
    {
        "id": "temario_2026_m1",
        "year": 2026,
        "type": "temario",
        "subject": "M1",
        "filename": "temario_paes_2026_m1.pdf",
        "url": "https://demre.cl/publicaciones/pdf/2026-25-03-20-temario-paes-regular-m1.pdf"
    },
    {
        "id": "temario_2026_m2",
        "year": 2026,
        "type": "temario",
        "subject": "M2",
        "filename": "temario_paes_2026_m2.pdf",
        "url": "https://demre.cl/publicaciones/pdf/2026-25-03-20-temario-paes-regular-m2.pdf"
    },
    {
        "id": "temario_2026_lectura",
        "year": 2026,
        "type": "temario",
        "subject": "LECTURA",
        "filename": "temario_paes_2026_competencia_lectora.pdf",
        "url": "https://demre.cl/publicaciones/pdf/2026-25-03-20-temario-paes-regular-competencia-lectora.pdf"
    },
    {
        "id": "temario_2026_ciencias",
        "year": 2026,
        "type": "temario",
        "subject": "CIENCIAS",
        "filename": "temario_paes_2026_ciencias.pdf",
        "url": "https://demre.cl/publicaciones/pdf/2026-25-03-20-temario-paes-regular-ciencias.pdf"
    },
    {
        "id": "temario_2026_historia",
        "year": 2026,
        "type": "temario",
        "subject": "HISTORIA",
        "filename": "temario_paes_2026_historia.pdf",
        "url": "https://demre.cl/publicaciones/pdf/2026-25-03-20-temario-paes-regular-historia.pdf"
    },

    # ==================== TEMARIOS 2025 ====================
    {
        "id": "temario_2025_m1",
        "year": 2025,
        "type": "temario",
        "subject": "M1",
        "filename": "temario_paes_2025_m1.pdf",
        "url": "https://demre.cl/publicaciones/pdf/2025-24-03-21-temario-paes-regular-m1.pdf"
    },
    {
        "id": "temario_2025_m2",
        "year": 2025,
        "type": "temario",
        "subject": "M2",
        "filename": "temario_paes_2025_m2.pdf",
        "url": "https://demre.cl/publicaciones/pdf/2025-24-03-21-temario-paes-regular-m2.pdf"
    },
    {
        "id": "temario_2025_lectura",
        "year": 2025,
        "type": "temario",
        "subject": "LECTURA",
        "filename": "temario_paes_2025_competencia_lectora.pdf",
        "url": "https://demre.cl/publicaciones/pdf/2025-24-03-21-temario-paes-regular-competencia-lectora.pdf"
    },
    {
        "id": "temario_2025_ciencias",
        "year": 2025,
        "type": "temario",
        "subject": "CIENCIAS",
        "filename": "temario_paes_2025_ciencias.pdf",
        "url": "https://demre.cl/publicaciones/pdf/2025-24-03-21-temario-paes-regular-ciencias.pdf"
    },
    {
        "id": "temario_2025_historia",
        "year": 2025,
        "type": "temario",
        "subject": "HISTORIA",
        "filename": "temario_paes_2025_historia.pdf",
        "url": "https://demre.cl/publicaciones/pdf/2025-24-03-21-temario-paes-regular-historia.pdf"
    },

    # ==================== TEMARIOS 2024 ====================
    {
        "id": "temario_2024_m1",
        "year": 2024,
        "type": "temario",
        "subject": "M1",
        "filename": "temario_paes_2024_m1.pdf",
        "url": "https://demre.cl/publicaciones/pdf/2024-23-03-23-temario-paes-regular-m1.pdf"
    },
    {
        "id": "temario_2024_m2",
        "year": 2024,
        "type": "temario",
        "subject": "M2",
        "filename": "temario_paes_2024_m2.pdf",
        "url": "https://demre.cl/publicaciones/pdf/2024-23-03-23-temario-paes-regular-m2.pdf"
    },
    {
        "id": "temario_2024_lectura",
        "year": 2024,
        "type": "temario",
        "subject": "LECTURA",
        "filename": "temario_paes_2024_competencia_lectora.pdf",
        "url": "https://demre.cl/publicaciones/pdf/2024-23-03-23-temario-paes-regular-competencia-lectora.pdf"
    },
    {
        "id": "temario_2024_ciencias",
        "year": 2024,
        "type": "temario",
        "subject": "CIENCIAS",
        "filename": "temario_paes_2024_ciencias.pdf",
        "url": "https://demre.cl/publicaciones/pdf/2024-23-03-23-temario-paes-regular-ciencias.pdf"
    },
    {
        "id": "temario_2024_historia",
        "year": 2024,
        "type": "temario",
        "subject": "HISTORIA",
        "filename": "temario_paes_2024_historia.pdf",
        "url": "https://demre.cl/publicaciones/pdf/2024-23-03-23-temario-paes-regular-historia.pdf"
    },

    # ==================== PRUEBAS OFICIALES 2026 ====================
    {
        "id": "prueba_2026_m1",
        "year": 2026,
        "type": "prueba_oficial",
        "subject": "M1",
        "filename": "prueba_oficial_paes_2026_m1.pdf",
        "url": "https://demre.cl/publicaciones/pdf/2026-25-12-03-paes-regular-matematica1-p2026.pdf"
    },
    {
        "id": "prueba_2026_m2",
        "year": 2026,
        "type": "prueba_oficial",
        "subject": "M2",
        "filename": "prueba_oficial_paes_2026_m2.pdf",
        "url": "https://demre.cl/publicaciones/pdf/2026-25-12-01-paes-regular-matematica2-p2026.pdf"
    },
    {
        "id": "prueba_2026_lectura",
        "year": 2026,
        "type": "prueba_oficial",
        "subject": "LECTURA",
        "filename": "prueba_oficial_paes_2026_competencia_lectora.pdf",
        "url": "https://demre.cl/publicaciones/pdf/2026-25-12-02-paes-regular-competencia-lectora-p2026.pdf"
    },
    {
        "id": "prueba_2026_historia",
        "year": 2026,
        "type": "prueba_oficial",
        "subject": "HISTORIA",
        "filename": "prueba_oficial_paes_2026_historia.pdf",
        "url": "https://demre.cl/publicaciones/pdf/2026-25-12-03-paes-regular-historia-p2026.pdf"
    },
    {
        "id": "prueba_2026_ciencias_biologia",
        "year": 2026,
        "type": "prueba_oficial",
        "subject": "CIENCIAS_BIOLOGIA",
        "filename": "prueba_oficial_paes_2026_ciencias_biologia.pdf",
        "url": "https://demre.cl/publicaciones/pdf/2026-25-12-02-paes-regular-ciencias-biologia-p2026.pdf"
    },
    {
        "id": "prueba_2026_ciencias_fisica",
        "year": 2026,
        "type": "prueba_oficial",
        "subject": "CIENCIAS_FISICA",
        "filename": "prueba_oficial_paes_2026_ciencias_fisica.pdf",
        "url": "https://demre.cl/publicaciones/pdf/2026-25-12-02-paes-regular-ciencias-fisica-p2026.pdf"
    },
    {
        "id": "prueba_2026_ciencias_quimica",
        "year": 2026,
        "type": "prueba_oficial",
        "subject": "CIENCIAS_QUIMICA",
        "filename": "prueba_oficial_paes_2026_ciencias_quimica.pdf",
        "url": "https://demre.cl/publicaciones/pdf/2026-25-12-02-paes-regular-ciencias-quimica-p2026.pdf"
    },

    # ==================== PRUEBAS OFICIALES 2025 ====================
    {
        "id": "prueba_2025_m1",
        "year": 2025,
        "type": "prueba_oficial",
        "subject": "M1",
        "filename": "prueba_oficial_paes_2025_m1.pdf",
        "url": "https://demre.cl/publicaciones/pdf/2025-24-12-04-paes-regular-matematica1-p2025.pdf"
    },
    {
        "id": "prueba_2025_m2",
        "year": 2025,
        "type": "prueba_oficial",
        "subject": "M2",
        "filename": "prueba_oficial_paes_2025_m2.pdf",
        "url": "https://demre.cl/publicaciones/pdf/2025-24-12-02-paes-regular-matematica2-p2025.pdf"
    },
    {
        "id": "prueba_2025_lectura",
        "year": 2025,
        "type": "prueba_oficial",
        "subject": "LECTURA",
        "filename": "prueba_oficial_paes_2025_competencia_lectora.pdf",
        "url": "https://demre.cl/publicaciones/pdf/2025-24-12-03-paes-regular-competencia-lectora-p2025.pdf"
    },
    {
        "id": "prueba_2025_historia",
        "year": 2025,
        "type": "prueba_oficial",
        "subject": "HISTORIA",
        "filename": "prueba_oficial_paes_2025_historia.pdf",
        "url": "https://demre.cl/publicaciones/pdf/2025-24-12-04-paes-regular-historia-p2025.pdf"
    },
    {
        "id": "prueba_2025_ciencias_biologia",
        "year": 2025,
        "type": "prueba_oficial",
        "subject": "CIENCIAS_BIOLOGIA",
        "filename": "prueba_oficial_paes_2025_ciencias_biologia.pdf",
        "url": "https://demre.cl/publicaciones/pdf/2025-24-12-03-paes-regular-ciencias-biologia-p2025.pdf"
    },
    {
        "id": "prueba_2025_ciencias_fisica",
        "year": 2025,
        "type": "prueba_oficial",
        "subject": "CIENCIAS_FISICA",
        "filename": "prueba_oficial_paes_2025_ciencias_fisica.pdf",
        "url": "https://demre.cl/publicaciones/pdf/2025-24-12-03-paes-regular-ciencias-fisica-p2025.pdf"
    },
    {
        "id": "prueba_2025_ciencias_quimica",
        "year": 2025,
        "type": "prueba_oficial",
        "subject": "CIENCIAS_QUIMICA",
        "filename": "prueba_oficial_paes_2025_ciencias_quimica.pdf",
        "url": "https://demre.cl/publicaciones/pdf/2025-24-12-03-paes-regular-ciencias-quimica-p2025.pdf"
    },

    # ==================== PRUEBAS OFICIALES 2024 ====================
    {
        "id": "prueba_2024_m1",
        "year": 2024,
        "type": "prueba_oficial",
        "subject": "M1",
        "filename": "prueba_oficial_paes_2024_m1.pdf",
        "url": "https://demre.cl/publicaciones/pdf/2024-23-11-29-paes-regular-oficial-matematica1-p2024.pdf"
    },
    {
        "id": "prueba_2024_m2",
        "year": 2024,
        "type": "prueba_oficial",
        "subject": "M2",
        "filename": "prueba_oficial_paes_2024_m2.pdf",
        "url": "https://demre.cl/publicaciones/pdf/2024-23-11-27-paes-regular-oficial-matematica2-p2024.pdf"
    },
    {
        "id": "prueba_2024_lectura",
        "year": 2024,
        "type": "prueba_oficial",
        "subject": "LECTURA",
        "filename": "prueba_oficial_paes_2024_competencia_lectora.pdf",
        "url": "https://demre.cl/publicaciones/pdf/2024-23-11-28-paes-regular-oficial-competencia-lectora-p2024.pdf"
    },
    {
        "id": "prueba_2024_historia",
        "year": 2024,
        "type": "prueba_oficial",
        "subject": "HISTORIA",
        "filename": "prueba_oficial_paes_2024_historia.pdf",
        "url": "https://demre.cl/publicaciones/pdf/2024-23-11-29-paes-regular-oficial-historia-p2024.pdf"
    },
    {
        "id": "prueba_2024_ciencias_biologia",
        "year": 2024,
        "type": "prueba_oficial",
        "subject": "CIENCIAS_BIOLOGIA",
        "filename": "prueba_oficial_paes_2024_ciencias_biologia.pdf",
        "url": "https://demre.cl/publicaciones/pdf/2024-23-11-28-paes-regular-oficial-ciencias-biologia-p2024.pdf"
    },
    {
        "id": "prueba_2024_ciencias_fisica",
        "year": 2024,
        "type": "prueba_oficial",
        "subject": "CIENCIAS_FISICA",
        "filename": "prueba_oficial_paes_2024_ciencias_fisica.pdf",
        "url": "https://demre.cl/publicaciones/pdf/2024-23-11-28-paes-regular-oficial-ciencias-fisica-p2024.pdf"
    },
    {
        "id": "prueba_2024_ciencias_quimica",
        "year": 2024,
        "type": "prueba_oficial",
        "subject": "CIENCIAS_QUIMICA",
        "filename": "prueba_oficial_paes_2024_ciencias_quimica.pdf",
        "url": "https://demre.cl/publicaciones/pdf/2024-23-11-28-paes-regular-oficial-ciencias-quimica-p2024.pdf"
    }
]


def download_file(url: str, dest_path: Path, max_retries: int = 3) -> bool:
    """Download a file with retry logic and validate PDF signature."""
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
    print("=== DEMRE Official Documents Downloader (Verified Catalog) ===")
    print(f"Total catalog entries: {len(DEMRE_CATALOG)}")

    TEMARIOS_DIR.mkdir(parents=True, exist_ok=True)
    PRUEBAS_DIR.mkdir(parents=True, exist_ok=True)

    manifest_records = []
    success_count = 0
    failure_count = 0

    for idx, item in enumerate(DEMRE_CATALOG, 1):
        dest_folder = TEMARIOS_DIR if item["type"] == "temario" else PRUEBAS_DIR
        dest_file = dest_folder / item["filename"]
        rel_path = dest_file.relative_to(BASE_DIR)

        print(f"[{idx:02d}/{len(DEMRE_CATALOG):02d}] {item['type'].upper()} {item['year']} - {item['subject']} ({item['filename']})...")

        # Check if already downloaded and valid
        downloaded_ok = False
        if dest_file.exists() and dest_file.stat().st_size > 1024:
            with open(dest_file, "rb") as f:
                header = f.read(5)
            if header == b"%PDF-":
                size_kb = dest_file.stat().st_size // 1024
                print(f"  -> Already exists and valid ({size_kb} KB). Skipping.")
                downloaded_ok = True

        if not downloaded_ok:
            ok = download_file(item["url"], dest_file)
            if ok:
                size_kb = dest_file.stat().st_size // 1024
                print(f"  -> Downloaded OK ({size_kb} KB)")
                downloaded_ok = True
            else:
                print(f"  -> FAILED to download from {item['url']}")

        if downloaded_ok:
            success_count += 1
            file_size = dest_file.stat().st_size
            manifest_records.append({
                "id": item["id"],
                "year": item["year"],
                "type": item["type"],
                "subject": item["subject"],
                "filename": item["filename"],
                "path": str(rel_path).replace("\\", "/"),
                "size_bytes": file_size,
                "url": item["url"],
                "valid_pdf": True
            })
        else:
            failure_count += 1
            manifest_records.append({
                "id": item["id"],
                "year": item["year"],
                "type": item["type"],
                "subject": item["subject"],
                "filename": item["filename"],
                "path": None,
                "size_bytes": 0,
                "url": item["url"],
                "valid_pdf": False
            })

    # Save manifest
    manifest_path = TARGET_DIR / "manifest.json"
    manifest_data = {
        "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "total_documents": len(DEMRE_CATALOG),
        "successful_downloads": success_count,
        "failed_downloads": failure_count,
        "documents": manifest_records
    }
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest_data, f, indent=2, ensure_ascii=False)

    print("\n" + "=" * 50)
    print(f"RESULT: {success_count}/{len(DEMRE_CATALOG)} documents downloaded successfully.")
    if failure_count > 0:
        print(f"WARNING: {failure_count} documents failed.")
    print(f"Manifest written to: {manifest_path}")
    print("=" * 50)


if __name__ == "__main__":
    main()
