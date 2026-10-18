#!/usr/bin/env python3
"""Importa um PDF do ENEM a partir de arquivo local ou URL oficial.

Grava um manifesto verificável sem modificar arquivos já existentes.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request, urlopen

MAX_BYTES = 150 * 1024 * 1024


def official_url(url: str) -> bool:
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    return parsed.scheme == "https" and (host == "gov.br" or host.endswith(".gov.br"))


def copy_and_hash(source, target: Path, max_bytes: int = MAX_BYTES) -> tuple[str, int]:
    digest = hashlib.sha256()
    size = 0
    with target.open("wb") as output:
        header = source.read(5)
        if header != b"%PDF-":
            raise ValueError("Fonte não contém cabeçalho PDF")
        output.write(header)
        digest.update(header)
        size += len(header)
        while chunk := source.read(1024 * 1024):
            size += len(chunk)
            if size > max_bytes:
                raise ValueError("PDF excede o limite configurado")
            output.write(chunk)
            digest.update(chunk)
    return digest.hexdigest(), size


def import_pdf(*, year: int, day: int, color: str, output: Path,
               source_path: Path | None = None, source_url: str | None = None) -> dict:
    if (source_path is None) == (source_url is None):
        raise ValueError("Informe exatamente uma origem: --file ou --url")
    if not 1998 <= year <= 2100 or day not in (1, 2):
        raise ValueError("Ano ou dia inválido")
    color = color.lower().strip()
    if not color.isalpha() or len(color) > 30:
        raise ValueError("Cor inválida")
    if source_url and not official_url(source_url):
        raise ValueError("A URL inicial deve ser HTTPS em domínio gov.br")
    if source_path and not source_path.is_file():
        raise FileNotFoundError(source_path)

    directory = output / str(year) / f"dia{day}" / color
    directory.mkdir(parents=True, exist_ok=True)
    destination = directory / "prova.pdf"
    manifest_path = directory / "source.json"
    if destination.exists() or manifest_path.exists():
        raise FileExistsError(f"Fonte já cadastrada em {directory}; não será sobrescrita")

    temp_name = None
    try:
        with tempfile.NamedTemporaryFile(prefix=".enem-", suffix=".pdf", dir=directory, delete=False) as temp:
            temp_name = Path(temp.name)
        if source_path:
            with source_path.open("rb") as source:
                sha, size = copy_and_hash(source, temp_name)
        else:
            request = Request(source_url, headers={"User-Agent": "SimuladorENEM/2.0 (public educational project)"})
            with urlopen(request, timeout=60) as response:
                sha, size = copy_and_hash(response, temp_name)
        manifest = {
            "year": year, "day": day, "color": color,
            "source_type": "official_url" if source_url else "local_file",
            "source": source_url if source_url else str(source_path.resolve()),
            "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
            "filename": "prova.pdf", "sha256": sha, "size_bytes": size,
        }
        os.replace(temp_name, destination)
        temp_name = None
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return manifest
    finally:
        if temp_name and temp_name.exists():
            temp_name.unlink()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--year", type=int, required=True)
    parser.add_argument("--day", type=int, choices=[1, 2], required=True)
    parser.add_argument("--color", required=True)
    parser.add_argument("--output", type=Path, default=Path("data/sources"))
    origin = parser.add_mutually_exclusive_group(required=True)
    origin.add_argument("--file", type=Path)
    origin.add_argument("--url")
    args = parser.parse_args()
    result = import_pdf(year=args.year, day=args.day, color=args.color,
                        output=args.output, source_path=args.file, source_url=args.url)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
