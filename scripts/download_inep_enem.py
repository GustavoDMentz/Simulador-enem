#!/usr/bin/env python3
"""Descobre e baixa provas regulares oficiais do Inep (2017–2025).

Não interpreta gabaritos nem altera registros já revisados.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import re
import time
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen

BASE = "https://www.gov.br/inep/pt-br/areas-de-atuacao/avaliacao-e-exames-educacionais/enem/provas-e-gabaritos/"
HEADING = re.compile(r"([12])\s*[ºo°]?\s*dia\s*[-–—]\s*caderno\s*([0-9]+)\s*[-–—]\s*([a-záéíóúâêôãõç]+)", re.I)
COLOR = {"azul": "azul"}
ALLOWED = {"download.inep.gov.br", "www.gov.br", "gov.br"}


class Blocks(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.blocks = []
        self.depth = 0
        self.text = []
        self.links = []
        self.href = None

    def handle_starttag(self, tag, attrs):
        if tag in ("p", "li", "h2", "h3", "h4"):
            if self.depth == 0:
                self.text, self.links = [], []
            self.depth += 1
        if tag == "a":
            self.href = dict(attrs).get("href")

    def handle_data(self, data):
        if self.depth:
            self.text.append(data)
            if self.href:
                self.links.append((data.strip(), self.href))

    def handle_endtag(self, tag):
        if tag == "a":
            self.href = None
        if tag in ("p", "li", "h2", "h3", "h4") and self.depth:
            self.depth -= 1
            if self.depth == 0:
                self.blocks.append((" ".join(" ".join(self.text).split()), self.links[:]))


def discover(html: str, page_url: str):
    parser = Blocks()
    parser.feed(html)
    found = {}
    current = None
    section = ""
    for label, links in parser.blocks:
        lower = label.lower()
        if "reaplica" in lower or "ppl" in lower or "belém" in lower:
            if not HEADING.search(lower):
                section = "other"
                current = None
        elif "aplicação regular" in lower and not HEADING.search(lower):
            section = "regular"
        match = HEADING.search(label)
        if match:
            day, code, color = match.groups()
            current = None
            if section != "other" and color.lower() in COLOR and (
                "regular" in lower or section == "regular"
            ) and not any(word in lower for word in ("ampliada", "libras", "ledor", "braile")):
                current = (int(day), color.lower())
                found.setdefault(current, {"code": int(code), "prova": None, "gabarito": None})
        if current is None:
            continue
        for text, href in links:
            key = "gabarito" if "gabarito" in text.lower() else (
                "prova" if text.lower().strip() == "prova" else None
            )
            if key and found[current][key] is None:
                found[current][key] = urljoin(page_url, href)
    return found


def request(url: str) -> bytes:
    if urlparse(url).scheme != "https" or urlparse(url).hostname not in ALLOWED:
        raise ValueError(f"Domínio não autorizado: {url}")
    with urlopen(Request(url, headers={"User-Agent": "ENEM-Research-Downloader/1.0"}),
                 timeout=45) as response:
        final = response.geturl()
        if urlparse(final).scheme != "https" or urlparse(final).hostname not in ALLOWED:
            raise ValueError(f"Redirecionamento não autorizado: {final}")
        chunks, size = [], 0
        while True:
            chunk = response.read(1024 * 1024)
            if not chunk:
                break
            size += len(chunk)
            if size > 100 * 1024 * 1024:
                raise ValueError("Arquivo excede 100 MiB")
            chunks.append(chunk)
    return b"".join(chunks)


def acquire(dest: Path, manifest_path: Path, *, years, delay: float = 1.0):
    dest.mkdir(parents=True, exist_ok=True)
    existing = {"exams": []}
    if manifest_path.exists():
        existing = json.loads(manifest_path.read_text(encoding="utf-8"))
    entries = list(existing.get("exams", []))
    known = {(int(e["year"]), int(e["day"])) for e in entries}
    results = []
    for year in years:
        page_url = BASE + str(year)
        try:
            discovered = discover(request(page_url).decode("utf-8", "replace"), page_url)
        except Exception as exc:
            results.append({"year": year, "status": "page_failed", "error": str(exc)})
            continue
        for day in (1, 2):
            if (year, day) in known:
                results.append({"year": year, "day": day, "status": "already_registered"})
                continue
            record = discovered.get((day, "azul"))
            if not record or not record["prova"]:
                results.append({"year": year, "day": day, "status": "not_discovered"})
                continue
            pdf_path = dest / f"{year}-regular-d{day}-azul.pdf"
            try:
                if pdf_path.exists():
                    payload = pdf_path.read_bytes()
                else:
                    payload = request(record["prova"])
                if not payload.startswith(b"%PDF"):
                    raise ValueError("Resposta não é PDF")
                if not pdf_path.exists():
                    pdf_path.write_bytes(payload)
                sha = hashlib.sha256(payload).hexdigest()
                entry = {"year": year, "day": day, "color": "azul",
                         "application": "regular", "pdf": str(pdf_path.resolve()),
                         "source_url": record["prova"], "source_sha256": sha,
                         "official_booklet_code": record["code"]}
                if record["gabarito"]:
                    answer_path = dest / f"{year}-regular-d{day}-azul-gabarito.pdf"
                    try:
                        answer = request(record["gabarito"])
                        if not answer.startswith(b"%PDF"):
                            raise ValueError("Gabarito não é PDF")
                        if not answer_path.exists():
                            answer_path.write_bytes(answer)
                        entry["answer_key_url"] = record["gabarito"]
                        entry["answer_key_pdf"] = str(answer_path.resolve())
                        entry["answer_key_sha256"] = hashlib.sha256(answer).hexdigest()
                    except Exception as exc:
                        entry["answer_key_download_error"] = str(exc)
                entries.append(entry)
                known.add((year, day))
                results.append({"year": year, "day": day, "status": "downloaded",
                                "sha256": sha, "answer_key": "answer_key_pdf" in entry})
                # Persist after each successful exam for interruption recovery.
                manifest_path.parent.mkdir(parents=True, exist_ok=True)
                manifest_path.write_text(json.dumps({**existing, "exams": entries},
                    ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            except Exception as exc:
                results.append({"year": year, "day": day, "status": "failed", "error": str(exc)})
            time.sleep(delay)
    report = {"results": results}
    (dest / "download-report.json").write_text(json.dumps(report, ensure_ascii=False,
                                                        indent=2) + "\n", encoding="utf-8")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dest", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--years", nargs="+", type=int, default=list(range(2017, 2026)))
    parser.add_argument("--delay", type=float, default=1.0)
    args = parser.parse_args()
    if any(y < 2017 or y > 2025 for y in args.years) or args.delay < 0:
        parser.error("Anos permitidos: 2017–2025; delay não negativo")
    report = acquire(args.dest, args.manifest, years=args.years, delay=args.delay)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
