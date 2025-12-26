from __future__ import annotations
import re
from dataclasses import dataclass
from typing import List, Tuple, Optional

import pdfplumber

# Heurística simples e prática:
# - captura pares numéricos com separador ponto ou vírgula
# - tenta detectar se parece UTM (6-7 dígitos + 7 dígitos) ou Lat/Lon (-xx.xxxxxx)
PAIR_RE = re.compile(
    r"(?P<a>-?\d{1,3}(?:[.,]\d+)?)\s*[,;\s]\s*(?P<b>-?\d{1,3}(?:[.,]\d+)?)"
)
UTM_PAIR_RE = re.compile(
    r"(?P<e>\d{6,7}(?:[.,]\d+)?)\s*[,;\s]\s*(?P<n>\d{6,8}(?:[.,]\d+)?)"
)

def _to_float(s: str) -> float:
    return float(s.replace(".", "").replace(",", ".")) if ("," in s and s.count(",") == 1 and s.count(".") >= 1) else float(s.replace(",", "."))

@dataclass
class ParsedPDF:
    raw_text: str
    utm_points: List[Tuple[float, float]]
    lonlat_points: List[Tuple[float, float]]
    hint: str  # "utm" | "lonlat" | "unknown"

def extract_text(pdf_path: str) -> str:
    text_parts = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            t = page.extract_text() or ""
            if t.strip():
                text_parts.append(t)
    return "\n".join(text_parts)

def parse_points_from_text(text: str) -> ParsedPDF:
    utm = []
    lonlat = []

    for m in UTM_PAIR_RE.finditer(text):
        e = _to_float(m.group("e"))
        n = _to_float(m.group("n"))
        # filtro bem prático pra evitar lixo
        if 100000 <= e <= 9999999 and 0 <= n <= 99999999:
            utm.append((e, n))

    for m in PAIR_RE.finditer(text):
        a = _to_float(m.group("a"))
        b = _to_float(m.group("b"))
        # provável lat/lon (Brasil)
        if -35 <= a <= 6 and -75 <= b <= -30:
            lonlat.append((b, a))  # armazeno (lon, lat)
        elif -35 <= b <= 6 and -75 <= a <= -30:
            lonlat.append((a, b))

    hint = "unknown"
    if len(utm) >= 3 and len(utm) >= len(lonlat):
        hint = "utm"
    elif len(lonlat) >= 3:
        hint = "lonlat"

    return ParsedPDF(raw_text=text, utm_points=utm, lonlat_points=lonlat, hint=hint)
