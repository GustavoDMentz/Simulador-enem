#!/usr/bin/env python3
"""Run a complete read-only ENEM blue audit using already-downloaded official PDFs.

Does not download, modify fused data, contact ArangoDB, or publish.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]

def inspect_sources(folder):
    sources = []
    for year in range(2017, 2026):
        for day in (1, 2):
            item = {"ano":year,"dia":day}
            for kind, suffix in (("prova",""),("gabarito","-gabarito")):
                path = folder / f"{year}-regular-d{day}-azul{suffix}.pdf"
                if not path.is_file():
                    item[kind] = {"status":"MISSING"}
                    continue
                with path.open("rb") as f:
                    header=f.read(8)
                    f.seek(0)
                    digest=hashlib.file_digest(f,"sha256").hexdigest()
                if not header.startswith(b"%PDF-"):
                    item[kind]={"status":"INVALID_HEADER","file":str(path)}
                    continue
                item[kind]={"status":"PRESENT_UNVERIFIED_ORIGIN","file":str(path),
                            "size":path.stat().st_size,"sha256":digest}
            sources.append(item)
    return sources

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--pdf-dir",type=Path,default=ROOT/"data/enem-pdfs/oficiais")
    p.add_argument("--fused",type=Path,default=ROOT/"data/fused")
    p.add_argument("--output-dir",type=Path,default=ROOT/"data/blue-staging")
    p.add_argument("--refresh",action="store_true",help="Extract PDF candidates for existing records too")
    p.add_argument("--require-complete",action="store_true",
                   help="Fail if any of the 18 exam PDFs or 18 keys is absent")
    args=p.parse_args()
    pdf_dir=args.pdf_dir.resolve()
    fused=args.fused.resolve()
    output=args.output_dir.resolve()
    if output==fused or fused in output.parents or output==pdf_dir or pdf_dir in output.parents:
        p.error("Output must be outside original fused data and official PDF directory")
    if not fused.is_dir():
        p.error(f"Fused source directory missing: {fused}")
    sources=inspect_sources(pdf_dir)
    missing=[{"ano":s["ano"],"dia":s["dia"],"tipo":k,"status":s[k]["status"]}
             for s in sources for k in ("prova","gabarito") if s[k]["status"]!="PRESENT_UNVERIFIED_ORIGIN"]
    output.mkdir(parents=True,exist_ok=True)
    inventory={"source_count":36,"present":36-len(missing),"missing_or_invalid":missing,
               "sources":sources,"origin_verified":False,
               "warning":"PDF magic bytes and SHA-256 do not prove official provenance."}
    (output/"local-source-inventory.json").write_text(
        json.dumps(inventory,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(f"Official PDF inventory: {inventory['present']}/36 present (provenance not verified)")
    if args.require_complete and missing:
        raise SystemExit(f"FAIL CLOSED: {len(missing)} PDF sources absent/invalid; see inventory")
    command=[sys.executable,str(ROOT/"scripts/rebuild_blue.py"),"--all",
             "--fused",str(fused),"--pdf-dir",str(pdf_dir),"--output-dir",str(output)]
    if args.refresh:
        command.append("--refresh")
    subprocess.run(command,cwd=ROOT,check=True)
    summary_path=output/"audit-matrix-summary.json"
    if not summary_path.is_file():
        raise SystemExit("FAIL CLOSED: audit matrix missing")
    summary=json.loads(summary_path.read_text(encoding="utf-8"))
    if summary.get("positions_reported")!=1620 or summary.get("publishable")!=0:
        raise SystemExit("FAIL CLOSED: invalid audit matrix")
    print("Read-only evidence complete; publication remains blocked.")
    print(json.dumps({"sources_present":inventory["present"],"positions":1620,
                      "priority_counts":summary.get("priority_counts",{}),
                      "output_dir":str(output)},ensure_ascii=False,indent=2))

if __name__=="__main__":
    main()
