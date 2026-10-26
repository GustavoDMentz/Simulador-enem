#!/usr/bin/env python3
"""Descobre e baixa provas regulares oficiais do Inep (2017–2025).

Não interpreta gabaritos nem altera registros já revisados.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import re
import ssl
import time
import socket
import subprocess
import tempfile
from urllib.error import HTTPError, URLError
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen, ProxyHandler, HTTPSHandler, build_opener

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


def request(url: str, *, attempts: int = 3, ca_bundle: str | None = None) -> bytes:
    if urlparse(url).scheme != "https" or urlparse(url).hostname not in ALLOWED:
        raise ValueError(f"Domínio não autorizado: {url}")
    if attempts < 1:
        raise ValueError("attempts deve ser positivo")
    context = ssl.create_default_context(cafile=ca_bundle)
    last_error = None
    for attempt in range(attempts):
        try:
            return _download_once(url, context, ca_bundle=ca_bundle)
        except (HTTPError, URLError, ConnectionResetError, TimeoutError,
                socket.timeout, ssl.SSLError) as exc:
            last_error = exc
            if isinstance(exc, HTTPError) and exc.code not in (429, 500, 502, 503, 504):
                raise
            if isinstance(exc, ssl.SSLCertVerificationError) or (
                isinstance(exc, URLError) and
                isinstance(exc.reason, ssl.SSLCertVerificationError)
            ):
                raise RuntimeError(
                    f"Falha de certificado HTTPS em {url}: {exc!r}. "
                    "Configure CA_BUNDLE com uma cadeia confiável; "
                    "não desative a verificação SSL."
                ) from exc
            if attempt + 1 < attempts:
                time.sleep(min(2 ** attempt, 8))
    raise RuntimeError(f"Falha após {attempts} tentativas em {url}: {last_error}")


def _curl_verified(url: str, *, ca_bundle: str | None = None) -> bytes:
    """Try verified IPv4 HTTPS through the environment, then directly.

    Never follow redirects or disable certificate verification. A custom CA
    bundle applies to both Python and curl.
    """
    errors = []
    with tempfile.TemporaryDirectory(prefix="enem-tls-") as tmp:
        target = Path(tmp) / "download.pdf"
        base = ["curl", "--ipv4", "--fail", "--silent", "--show-error",
                "--proto", "=https", "--connect-timeout", "8", "--max-time", "30",
                "--max-filesize", str(100 * 1024 * 1024),
                "--output", str(target)]
        if ca_bundle:
            base += ["--cacert", ca_bundle]
        for transport in ([], ["--noproxy", "*"]):
            try:
                result = subprocess.run(base + transport + [url],
                                        capture_output=True, text=True, timeout=35)
            except subprocess.TimeoutExpired:
                errors.append("curl transport timed out")
                continue
            if result.returncode:
                errors.append(result.stderr[:250])
                continue
            if target.stat().st_size > 100 * 1024 * 1024:
                raise ValueError("Arquivo excede 100 MiB")
            return target.read_bytes()
    raise URLError("Verified IPv4 HTTPS transports failed: " + "; ".join(errors))


def _download_once(url: str, context: ssl.SSLContext,
                   *, ca_bundle: str | None = None) -> bytes:
    # Respect a configured HTTPS proxy. Some runners cannot reach Inep directly.
    # If Python fails, curl tries verified IPv4 with the proxy and then directly.
    opener = build_opener(ProxyHandler(), HTTPSHandler(context=context))
    try:
        response = opener.open(Request(url, headers={"User-Agent": "ENEM-Research-Downloader/1.0"}),
                               timeout=20)
    except HTTPError:
        raise
    except (ssl.SSLError, URLError, TimeoutError, ConnectionResetError):
        return _curl_verified(url, ca_bundle=ca_bundle)
    with response:
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


def acquire(dest: Path, manifest_path: Path, *, years, delay: float = 1.0,
            ca_bundle: str | None = None):
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
            discovered = discover(request(page_url, ca_bundle=ca_bundle).decode("utf-8", "replace"), page_url)
        except Exception as exc:
            results.append({"year": year, "status": "page_failed", "error": str(exc)})
            # A source transport outage affecting the first year is unlikely
            # to improve across the same domain; fail early in unattended CI.
            if year == years[0] and not entries:
                results.append({"status": "source_transport_blocked",
                                "reason": "First official index page inaccessible"})
                break
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
                    payload = request(record["prova"], ca_bundle=ca_bundle)
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
                        answer = request(record["gabarito"], ca_bundle=ca_bundle)
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
                if not entries and any(x in str(exc).lower() for x in
                                       ("certificate", "certificado", "curl: (60)", "timed out",
                                        "transports failed")):
                    results.append({"status": "source_transport_blocked",
                                    "reason": "Verified HTTPS unavailable for official PDFs"})
                    (dest / "download-report.json").write_text(
                        json.dumps({"results": results}, ensure_ascii=False, indent=2) + "\n",
                        encoding="utf-8")
                    return {"results": results}
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
    parser.add_argument("--ca-bundle", type=Path,
                        help="Arquivo PEM com CAs confiáveis, se necessário")
    args = parser.parse_args()
    if any(y < 2017 or y > 2025 for y in args.years) or args.delay < 0:
        parser.error("Anos permitidos: 2017–2025; delay não negativo")
    report = acquire(args.dest, args.manifest, years=args.years, delay=args.delay,
                     ca_bundle=str(args.ca_bundle) if args.ca_bundle else None)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

