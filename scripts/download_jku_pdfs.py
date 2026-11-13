"""Download the JKU test documents into data/raw/ and write data/sources.csv.

Run from the project root:
    python scripts/download_jku_pdfs.py

Only uses the Python standard library. If PyMuPDF is installed
(pip install pymupdf), it also checks every PDF for real text and flags
files that look like scans.
"""

import csv
import time
import urllib.request
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data" / "raw"
SOURCES_CSV = ROOT / "data" / "sources.csv"

# (filename, title, category, language, url)
DOCS = [
    # --- Regulations (long legal text, German) ---
    ("satzung_studienrecht_2026.pdf", "Satzungsteil Studienrecht (Stand 01.07.2026)", "regulation", "de",
     "https://www.jku.at/fileadmin/gruppen/61/Satzung___Co/Satzung/Studienrecht/2105_Satzungsteil_Studienrecht_V31_2026_07_02.pdf"),
    ("anmeldeverordnung.pdf", "Anmeldeverordnung", "regulation", "de",
     "https://www.jku.at/fileadmin/gruppen/381/SIBS/Zusatzinfos_Studienrichtungen/Anmeldeverordnung_mtb23_170506.pdf"),
    ("hausordnung_2026.pdf", "Hausordnung (Stand 08.10.2026)", "regulation", "de",
     "https://www.jku.at/fileadmin/gruppen/61/Satzung___Co/Hausordnung/2116_Hausordnung_V17_2026_10_08.pdf"),
    ("parkordnung_2026.pdf", "Parkordnung (Stand 09.09.2026)", "regulation", "de",
     "https://www.jku.at/fileadmin/gruppen/61/Satzung___Co/Parkordnung/4101_Parkordnung_V6_2026_09_09.pdf"),
    ("parkordnung_kostenblatt_2026.pdf", "Kostenblatt 2026 zur Parkordnung (table)", "regulation", "de",
     "https://www.jku.at/fileadmin/gruppen/61/Satzung___Co/Parkordnung/4101_Parkordnung_Kostenblatt_Anhang_1_V9_2026_03_01.pdf"),
    ("benuetzungsordnung_bibliothek.pdf", "Benützungsordnung der Universitätsbibliothek", "regulation", "de",
     "https://www.jku.at/fileadmin/gruppen/61/Satzung___Co/Benuetzungsordnung_Bibliothek/Benuetzungsordnung_UB_MTB06_080212.pdf"),

    # --- KUSSS info sheets (short how-tos, German) ---
    ("kusss_lva_pruefungsanmeldung.pdf", "Infoblatt LVA-Prüfungsanmeldung", "info_sheet", "de",
     "https://www.jku.at/fileadmin/gruppen/381/SIBS/Zusatzinfos_Studienrichtungen/InformationsblattLVA-PrfungsanmeldungV4.1.pdf"),
    ("kusss_terminkollision.pdf", "Infoblatt Terminkollision und Anmeldung/Zuteilung", "info_sheet", "de",
     "https://www.jku.at/fileadmin/gruppen/381/SIBS/Zusatzinfos_Studienrichtungen/Infoblatt-Terminkollision-im-KUSSS-V1.4.pdf"),
    ("kusss_voraussetzungspruefung.pdf", "Infoblatt Voraussetzungsprüfung im KUSSS", "info_sheet", "de",
     "https://www.jku.at/fileadmin/gruppen/381/SIBS/KUSSS_Informationsblaetter/Voraussetzungspruefung_V7.pdf"),

    # --- Study guides (student-friendly) ---
    ("Bachelor_AI_Studienleitfaden.pdf", "ÖH Study Guide Bachelor AI (2025/26)", "study_guide", "en",
     "https://oeh.jku.at/fileadmin/user_upload/StV_Artificial-Intelligence/pdf/Bachelor_AI_Studienleitfaden.pdf"),
    ("Leitfaden_Bachelorstudium_Informatik.pdf", "ÖH Leitfaden Bachelorstudium Informatik", "study_guide", "de",
     "https://oeh.jku.at/fileadmin/user_upload/StV_Informatik/Unterlagen/Leitfaden_Bachelorstudium_Informatik.pdf"),
    ("cs_bachelor_guide_2023_de.pdf", "CS Bachelor Guide 2023", "study_guide", "de",
     "https://www.cs.jku.at/teaching/curricula/2023/CS_Bachelor_Guide_de.pdf"),

    # --- Program flyers (short, marketing) ---
    ("flyer_master_ai.pdf", "Flyer Master Artificial Intelligence", "flyer", "unknown",
     "https://www.jku.at/fileadmin/marketing/01_STUDIEN/MA-Artificial-Intelligence.pdf"),

]

HEADERS = {"User-Agent": "Mozilla/5.0 (rag-document-assistant; student portfolio project)"}


def download(url: str, target: Path) -> int:
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=60) as resp:
        data = resp.read()
    if not data.startswith(b"%PDF"):
        raise ValueError("response is not a PDF")
    target.write_bytes(data)
    return len(data)


def text_check(path: Path) -> str:
    """Return a short note on whether the PDF has extractable text."""
    try:
        import fitz  # PyMuPDF
    except ImportError:
        return "not checked (pip install pymupdf)"
    with fitz.open(path) as doc:
        pages = doc.page_count
        chars = sum(len(page.get_text()) for page in doc)
    per_page = chars / max(pages, 1)
    verdict = "LIKELY SCAN - skip for now" if per_page < 200 else "ok"
    return f"{pages} pages, ~{per_page:.0f} chars/page, {verdict}"


def main() -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    rows = []
    for filename, title, category, lang, url in DOCS:
        target = RAW_DIR / filename
        try:
            if target.exists():
                size = target.stat().st_size
                status = "already there"
            else:
                size = download(url, target)
                status = "downloaded"
            check = text_check(target)
        except Exception as exc:  # keep going if one link is dead
            size, status, check = 0, f"FAILED: {exc}", ""
        print(f"{status:>14}  {filename}  {check}")
        rows.append({
            "filename": filename, "title": title, "category": category,
            "language": lang, "url": url, "downloaded": date.today().isoformat(),
            "bytes": size, "status": status, "text_check": check,
        })
        time.sleep(1)  # be polite to the server

    with SOURCES_CSV.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    ok = sum(r["bytes"] > 0 for r in rows)
    print(f"\n{ok}/{len(rows)} PDFs in {RAW_DIR}")
    print(f"Sources written to {SOURCES_CSV}")


if __name__ == "__main__":
    main()
