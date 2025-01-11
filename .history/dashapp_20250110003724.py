import dash
import dash_vtk
import dash_bootstrap_components as dbc
import dash_html_components as html
import dash_core_components as dcc
from dash.dependencies import Input, Output, State

import random
import json
import numpy as np
import pyvista as pv
from vtk.util.numpy_support import vtk_to_numpy

from dash_vtk.utils import presets

# Firedrake imports
import os
import shutil
from firedrake import *
from firedrake.output import VTKFile
random.seed(42)

###############################################################################
# 1) Simple PDE solver in Firedrake + Helper to load via PyVista
###############################################################################


def solve_poisson(n=20):
    """
    Solve -Delta(u) = 1 on the unit square, with u=0 on boundary.
    Returns a Firedrake Function 'u'.
    """
    mesh = UnitSquareMesh(n, n)
    V = FunctionSpace(mesh, "CG", 1)
    u = Function(V)
    v = TestFunction(V)
    f = Constant(1.0)

    # Poisson: (grad(u), grad(v)) = (f, v)
    F = dot(grad(u), grad(v))*dx - f*v*dx
    bcs = DirichletBC(V, 0.0, "on_boundary")
    solve(F == 0, u, bcs)
    return u


def firedrake_to_arrays(n=20, warp_factor=1.0, preset_file="temp.pvd"):
    """
    1) Solve PDE with mesh size 'n'.
    2) Write solution to 'temp_000000.vtu' via Firedrake File(...).
    3) Read in PyVista, warp geometry, extract points/polys/scalars
    4) Return (points, polys, values, [min_val, max_val]).
    """
    # Ensure we start fresh each time
    if os.path.exists("temp_000000.vtu"):
        os.remove("temp_000000.vtu")
    if os.path.exists("temp.pvd"):
        os.remove("temp.pvd")

    # Solve PDE in Firedrake
    u = solve_poisson(n)

    # Write to .vtu (via .pvd), e.g. "temp_000000.vtu"
    VTKFile(preset_file).write(u)
    vtu_file = "temp_000000.vtu"
    if not os.path.exists(vtu_file):
        raise RuntimeError(
            f"Could not find {vtu_file} after writing Firedrake solution.")

    # Load with PyVista
    mesh = pv.read(vtu_file)

    # Optionally warp the mesh by the solution.  If you want just a flat mesh,
    # set warp_factor = 0 or skip warp_by_scalar altogether.
    if warp_factor != 0:
        # The PDE solution is stored in mesh["u"] (the name may differ)
        # Let's rename to "scalar1of1" so we can call warp_by_scalar easily:
        if "u" in mesh.point_data:
            mesh["scalar1of1"] = mesh["u"]
        # Warp by the solution
        warped = mesh.warp_by_scalar("scalar1of1", factor=warp_factor)
        polydata = warped.extract_geometry()
    else:
        polydata = mesh.extract_geometry()

    # Extract arrays
    points = polydata.points.ravel()           # Flatten into 1D
    polys = vtk_to_numpy(polydata.GetPolys().GetData())
    # The PDE solution we want to color by is "scalar1of1" in the warped polydata:
    if "scalar1of1" in polydata.point_data:
        values = polydata.point_data["scalar1of1"]
    else:
        values = np.zeros(polydata.points.shape[0])

    min_val = np.min(values)
    max_val = np.max(values)

    return (points, polys, values, [min_val, max_val])


###############################################################################
# 2) Build Dash App
###############################################################################
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
server = app.server

# Precompute initial data
init_points, init_polys, init_values, init_range = firedrake_to_arrays(
    n=20, warp_factor=1.0)

vtk_view = dash_vtk.View(
    id="vtk-view",
    pickingModes=["hover"],
    children=[
        dash_vtk.GeometryRepresentation(
            id="vtk-representation",
            children=[
                dash_vtk.PolyData(
                    id="vtk-polydata",
                    points=init_points,
                    polys=init_polys,
                    children=[
                        dash_vtk.PointData(
                            [
                                dash_vtk.DataArray(
                                    id="vtk-array",
                                    registration="setScalars",
                                    name="solution",
                                    values=init_values,
                                )
                            ]
                        )
                    ],
                )
            ],
            colorMapPreset="erdc_blue2green_muted",
            colorDataRange=init_range,
            property={"edgeVisibility": True},
            showCubeAxes=True,
            cubeAxesStyle={"axisLabels": ["X", "Y", "U"]},
        ),
        # Optional 'picker' geometry (like in your crater example)
        dash_vtk.GeometryRepresentation(
            id="pick-rep",
            actor={"visibility": False},
            children=[
                dash_vtk.Algorithm(
                    id="pick-sphere",
                    vtkClass="vtkSphereSource",
                    state={"radius": 0.1},
                )
            ],
        ),
    ],
)

