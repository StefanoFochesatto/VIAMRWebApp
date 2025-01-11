import dash
from dash import dcc, html, Input, Output, State
import requests
import dash_vtk

app = dash.Dash(__name__)
server = app.server

# In Docker Compose, this might be "http://backend:5000"
BACKEND_URL = "http://localhost:5000"


app.layout = html.Div([
    html.H1("Dash VTK + PyVista (.vtu) Example"),

    # User input for 'resolution'
    html.Label("Resolution:"),
    dcc.Input(id="input-resolution", type="number", value=20),

    html.Button("Generate VTU Mesh", id="generate-mesh-btn", n_clicks=0),
    html.Br(), html.Br(),

    # Status feedback
    html.Div(id="status-div", style={"marginBottom": "20px"}),

    # Store the .vtu filename returned by the backend
    dcc.Store(id="vtu-filename-store"),

    # Dash VTK Visualization
    dash_vtk.View(
        children=[
            dash_vtk.GeometryRepresentation(
                id="vtk-geometry",
                children=[]
            )
        ],
        style={"width": "600px", "height": "400px"}
    ),
])


@app.callback(
    Output("vtu-filename-store", "data"),
    Output("status-div", "children"),
    Input("generate-mesh-btn", "n_clicks"),
    State("input-resolution", "value"),
    prevent_initial_call=True
)
def on_generate_mesh(n_clicks, resolution):
    """
    1) POST resolution to the backend's /generate_vtu endpoint.
    2) Backend generates .vtu, returns filename.
    3) Store filename in dcc.Store and show status in UI.
    """
    try:
        resp = requests.post(
            f"{BACKEND_URL}/generate_vtu",
            json={"resolution": resolution},
            timeout=10
        )
        resp.raise_for_status()
        data = resp.json()
        filename = data.get("filename", "")
        return filename, f"Mesh generated: {filename}"
    except Exception as e:
        return "", f"Error: {e}"


@app.callback(
    Output("vtk-geometry", "children"),
    Input("vtu-filename-store", "data")
)
def update_vtk_reader(filename):
    """
    Once we have a .vtu filename, point dash_vtk.VTKReader to /data/<filename> 
    on the backend to load the mesh.
    """
    if filename:
        # e.g. "my_sphere.vtu"
        file_url = f"{BACKEND_URL}/data/{filename}"
        return [
            dash_vtk.VTKReader(
                vtkUrl=file_url  # This fetches the file from the backend
            )
        ]
    return []


if __name__ == "__main__":
    app.run_server(host="0.0.0.0", port=8050, debug=True)
