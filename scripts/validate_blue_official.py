#!/usr/bin/env python3
"""Read-only official-PDF evidence audit of 2017-2025 blue staging.

Independently parses official PDF page geometry using PyMuPDF; never approves
a question for publication or treats token agreement as visual fidelity.
Requires: python3 -m pip install pymupdf
"""
import argparse
from collections import Counter, defaultdict
from difflib import SequenceMatcher
import hashlib
import json
from pathlib import Path
import re
import unicodedata

try:
    import fitz
except ImportError as exc:
    raise SystemExit("Install PyMuPDF: python3 -m pip install pymupdf") from exc

HEADING = re.compile(r"^QUEST[ÃA]O\s+(\d{1,3})$", re.I)
LETTERS = "ABCDE"

def tokens(value):
    value = unicodedata.normalize("NFKD", str(value or "")).casefold()
    value = "".join(c for c in value if not unicodedata.combining(c))
    return re.findall(r"[a-z0-9]+", value)

def contains_sequence(needle, haystack):
    n = len(needle)
    return bool(n and any(haystack[i:i+n] == needle
                          for i in range(len(haystack)-n+1)))

def evidence(haystack, needle):
    """Find localized source PDF excerpt; never use fuzzy match for approval."""
    if not needle or not haystack:
        return {"similarity": 0, "record_excerpt": " ".join(needle[:50]),
                "pdf_excerpt": "", "token_differences": []}
    matcher = SequenceMatcher(None, needle, haystack, autojunk=False)
    anchors = sorted((b for b in matcher.get_matching_blocks() if b.size >= 2),
                     key=lambda b: b.size, reverse=True)[:7]
    offsets = {max(0, b.b-b.a) for b in anchors} or {0}
    starts = {min(max(0, offset+d), max(0,len(haystack)-len(needle)))
              for offset in offsets for d in (-4,-2,0,2,4)}
    score,position,window = -1,0,[]
    for start in sorted(starts):
        candidate = haystack[start:start+len(needle)]
        value = SequenceMatcher(None,needle,candidate,autojunk=False).ratio()
        if value > score:
            score,position,window = value,start,candidate
    changes = []
    for op,a,b,c,d in SequenceMatcher(None,needle,window,autojunk=False).get_opcodes():
        if op != "equal":
            changes.append({"operation":op,"record":" ".join(needle[a:b])[:160],
                            "pdf":" ".join(window[c:d])[:160]})
    return {"similarity": round(score,4),
            "record_excerpt": " ".join(needle[:55])[:450],
            "pdf_excerpt": " ".join(window[:55])[:450],
            "token_differences": changes[:8]}

def headings(page):
    found=[]
    for block in page.get_text("dict")["blocks"]:
        if block.get("type") != 0: continue
        for line in block["lines"]:
            text="".join(s["text"] for s in line["spans"]).strip()
            match=HEADING.fullmatch(text)
            if match:
                found.append({"number":int(match.group(1)),
                              "x":float(line["bbox"][0]),
                              "y":float(line["bbox"][1])})
    return found

def regions_for_page(page, page_no):
    found=headings(page)
    width,height=page.rect.width,page.rect.height
    mid=width/2
    top,bottom=57,min(height-35,742)
    right_text=sum(len(span["text"].strip())
                   for block in page.get_text("dict")["blocks"]
                   if block.get("type")==0
                   for line in block["lines"] for span in line["spans"]
                   if span["bbox"][0]>mid+9 and top<span["bbox"][1]<bottom)
    columns=([("left",24,mid-4),("right",mid+1,width-25)]
             if any(h["x"]>mid for h in found) or right_text>120
             else [("full",24,width-25)])
    regions=[]
    for side,x0,x1 in columns:
        hs=sorted((h for h in found if side=="full" or
                   (h["x"]<mid)==(side=="left")),key=lambda h:h["y"])
        if not hs: continue
        if hs[0]["y"]>top+4:
            box=[x0,top,x1,hs[0]["y"]-.5]
            prefix=page.get_text("text",clip=fitz.Rect(box)).strip()
            if len(prefix)>18:
                regions.append({"number":None,"page":page_no,"column":side,
                                "bbox":box,"is_prefix":True})
        for i,h in enumerate(hs):
            end=hs[i+1]["y"]-.5 if i+1<len(hs) else bottom
            if end<=h["y"]-2: continue
            regions.append({"number":h["number"],"page":page_no,
                            "column":side,"bbox":[x0,h["y"]-2,x1,end],
                            "is_prefix":False})
    return regions

