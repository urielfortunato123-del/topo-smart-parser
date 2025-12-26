# PDF → Polígono (KML/KMZ/DXF)

Sistema que recebe um PDF (memorial / matrícula / topografia), extrai coordenadas e gera automaticamente:
- KML
- KMZ
- DXF (para CAD)

## Rodar local (Docker)
```bash
docker compose up --build
```

Frontend: http://localhost:8050

Backend: http://localhost:8000/docs

Sobre DWG

DWG é formato proprietário. O padrão recomendado é gerar DXF e converter para DWG via ODA File Converter ou AutoCAD.
