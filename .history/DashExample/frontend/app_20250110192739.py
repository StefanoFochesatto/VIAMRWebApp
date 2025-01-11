import dash
from dash import dcc, html, Input, Output, State
import requests
import dash_vtk

app = dash.Dash(__name__)
server = app.server

# In Docker Compose, "backend" is the service name
BACKEND_URL = "http://backend:5000"

app.layout = html.Div([
    html.H1("Dash VTK + PyVista VTU Example"),
    html.Div([
        html.Label("Resolution:"),
        dcc.Input(id="input-resolution", type="number", value=20),
        html.Button("Generate Mesh", id="generate-mesh-btn", n_clicks=0),
    ], style={"marginBottom": "20px"}),

    html.Div(id="status-div", style={"marginBottom": "20px"}),

    # Store the generated file name (vtu) here
    dcc.Store(id="vtu-filename-store"),

    # Dash VTK component
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
    When 'Generate Mesh' is clicked, POST the resolution parameter
    to the backend. The backend will generate a .vtu file and return
    the filename.
    """
    try:
        resp = requests.post(
            f"{BACKEND_URL}/generate_vtu",
            json={"resolution": resolution},
            timeout=10
        )
        resp.raise_for_status()  # throw if not 200
        data = resp.json()
        filename = data.get("filename", "")
        return filename, f"Mesh generated: {filename}"
    except Exception as e:
        return "", f"Error from backend: {e}"


@app.callback(
    Output("vtk-geometry", "children"),
    Input("vtu-filename-store", "data")
)
def update_vtk_reader(filename):
    """
    After the .vtu file is generated, dash_vtk can read it from
    /data/<filename> in the backend.
    """
    if filename:
        file_url = f"{BACKEND_URL}/data/{filename}"
        return [
            dash_vtk.VTKReader(
                vtkUrl=file_url  # Path to the .vtu file served by the backend
            )
        ]
    return []  # no file yet


if __name__ == "__main__":
    app.run_server(host="0.0.0.0", port=8050, debug=True)