class PDFSource:
    def __init__(self,path):
        self.path=Path(path)
        self.sha256=hashlib.sha256(self.path.read_bytes()).hexdigest()
        self.doc=fitz.open(self.path)
        self.by_number=defaultdict(list)
        current=None
        for page_no,page in enumerate(self.doc,1):
            for region in regions_for_page(page,page_no):
                if region["number"] is not None:
                    current={"regions":[],"warnings":[]}
                    self.by_number[region["number"]].append(current)
                if current is not None:
                    if region["number"] is None:
                        current["warnings"].append("POSSIBLE_COLUMN_OR_PAGE_CONTINUATION")
                    current["regions"].append(region)

    def get(self,position):
        matches=self.by_number.get(position,[])
        if len(matches)!=1:
            return None,"HEADER_ABSENT" if not matches else "HEADER_DUPLICATED"
        item=matches[0]
        fragments=[]
        for r in item["regions"]:
            words=self.doc[r["page"]-1].get_text("words",clip=fitz.Rect(r["bbox"]),sort=True)
            words.sort(key=lambda w:(w[5],w[6],w[7]))
            fragments.extend(str(w[4]) for w in words)
        return {"tokens":tokens(" ".join(fragments)),
                "regions":item["regions"],"warnings":item["warnings"]},None

    def close(self):
        self.doc.close()

def compare_text(q,src):
    content=q.get("conteudo") or {}
    options=content.get("alternativas") or {}
    fields={"texto_base":content.get("texto_base"),"enunciado":content.get("enunciado")}
    fields.update({f"alternativa_{k}":options.get(k) for k in LETTERS})
    checks=[]
    for field,value in fields.items():
        needle=tokens(value)
        if not needle:
            if field!="texto_base":
                checks.append({"field":field,"status":"EMPTY_FIELD"})
        elif contains_sequence(needle,src["tokens"]):
            checks.append({"field":field,"status":"EXACT_TOKEN_SEQUENCE","tokens":len(needle)})
        else:
            checks.append({"field":field,"status":"NOT_EXACT",
                           "tokens":len(needle),"evidence":evidence(src["tokens"],needle)})
    misses=[c for c in checks if c["status"]!="EXACT_TOKEN_SEQUENCE"]
    if not misses:
        status="TEXT_MATCH_VISUAL_UNVERIFIED"
    elif any(c["status"]=="NOT_EXACT" and c["evidence"]["similarity"]>=.75
             for c in misses):
        status="SUSPECTED_TEXT_DIVERGENCE"
    else:
        status="TEXT_INCONCLUSIVE"
    visual=["PDF_GRAPHICS_FORMULAS_NOT_SEMANTICALLY_VERIFIED"]
    meta=content.get("metadados_visual") or {}
    if meta.get("contem_imagem") and not meta.get("caminho_local_imagem"):
        visual.append("DECLARED_IMAGE_WITHOUT_LOCAL_ASSET")
    return status,checks,visual

