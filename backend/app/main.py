from __future__ import annotations
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from pathlib import Path
from typing import Optional, List, Tuple
import json

from .storage import ensure_dirs, new_job_id, job_dir, upload_path
from .parser import extract_text, parse_points_from_text
from .geom import build_polygon
from .exporters import export_kml, export_kmz, export_dxf
from pyproj import Transformer

app = FastAPI(title="PDF → Poligono (KML/KMZ/DXF)", version="1.1.0")

class ProcessRequest(BaseModel):
    # Se o PDF for UTM e você souber a zona (SP geralmente 23S), informe aqui
    utm_zone: Optional[int] = None
    utm_south: bool = True
    name: str = "Poligono"

class JobResponse(BaseModel):
    job_id: str
    detected: str
    points_count: int
    points: List[Tuple[float, float]]  # (lon, lat) para o mapa
    center: dict # {"lat": ..., "lon": ...}
    area: float
    perimeter: float
    outputs: dict

@app.on_event("startup")
def _startup():
    ensure_dirs()

def _epsg_utm(zone: int, south: bool) -> str:
    return f"EPSG:{32700 + zone}" if south else f"EPSG:{32600 + zone}"

@app.post("/upload", response_model=JobResponse)
async def upload_and_process(
    file: UploadFile = File(...),
    cfg: str = File(""),
):
    try:
        data = json.loads(cfg) if cfg else {}
        req = ProcessRequest(**data)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"cfg inválido: {e}")

    job_id = new_job_id()
    up = upload_path(job_id, file.filename)
    up.write_bytes(await file.read())

    text = extract_text(str(up))
    parsed = parse_points_from_text(text)

    # Decide pontos "base" detectados
    if parsed.hint == "utm" and len(parsed.utm_points) >= 3:
        base_mode = "utm"
        base_pts = parsed.utm_points
    elif parsed.hint == "lonlat" and len(parsed.lonlat_points) >= 3:
        base_mode = "lonlat"
        base_pts = parsed.lonlat_points
    else:
        raise HTTPException(
            status_code=422,
            detail="Não reconheci coordenadas suficientes no PDF (preciso de pelo menos 3 pontos)."
        )

    outdir = job_dir(job_id)

    outputs = {
        # downloads (você escolhe qual clicar)
        "kml": f"/download/{job_id}/kml",
        "kmz": f"/download/{job_id}/kmz",
        "dxf_utm": f"/download/{job_id}/dxf_utm",
        "dxf_lonlat": f"/download/{job_id}/dxf_lonlat",
    }

    # 1) Constrói polígono na base detectada
    poly = build_polygon(base_pts)

    # 2) Sempre produzir Lon/Lat fechado (EPSG:4326) pra KML
    if base_mode == "lonlat":
        pts_lonlat = poly.points  # (lon, lat)
        # Se tiver zona UTM, também gera UTM "certo". Se não, usa 3857 só pra DXF
        if req.utm_zone:
            tr_to_utm = Transformer.from_crs("EPSG:4326", _epsg_utm(req.utm_zone, req.utm_south), always_xy=True)
            pts_utm = [tr_to_utm.transform(lon, lat) for lon, lat in pts_lonlat]
        else:
            pts_utm = None
    else:
        # base UTM -> converte para lonlat (pra KML) exige zona
        if not req.utm_zone:
            raise HTTPException(
                status_code=422,
                detail="Detectei UTM no PDF, mas você não informou utm_zone. Ex: 23 (SP)."
            )
        pts_utm = poly.points  # (E, N)
        tr_to_lonlat = Transformer.from_crs(_epsg_utm(req.utm_zone, req.utm_south), "EPSG:4326", always_xy=True)
        pts_lonlat = [tr_to_lonlat.transform(e, n) for (e, n) in pts_utm]  # (lon, lat)

    # 3) KML + KMZ sempre (base lonlat)
    kml_path = outdir / "poligono.kml"
    kmz_path = outdir / "poligono.kmz"
    export_kml(pts_lonlat, kml_path, name=req.name)
    export_kmz(kml_path, kmz_path)

    # 4) DXF em Lon/Lat (não é “métrico”, mas você pediu ambos)
    dxf_lonlat = outdir / "poligono_lonlat.dxf"
    export_dxf(pts_lonlat, dxf_lonlat, layer="POLIGONO_LONLAT")

    # 5) DXF em UTM (métrico e perfeito pra CAD)
    # Se não tiver zona e base for lonlat, eu gero em 3857 (métrico aproximado) e deixo explícito no nome
    if pts_utm is not None:
        dxf_utm = outdir / "poligono_utm.dxf"
        export_dxf(pts_utm, dxf_utm, layer="POLIGONO_UTM")
    else:
        tr_3857 = Transformer.from_crs("EPSG:4326", "EPSG:3857", always_xy=True)
        pts_3857 = [tr_3857.transform(lon, lat) for lon, lat in pts_lonlat]
        dxf_utm = outdir / "poligono_mercator_3857.dxf"
        export_dxf(pts_3857, dxf_utm, layer="POLIGONO_3857")

    lons = [p[0] for p in pts_lonlat]
    lats = [p[1] for p in pts_lonlat]
    center = {"lon": sum(lons)/len(lons), "lat": sum(lats)/len(lats)}

    return JobResponse(
        job_id=job_id,
        detected=base_mode,
        points_count=len(poly.points),
        points=pts_lonlat,
        center=center,
        area=poly.area,
        perimeter=poly.perimeter,
        outputs=outputs
    )

@app.get("/download/{job_id}/{fmt}")
def download(job_id: str, fmt: str):
    outdir = Path("data/outputs") / job_id
    if not outdir.exists():
        raise HTTPException(status_code=404, detail="Job não encontrado.")

    mapping = {
        "kml": "poligono.kml",
        "kmz": "poligono.kmz",
        "dxf_lonlat": "poligono_lonlat.dxf",
        "dxf_utm": "poligono_utm.dxf",
    }

    # fallback se gerou 3857 por falta de zona
    if fmt == "dxf_utm" and not (outdir / mapping["dxf_utm"]).exists():
        mapping["dxf_utm"] = "poligono_mercator_3857.dxf"

    if fmt not in mapping:
        raise HTTPException(status_code=400, detail="Formato inválido.")

    f = outdir / mapping[fmt]
    if not f.exists():
        raise HTTPException(status_code=404, detail="Arquivo não gerado.")
    return FileResponse(str(f), filename=f.name)
