#!/usr/bin/env python3
"""Baixa SOMENTE o ITENS_PROVA de um microdados_enem_ANO.zip do Inep, por HTTP range.

O zip inteiro (500+ MB) não é baixado: lê-se o diretório central no fim do arquivo e só os
bytes comprimidos da entrada ITENS_PROVA_*.csv. Grava o CSV bruto (para conferência do SHA-256)
e uma versão mínima com as colunas de identidade, sem dados de participantes.

Uso:
  python scripts/fetch_inep_itens_prova.py --year 2023 --out-dir DIR [--ca-bundle data/certificates/inep-ca-bundle.pem]
"""
import argparse
import csv
import hashlib
import io
import ssl
import struct
import urllib.request
import zlib
from pathlib import Path

URL = "https://download.inep.gov.br/microdados/microdados_enem_{year}.zip"
KEEP = ("CO_PROVA", "TX_COR", "CO_POSICAO", "CO_ITEM", "SG_AREA", "TX_GABARITO", "IN_ITEM_ABAN", "TX_MOTIVO_ABAN",
        "CO_HABILIDADE", "IN_ITEM_ADAPTADO", "TP_LINGUA")


def get(url, ctx, start=None, end=None):
    headers = {"User-Agent": "Mozilla/5.0"}
    if start is not None:
        headers["Range"] = f"bytes={start}-{'' if end is None else end}"
    with urllib.request.urlopen(urllib.request.Request(url, headers=headers), context=ctx, timeout=120) as r:
        return r.read(), r.status


def size_of(url, ctx):
    with urllib.request.urlopen(urllib.request.Request(url, method="HEAD", headers={"User-Agent": "Mozilla/5.0"}),
                                context=ctx, timeout=60) as r:
        assert r.headers.get("Accept-Ranges") == "bytes", "servidor sem suporte a range"
        return int(r.headers["Content-Length"])


def central_directory(url, ctx, total):
    tail_len = 1 << 16
    tail, _ = get(url, ctx, total - tail_len, total - 1)
    i = tail.rfind(b"PK\x05\x06")
    assert i >= 0, "EOCD não encontrado"
    _, _, _, n_here, n_total, cd_size, cd_off, _ = struct.unpack("<4s4H2LH", tail[i:i + 22])
    assert cd_off != 0xFFFFFFFF, "zip64 não suportado"
    data, _ = get(url, ctx, cd_off, cd_off + cd_size - 1)
    pos, entries = 0, []
    while pos < len(data) and data[pos:pos + 4] == b"PK\x01\x02":
        (_, _, _, flags, method, _, _, crc, csize, usize, nlen, elen, clen, _, _, _, loff) = struct.unpack("<4s6H3L5H2L", data[pos:pos + 46])
        name = data[pos + 46:pos + 46 + nlen].decode("cp437" if not flags & 0x800 else "utf-8")
        entries.append(dict(name=name, method=method, crc=crc, csize=csize, usize=usize, offset=loff))
        pos += 46 + nlen + elen + clen
    return entries


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--year", type=int, required=True)
    ap.add_argument("--out-dir", type=Path, required=True)
    ap.add_argument("--ca-bundle", default="data/certificates/inep-ca-bundle.pem")
    args = ap.parse_args()
    url = URL.format(year=args.year)
    ctx = ssl.create_default_context(cafile=args.ca_bundle)
    total = size_of(url, ctx)
    entries = [e for e in central_directory(url, ctx, total) if "ITENS_PROVA" in e["name"].upper() and e["name"].lower().endswith(".csv")]
    assert len(entries) == 1, [e["name"] for e in entries]
    e = entries[0]
    head, _ = get(url, ctx, e["offset"], e["offset"] + 29)
    nlen, elen = struct.unpack("<2H", head[26:30])
    start = e["offset"] + 30 + nlen + elen
    comp, _ = get(url, ctx, start, start + e["csize"] - 1)
    raw = zlib.decompress(comp, -15) if e["method"] == 8 else comp
    assert len(raw) == e["usize"] and zlib.crc32(raw) & 0xFFFFFFFF == e["crc"], "CRC/tamanho divergentes"
    args.out_dir.mkdir(parents=True, exist_ok=True)
    (args.out_dir / f"ITENS_PROVA_{args.year}.csv").write_bytes(raw)
    text = raw.decode("latin-1")
    rows = list(csv.DictReader(io.StringIO(text), delimiter=";", quoting=csv.QUOTE_NONE))
    cols = [c for c in KEEP if c in rows[0]]
    with (args.out_dir / f"itens-prova-{args.year}.min.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh, delimiter=";")
        w.writerow(cols)
        for r in rows:
            w.writerow([r[c] for c in cols])
    print(f"{args.year}: {e['name']} usize={e['usize']} csize={e['csize']} sha256={hashlib.sha256(raw).hexdigest()} "
          f"linhas={len(rows)} colunas_mantidas={cols}")


if __name__ == "__main__":
    main()
