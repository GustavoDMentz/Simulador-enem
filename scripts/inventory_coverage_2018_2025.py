#!/usr/bin/env python3
"""Read-only inventory of missing ENEM blue-booklet positions, 2018–2025."""
import argparse
import json
import re
from collections import defaultdict
from pathlib import Path

def inventory(manifest_path, fused_dir):
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    authorized = {q["id"] for q in manifest["questions"] if q.get("publication_authorized")}
    fused = defaultdict(list)
    for path in sorted(fused_dir.glob("*.jsonl")):
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            q = json.loads(line)
            year, day, pos = q.get("ano"), q.get("dia"), q.get("posicao_prova")
            if isinstance(year, int) and isinstance(day, int) and isinstance(pos, int) and q.get("cor_prova") == "AZUL":
                fused[(year, day, pos)].append(q.get("id_unico_sistema"))
    positions = []
    totals = defaultdict(lambda: {"authorized": 0, "fused_only": 0, "absent": 0, "multiple_fused": 0})
    for year in range(2018, 2026):
        for day in (1, 2):
            for pos in range(1 if day == 1 else 91, 91 if day == 1 else 181):
                key = (year, day, pos)
                canonical = f"{year}_AZUL_D{day}_Q{pos:02d}"
                records = fused[key]
                status = "AUTHORIZED" if canonical in authorized else "FUSED_UNREVIEWED" if records else "ABSENT_FROM_FUSED"
                totals[year][{"AUTHORIZED":"authorized","FUSED_UNREVIEWED":"fused_only","ABSENT_FROM_FUSED":"absent"}[status]] += 1
                if len(records) > 1:
                    totals[year]["multiple_fused"] += 1
                positions.append({"year":year,"day":day,"position":pos,"id":canonical,"status":status,"fused_ids":records})
    return {"read_only":True,"scope":"ENEM 2018-2025 blue booklet; 1440 positions","caveats":["Fused records are NOT authorized for publication.","Annullments and language variants require independent verification.","A digital exam is not interchangeable with a regular exam."],"summary":[{"year":y,**totals[y]} for y in range(2018,2026)],"positions":positions}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--manifest",type=Path,default=Path("data/audit/manifest.json"))
    ap.add_argument("--fused",type=Path,default=Path("data/fused"))
    ap.add_argument("--output",type=Path,default=Path("/tmp/enem-coverage-2018-2025.json"))
    args=ap.parse_args()
    result=inventory(args.manifest,args.fused)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    for row in result["summary"]:
        print("{year}: approved={authorized} fused_pending={fused_only} absent={absent} duplicates={multiple_fused}".format(**row))
    print("Saved:",args.output)

if __name__=="__main__":
    main()
