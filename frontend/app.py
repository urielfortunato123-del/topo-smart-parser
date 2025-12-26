import base64
import json
import requests
import dash_leaflet as dl
from dash import Dash, html, dcc, Output, Input, State, no_update

API_URL = "http://backend:8000"  # no docker-compose; no Render você troca para URL pública

app = Dash(__name__)
server = app.server

app.layout = html.Div([
    html.H2("Topografia Inteligente (PDF/Imagem → Polígono)"),
    html.Div("Suba o arquivo (PDF ou Imagem) e o sistema já extrai e gera os arquivos."),
    dcc.Upload(
        id="upload",
        children=html.Div(["Arraste o arquivo aqui ou clique para selecionar"]),
        style={"width": "100%", "padding": "20px", "border": "2px dashed #999", "marginTop": "10px"},
        multiple=False,
        accept="application/pdf, image/*"
    ),
    html.Div([
        dcc.Input(id="utm_zone", type="number", placeholder="UTM zone (ex: 23)", style={"marginRight":"10px"}),
        dcc.Dropdown(
            id="force_mode",
            options=[{"label":"Auto", "value":""}, {"label":"UTM", "value":"utm"}, {"label":"Lon/Lat", "value":"lonlat"}],
            value="",
            style={"width":"220px", "display":"inline-block", "verticalAlign":"middle"}
        ),
    ], style={"marginTop":"10px"}),

    html.Button("Processar", id="btn", style={"marginTop":"10px"}),
    
    html.Div([
        dl.Map(
            id="map",
            center=[-23.55, -46.63],  # default SP
            zoom=12,
            style={"width": "100%", "height": "500px", "marginTop": "12px"},
            children=[
                dl.TileLayer(url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"),
                dl.LayerGroup(id="map_layer")
            ]
        ),
    ], id="map-container", style={"display": "none"}),

    html.Div(id="links", style={"marginTop":"10px"}),
    html.Pre(id="out", style={"whiteSpace":"pre-wrap", "marginTop":"10px"}),
])

@app.callback(
    Output("out", "children"),
    Output("links", "children"),
    Output("map_layer", "children"),
    Output("map", "center"),
    Output("map-container", "style"),
    Input("btn", "n_clicks"),
    State("upload", "contents"),
    State("upload", "filename"),
    State("utm_zone", "value"),
    State("force_mode", "value"),
    prevent_initial_call=True
)
def process(n, contents, filename, utm_zone, force_mode):
    if not contents:
        return "Envie um PDF primeiro.", "", [], no_update, {"display": "none"}

    head, b64 = contents.split(",", 1)
    mime = head.split(";")[0].split(":")[1]
    pdf_bytes = base64.b64decode(b64)

    cfg = {
        "utm_zone": utm_zone,
        "utm_south": True,
        "name": "Poligono",
        "force_mode": (force_mode or None)
    }

    files = {"file": (filename, pdf_bytes, mime)}
    data = {"cfg": json.dumps(cfg)}

    r = requests.post(f"{API_URL}/upload", files=files, data=data, timeout=120)
    if r.status_code != 200:
        return f"Erro: {r.status_code}\n{r.text}", "", [], no_update, {"display": "none"}

    j = r.json()
    
    # Gerar mapa (dash-leaflet)
    pts = j.get("points", [])
    center = j.get("center")
    
    map_children = []
    map_center = no_update
    
    if pts and center:
        # dash-leaflet usa [lat, lon]
        latlon = [[p[1], p[0]] for p in pts]
        map_children = [
            dl.Polygon(positions=latlon),
            dl.Marker(position=[center["lat"], center["lon"]]),
        ]
        map_center = [center["lat"], center["lon"]]

    gmaps_link = f"https://www.google.com/maps?q={center['lat']},{center['lon']}" if center else "#"

    links = html.Div([
        html.Div([
            html.A("Baixar KML", href=f"{API_URL}{j['outputs']['kml']}", target="_blank", className="btn-link"),
            html.A("Baixar KMZ", href=f"{API_URL}{j['outputs']['kmz']}", target="_blank", className="btn-link"),
            html.A("Baixar DXF UTM (CAD)", href=f"{API_URL}{j['outputs']['dxf_utm']}", target="_blank", className="btn-link"),
            html.A("Baixar DXF Lon/Lat", href=f"{API_URL}{j['outputs']['dxf_lonlat']}", target="_blank", className="btn-link"),
            html.A("Abrir no Google Maps", href=gmaps_link, target="_blank", className="btn-link", style={"backgroundColor":"#4285F4", "color":"white", "padding":"5px 10px", "borderRadius":"4px", "textDecoration":"none", "marginLeft":"20px"}),
        ], style={"display":"flex", "alignItems":"center", "gap":"12px", "flexWrap":"wrap"}),
        html.Div([
            html.B(f"Área: {j.get('area'):.2f} m² | Perímetro: {j.get('perimeter'):.2f} m"),
            html.Br(),
            html.Small(f"Job: {j.get('job_id')} | Detectado: {j.get('detected')}")
        ], style={"marginTop":"12px", "color":"#444"})
    ])

    return json.dumps(j, indent=2, ensure_ascii=False), links, map_children, map_center, {"display": "block"}

if __name__ == "__main__":
    app.run_server(host="0.0.0.0", port=8050, debug=True)
