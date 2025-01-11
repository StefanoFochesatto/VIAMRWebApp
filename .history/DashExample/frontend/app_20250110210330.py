import dash
from dash import dcc, html, Input, Output, State
import requests
import vtk
import dash_vtk
import os

app = dash.Dash(__name__)
server = app.server

# The backend is "http://backend:5000" inside Docker Compose
BACKEND_URL = "http://backend:5000"

# Our shared data directory (mounted read-only)
DATA_DIR = "/app/shared_data"


def read_vtu_from_disk(filename):
    """
    Use native Python VTK to load a .vtu file, return a vtkUnstructuredGrid.
    """
    fullpath = os.path.join(DATA_DIR, filename)
    if not os.path.exists(fullpath):
        raise FileNotFoundError(f"File {fullpath} not found.")

    reader = vtk.vtkXMLUnstructuredGridReader()
    reader.SetFileName(fullpath)
    reader.Update()
    return reader.GetOutput()  # vtkUnstructuredGrid


def vtk_to_dash_vtk(ugrid):
    """
    Convert a vtkUnstructuredGrid -> dash_vtk.UnstructuredGrid for server-side rendering.
    """
    points_vtk = ugrid.GetPoints()
    num_points = points_vtk.GetNumberOfPoints()
    coords = []
    for i in range(num_points):
        x, y, z = points_vtk.GetPoint(i)
        coords.extend([x, y, z])

    cell_array = ugrid.GetCells()
    cell_locations = ugrid.GetCellLocationsArray()
    cell_types_arr = ugrid.GetCellTypesArray()

    num_cells = ugrid.GetNumberOfCells()
    connectivity = []
    cell_types = []
    for cid in range(num_cells):
        ctype = cell_types_arr.GetValue(cid)
        cell_types.append(ctype)
        offset = cell_locations.GetValue(cid)
        npts = cell_array.GetValue(offset)
        for k in range(npts):
            pid = cell_array.GetValue(offset + 1 + k)
            connectivity.append(pid)

    dash_grid = dash_vtk.UnstructuredGrid(
        points=coords,
        connectivity=connectivity,
        cellTypes=cell_types
    )

    return dash_vtk.GeometryRepresentation(
        children=[dash_grid],
        colorMapPreset="Cool to Warm",
    )


app.layout = html.Div([
    html.H1("Dash VTK + VTK Server-Side (.vtu) Example"),

    html.Div([
        html.Label("Resolution:"),
        dcc.Input(id="resolution-input", type="number", value=20),
        html.Button("Generate .vtu", id="gen-button", n_clicks=0),
    ], style={"marginBottom": "20px"}),

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
    1) Post 'resolution' to backend /generate_vtu
    2) Backend writes my_sphere.vtu to /app/shared_data
    3) Read my_sphere.vtu from disk here, convert to dash_vtk, display
    """
    try:
        # 1) Call backend
        resp = requests.post(f"{BACKEND_URL}/generate_vtu",
                             json={"resolution": resolution}, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        fname = data.get("filename", "")
        if not fname:
            return [], "No filename returned by backend."

        # 2) Read .vtu from shared_data
        ugrid = read_vtu_from_disk(fname)

        # 3) Convert to dash_vtk
        dash_geom = vtk_to_dash_vtk(ugrid)
        return [dash_geom], f"Generated {fname} at resolution={resolution}"
    except Exception as e:
        return [], f"Error: {str(e)}"


if __name__ == "__main__":
    app.run_server(host="0.0.0.0", port=8050, debug=True)