app.layout = dbc.Container(
    fluid=True,
    style={"height": "100vh"},
    children=[
        dbc.Row(
            [
                dbc.Col(
                    children=[
                        # 1) Mesh resolution slider
                        html.Label("Mesh resolution (n)"),
                        dcc.Slider(
                            id="n-slider",
                            min=5,
                            max=50,
                            step=5,
                            value=20,
                            marks={5: "5", 50: "50"},
                        ),
                        # 2) Warp factor slider
                        html.Label("Warp factor"),
                        dcc.Slider(
                            id="warp-factor",
                            min=0.0,
                            max=2.0,
                            step=0.1,
                            value=1.0,
                            marks={0.0: "0", 2.0: "2"},
                        ),
                        # 3) Color Preset
                        html.Label("Color Preset"),
                        dcc.Dropdown(
                            id="dropdown-preset",
                            options=[{"label": nm, "value": nm}
                                     for nm in presets],
                            value="erdc_rainbow_bright",
                        ),
                        # 4) Toggle Grid
                        dcc.Checklist(
                            id="toggle-cube-axes",
                            options=[
                                {"label": " Show axis grid", "value": "grid"},
                            ],
                            value=[],
                            labelStyle={"display": "inline-block"},
                            style={"marginTop": "8px"},
                        ),
                    ],
                    md=3,
                    style={"padding": "10px"},
                ),
                dbc.Col(
                    children=[
                        html.Div(
                            html.Div(vtk_view, style={
                                     "height": "100%", "width": "100%"}),
                            style={"height": "88%"},
                        ),
                        html.Pre(
                            id="tooltip",
                            style={
                                "position": "absolute",
                                "bottom": "25px",
                                "left": "25px",
                                "zIndex": 1,
                                "color": "white",
                            },
                        ),
                    ],
                    md=9,
                ),
            ],
            style={"height": "100%"},
        )
    ],
)


###############################################################################
# 3) Callbacks
###############################################################################
@app.callback(
    [
        Output("vtk-representation", "showCubeAxes"),
        Output("vtk-representation", "colorMapPreset"),
        Output("vtk-representation", "colorDataRange"),
        Output("vtk-polydata", "points"),
        Output("vtk-polydata", "polys"),
        Output("vtk-array", "values"),
        Output("vtk-view", "triggerResetCamera"),
    ],
    [
        Input("dropdown-preset", "value"),
        Input("n-slider", "value"),
        Input("warp-factor", "value"),
        Input("toggle-cube-axes", "value"),
    ],
)
def updateSolutionColorMap(color_preset, mesh_n, warp_factor, cube_axes):
    """
    Solve PDE for the given 'mesh_n', warp by 'warp_factor',
    and set colorMapPreset + showCubeAxes.
    """
    points, polys, values, color_range = firedrake_to_arrays(
        n=mesh_n,
        warp_factor=warp_factor
    )
    return [
        ("grid" in cube_axes),   # showCubeAxes
        color_preset,           # colorMapPreset
        color_range,            # colorDataRange
        points,                 # update the mesh points
        polys,                  # update the connectivity
        values,                 # update the scalar array
        random.random(),        # triggerResetCamera => forces camera reset
    ]


@app.callback(
    [
        Output("tooltip", "children"),
        Output("pick-sphere", "state"),
        Output("pick-rep", "actor"),
    ],
    [
        Input("vtk-view", "clickInfo"),
        Input("vtk-view", "hoverInfo"),
    ],
)
def onInfo(clickData, hoverData):
    """
    Mimic your crater example: show coords in bottom-left if user hovers/clicks.
    """
    info = hoverData if hoverData else clickData
    if info:
        if (
            "representationId" in info
            and info["representationId"] == "vtk-representation"
        ):
            return (
                [json.dumps(info, indent=2)],
                {"center": info["worldPosition"]},
                {"visibility": True},
            )
        return dash.no_update, dash.no_update, dash.no_update
    return [""], {}, {"visibility": False}


###############################################################################
# 4) Run
###############################################################################
if __name__ == "__main__":
    app.run_server(debug=True)
