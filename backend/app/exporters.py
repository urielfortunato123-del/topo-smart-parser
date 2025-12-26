from __future__ import annotations
from pathlib import Path
from typing import List, Tuple, Optional
import zipfile

import simplekml
import ezdxf

def export_kml(points_lonlat: List[Tuple[float, float]], out_file: Path, name: str = "Poligono") -> None:
    kml = simplekml.Kml()
    pol = kml.newpolygon(name=name)
    pol.outerboundaryis = [(lon, lat) for lon, lat in points_lonlat]
    pol.style.polystyle.fill = 1
    pol.style.polystyle.outline = 1
    kml.save(str(out_file))

def export_kmz(kml_file: Path, out_file: Path) -> None:
    with zipfile.ZipFile(out_file, "w", compression=zipfile.ZIP_DEFLATED) as z:
        z.write(kml_file, arcname="doc.kml")

def export_dxf(points_xy: List[Tuple[float, float]], out_file: Path, layer: str = "POLIGONO") -> None:
    doc = ezdxf.new(setup=True)
    msp = doc.modelspace()
    # layer
    if layer not in doc.layers:
        doc.layers.new(name=layer)
    # polyline (closed)
    msp.add_lwpolyline(points_xy, close=True, dxfattribs={"layer": layer})
    doc.saveas(str(out_file))
