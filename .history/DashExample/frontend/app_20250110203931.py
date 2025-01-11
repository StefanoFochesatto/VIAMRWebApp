import dash
from dash import dcc, html, Input, Output, State
import requests
import dash_vtk

app = dash.Dash(__name__)
server = app.server

# In Docker Compose, use "http://backend:5000"
# For local dev without Compose, might be "http://127.0.0.1:5000"
BACKEND_URL = "http://backend:5000"

app.layout = html.Div([
    html.H1("Dash VTK + PyVista (.vtu) Example (Client-Side Reader)"),

    # User input for 'resolution'
    html.Label("Resolution:"),
    dcc.Input(id="input-resolution", type="number", value=20),

    html.Button("Generate VTU Mesh", id="generate-mesh-btn", n_clicks=0),
    html.Br(), html.Br(),

    # Status/feedback
    html.Div(id="status-div", style={"marginBottom": "20px"}),

    # Store the filename returned by the backend
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
    1) POST the resolution to /generate_vtu on the backend.
    2) The backend generates my_sphere.vtu and returns its filename.
    3) Store that filename in a dcc.Store and show status in the UI.
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
        return "", f"Error generating mesh: {str(e)}"


@app.callback(
    Output("vtk-geometry", "children"),
    Input("vtu-filename-store", "data")
)
def update_vtk_reader(filename):
    """
    Once we have the .vtu filename, we create a dash_vtk.Reader
    that fetches the .vtu file from /data/<filename>.
    This is a client-side parse of the .vtu using vtk.js.
    """
    if filename:
        file_url = f"{BACKEND_URL}/data/{filename}"
        return [
            # The new usage: dash_vtk.Reader with a .vtu
            dash_vtk.Reader(
                vtkClass="vtkXMLUnstructuredGridReader",
                url=file_url,
                resetCameraOnUpdate=True,
                renderOnUpdate=True
            )
        ]
    return []


if __name__ == "__main__":
    # For local debugging. In production, set up a WSGI server or similar.
    app.run_server(host="0.0.0.0", port=8050, debug=True)
