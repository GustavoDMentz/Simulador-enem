#!/usr/bin/env python3
"""Captura HTML local com Chromium/Playwright e registra hash no manifesto."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def capture(folder: Path) -> dict:
    folder = folder.resolve()
    manifest_path = folder / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    files = manifest["files_sha256"]
    for name, expected in files.items():
        path = (folder / name).resolve()
        if not path.is_relative_to(folder) or not path.is_file() or digest(path) != expected:
            raise ValueError(f"Evidência alterada: {name}")
    if "reconstructed.png" in files:
        raise ValueError("Captura já registrada; crie novo pacote para recapturar")
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise RuntimeError("Instale playwright e o Chromium: pip install playwright && python -m playwright install chromium") from exc
    html_path = folder / "reconstructed.html"
    png = folder / "reconstructed.png"
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        try:
            page = browser.new_page(viewport={"width": 1100, "height": 900}, device_scale_factor=1)
            page.goto(html_path.as_uri(), wait_until="load")
            page.locator("img").evaluate_all(
                "(images) => Promise.all(images.map(i => i.decode()))"
            )
            page.screenshot(path=str(png), full_page=True, animations="disabled")
        finally:
            browser.close()
    files["reconstructed.png"] = digest(png)
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"image": str(png), "sha256": files["reconstructed.png"],
            "publication_authorized": False}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package", required=True, type=Path)
    args = parser.parse_args()
    print(json.dumps(capture(args.package), ensure_ascii=False))


if __name__ == "__main__":
    main()