def compare_candidate(extraction,src):
    segmentation=extraction.get("option_segmentation") or {}
    options=segmentation.get("options") or {}
    if set(options)!=set(LETTERS):
        return "CANDIDATE_OPTIONS_INCOMPLETE",[]
    checks=[]
    for letter in LETTERS:
        needle=tokens(options[letter])
        if contains_sequence(needle,src["tokens"]):
            checks.append({"field":letter,"status":"EXACT_TOKEN_SEQUENCE"})
        else:
            checks.append({"field":letter,"status":"NOT_EXACT",
                           "evidence":evidence(src["tokens"],needle)})
    return ("CANDIDATE_OPTIONS_TEXT_MATCH_ONLY" if all(
            c["status"]=="EXACT_TOKEN_SEQUENCE" for c in checks)
            else "CANDIDATE_OPTIONS_NEED_RECOVERY"),checks

def audit(rows):
    cache={}
    results=[]
    try:
        for row in rows:
            output={"ano":row["ano"],"dia":row["dia"],"posicao":row["posicao"],
                    "publishable":False,"full_fidelity_verified":False,
                    "answer_verified":False,"tri_verified":False}
            pdf=row.get("official_pdf")
            if not pdf or not Path(pdf).is_file():
                output["status"]="SOURCE_MISSING"
                results.append(output);continue
            if pdf not in cache:
                cache[pdf]=PDFSource(pdf)
            source=cache[pdf]
            output["source_pdf_sha256"]=source.sha256
            region,error=source.get(row["posicao"])
            if error:
                output.update(status="INCONCLUSIVE",reason=error)
                results.append(output);continue
            output["source_regions"]=region["regions"]
            output["region_warnings"]=region["warnings"]
            output["source_token_count"]=len(region["tokens"])
            existing=row.get("existing_records") or []
            if len(existing)>1:
                output.update(status="INCONCLUSIVE",reason="DUPLICATED_RECORDS")
            elif existing:
                record=existing[0]["record"]
                status,checks,visual=compare_text(record,region)
                output.update(status=status,record_id=record.get("id_unico_sistema"),
                              recorded_answer=record.get("gabarito_oficial"),
                              text_evidence=checks,visual_warnings=visual)
                if row.get("extraction"):
                    candidate_status,candidate_checks=compare_candidate(row["extraction"],region)
                    output["refresh_candidate_status"]=candidate_status
                    output["refresh_candidate_checks"]=candidate_checks
                if region["warnings"] and status=="TEXT_MATCH_VISUAL_UNVERIFIED":
                    output["status"]="INCONCLUSIVE_REGION_BOUNDARY"
            elif row.get("extraction"):
                status,checks=compare_candidate(row["extraction"],region)
                output.update(status=status,text_evidence=checks,
                              reason="Stem, support text and graphics not independently reconstructed")
            else:
                output.update(status="INCONCLUSIVE",reason="NO_RECORD_OR_CANDIDATE")
            results.append(output)
    finally:
        for source in cache.values():
            source.close()
    return results

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--input",type=Path,default=Path("data/blue-staging/blue-candidates.jsonl"))
    ap.add_argument("--output-dir",type=Path,default=Path("data/blue-staging"))
    args=ap.parse_args()
    output=args.output_dir
    if args.input.resolve() in [(output/"official-validation.jsonl").resolve(),
                                (output/"official-validation-summary.json").resolve()]:
        ap.error("Refusing input/output collision")
    with args.input.open(encoding="utf-8") as f:
        results=audit(json.loads(line) for line in f if line.strip())
    output.mkdir(parents=True,exist_ok=True)
    detail=output/"official-validation.jsonl"
    with detail.open("w",encoding="utf-8") as f:
        for item in results:
            f.write(json.dumps(item,ensure_ascii=False)+"\n")
    summary={"read_only":True,"total":len(results),
             "summary":dict(Counter(item["status"] for item in results)),
             "full_fidelity_validated":0,"answers_validated":0,"tri_validated":0,
             "warning":"PDF text compatibility is not complete fidelity; images, formulas, credits and official keys remain unverified.",
             "details":str(detail)}
    (output/"official-validation-summary.json").write_text(
        json.dumps(summary,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps(summary,ensure_ascii=False,indent=2))

if __name__=="__main__":
    main()
