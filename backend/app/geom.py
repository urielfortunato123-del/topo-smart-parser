from __future__ import annotations
from dataclasses import dataclass
from typing import List, Tuple, Optional
from shapely.geometry import Polygon

@dataclass
class PolygonResult:
    points: List[Tuple[float, float]]  # (x, y) in chosen CRS
    is_closed: bool
    area: float
    perimeter: float

def build_polygon(points: List[Tuple[float, float]]) -> PolygonResult:
    if len(points) < 3:
        raise ValueError("Precisa de pelo menos 3 pontos pra formar polígono.")
    # Fecha se necessário
    is_closed = points[0] == points[-1]
    pts = points[:] if is_closed else points + [points[0]]
    poly = Polygon(pts)
    if not poly.is_valid:
        # tenta “consertar” auto-interseção leve
        poly = poly.buffer(0)
    if not poly.is_valid or poly.area == 0:
        raise ValueError("Polígono inválido (auto-interseção grave ou área zero).")
    return PolygonResult(points=pts, is_closed=True, area=float(poly.area), perimeter=float(poly.length))
