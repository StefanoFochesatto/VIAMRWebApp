import os
import dash
from dash import dcc, html, Input, Output, State
import requests
import pyvista as pv
import dash_vtk

app = dash.Dash(__name__)
server = app.server

# In Docker Compose, the backend is http://backend:5000
BACKEND_URL = "http://backend:5000"

# We'll read .vtu files from here
DATA_DIR = "/app/shared_data"


def load_vtu_with_pyvista(filename):
    """
    Load a .vtu file from DATA_DIR with PyVista,
    convert it to dash_vtk geometry, return.
    """
    filepath = os.path.join(DATA_DIR, filename)
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"File {filepath} not found.")

    # 1) Read the .vtu with PyVista
    mesh = pv.UnstructuredGrid(filepath)

    # 2) Extract geometry arrays
    #    Points: Nx3 => flatten to [x0,y0,z0, x1,y1,z1, ...]
    points_array = mesh.points.ravel().tolist()

    # mesh.celltypes: each cell's VTK type
    cell_types_list = mesh.celltypes.tolist()

    # mesh.cells: [nPts, id0, id1, ..., nPts, id0, ...]
    # We must skip the "nPts" integers to build a flat connectivity array
    all_cells = mesh.cells
    connectivity = []
    i = 0
    while i < len(all_cells):
        npts = all_cells[i]
        cell_pt_ids = all_cells[i+1: i+1+npts]
        connectivity.extend(cell_pt_ids)
        i += 1 + npts

    # 3) Build dash_vtk.UnstructuredGrid
    dash_grid = dash_vtk.UnstructuredGrid(
        points=points_array,
        connectivity=connectivity,
        cellTypes=cell_types_list
    )

    # 4) Wrap in a GeometryRepresentation
    return dash_vtk.GeometryRepresentation(
        children=[dash_grid],
        colorMapPreset="Cool to Warm",
        showScalarBar=False
    )


app.layout = html.Div([
    html.H1("Dash VTK + PyVista (.vtu) Example"),

    html.Label("Resolution:"),
    dcc.Input(id="resolution-input", type="number", value=20),
    html.Button("Generate VTU", id="gen-button", n_clicks=0),
    html.Div(id="status-div", style={"marginBottom": "20px"}),

    dash_vtk.View(
        id="vtk-view",
        style={"width": "600px", "height": "400px"},
        children=[]
    ),
])


@app.callback(
    Output("vtk-view", "children"),
    Output("status-div", "children"),
    Input("gen-button", "n_clicks"),
    State("resolution-input", "value"),
    prevent_initial_call=True
)
def on_generate_vtu(n_clicks, resolution):
    """
    1) POST to /generate_vtu with 'resolution' 
    2) backend writes my_sphere.vtu -> shared_data 
    3) Read that file in PyVista, parse -> dash_vtk geometry
    """
    try:
        # 1) POST to backend
        resp = requests.post(
            f"{BACKEND_URL}/generate_vtu",
            json={"resolution": resolution},
            timeout=10
        )
        resp.raise_for_status()
        data = resp.json()
        fname = data.get("filename", "")
        if not fname:
            return [], "No filename returned from backend"

        # 2) Load .vtu with PyVista
        dash_geom = load_vtu_with_pyvista(fname)
        return [dash_geom], f"Generated {fname} with resolution={resolution}"

    except Exception as e:
        return [], f"Error: {str(e)}"


if __name__ == "__main__":
    app.run_server(host="0.0.0.0", port=8050, debug=True)
