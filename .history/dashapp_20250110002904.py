# app.py
import dash
from dash import dcc, html
from dash.dependencies import Input, Output, State
import dash_bootstrap_components as dbc
import dash_vtk
import base64
import os
import random
import shutil

# VTK reading
import vtk
from vtk import vtkXMLUnstructuredGridReader

# Import your Firedrake solver logic
from solver import solve_problem_cached
from firedrake import File  # For writing .pvd/.vtu

app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])

# We’ll store solutions (as .vtu file paths, for instance) in a hidden dcc.Store
# or store the raw base64 data for each iteration. We'll do .vtu approach here.

app.layout = dbc.Container(fluid=True, children=[
    dbc.Row([
        dbc.Col([
            html.H3("Adaptation Parameters"),
            dbc.Label("Problem:"),
            dcc.Dropdown(
                id="problem-dropdown",
                options=[
                    {"label": "Sphere", "value": "Sphere"},
                    {"label": "Spiral", "value": "Spiral"},
                ],
                value="Sphere",
            ),
            dbc.Label("Initial Triangle Height:"),
            dcc.Input(
                id="initTriHeight",
                type="number",
                min=0.1,
                step=0.05,
                value=0.45,
            ),
            dbc.Label("Max Iterations:"),
            dcc.Input(
                id="max_iterations",
                type="number",
                min=1,
                step=1,
                value=1,
            ),
            dbc.Label("Refinement Method:"),
            dcc.Dropdown(
                id="refinement-method",
                options=[
                    {"label": "VCES", "value": "VCES"},
                    {"label": "UDO", "value": "UDO"},
                ],
                value="VCES",
            ),
            html.Div(id="vces-range-container", children=[
                dbc.Label("VCES Lower Bound:"),
                dcc.Slider(
                    id="vces-lower",
                    min=0.0,
                    max=0.5,
                    step=0.01,
                    value=0.45,
                ),
                dbc.Label("VCES Upper Bound:"),
                dcc.Slider(
                    id="vces-upper",
                    min=0.5,
                    max=1.0,
                    step=0.01,
                    value=0.65,
                ),
            ], style={"display": "block"}),  # can hide dynamically if needed

            html.Div(id="udo-neighbor-container", children=[
                dbc.Label("UDO Neighborhood Depth:"),
                dcc.Input(
                    id="neighbors",
                    type="number",
                    min=1,
                    step=1,
                    value=3,
                )
            ], style={"display": "none"}),

            dbc.Button("Solve", id="solve-button",
                       color="primary", n_clicks=0),
        ], md=3),
        dbc.Col([
            html.H2("Obstacle Problem Solver with AMR"),
            html.Div(id="status-text", style={"marginBottom": "10px"}),

            # We store the .vtu file data or paths for each iteration
            dcc.Store(id="vtu-files", data=[]),

            # Dropdown (or slider) to pick iteration
            dbc.Label("Select Iteration:"),
            dcc.Dropdown(
                id="iteration-dropdown",
                options=[],
                value=None
            ),

            # VTK viewer
            dash_vtk.View(id="vtk-view", children=[
                dash_vtk.GeometryRepresentation([
                    dash_vtk.GeometryLoader(
                        id="geometry-loader",
                        # data prop set in a callback
                    )
                ],
                    id="geometry-rep",
                    # for instance:
                    representation="Surface With Edges",
                    colorMapPreset="erdc_rainbow_bright",
                )
            ], style={"width": "100%", "height": "80vh", "backgroundColor": "white"}),
        ], md=9),
    ])
], style={"height": "100vh"})


@app.callback(
    [Output("vces-range-container", "style"),
     Output("udo-neighbor-container", "style")],
    Input("refinement-method", "value")
)
def toggle_refinement_containers(refine_method):
    """
    Show/hide controls based on refinement method.
    """
    if refine_method == "VCES":
        return ({"display": "block"}, {"display": "none"})
    else:
        return ({"display": "none"}, {"display": "block"})


@app.callback(
    Output("vtu-files", "data"),
    Output("status-text", "children"),
    Input("solve-button", "n_clicks"),
    State("problem-dropdown", "value"),
    State("initTriHeight", "value"),
    State("max_iterations", "value"),
    State("refinement-method", "value"),
    State("vces-lower", "value"),
    State("vces-upper", "value"),
    State("neighbors", "value")
)
def run_solver(n_clicks, problem, initTriHeight, max_iterations,
               refinement_method, vces_lower, vces_upper, neighbors):
    """
    Trigger PDE solves when the user clicks "Solve".
    Store a list of .vtu filepaths (one per iteration) in vtu-files store.
    """
    if n_clicks < 1:
        return [], "Click 'Solve' to run the PDE."

    # Just to ensure a clean folder each time
    if os.path.exists("output_vtus"):
        shutil.rmtree("output_vtus")
    os.makedirs("output_vtus", exist_ok=True)

    bracket = None
    if refinement_method == "VCES":
        bracket = [vces_lower, vces_upper]

    # Solve PDE
    solutions, meshes = solve_problem_cached(
        max_iterations, problem, initTriHeight,
        refinement_method, bracket, neighbors
    )

    # Now write each solution to a .vtu file
    vtu_list = []
    for i, sol in enumerate(solutions):
        filename_base = f"output_vtus/solution_iter{i}"
        File(filename_base + ".pvd").write(sol)
        # Firedrake writes solution_iter{i}_000000.vtu by default
        # We'll reference that exact file:
        vtu_file = filename_base + "_000000.vtu"
        vtu_list.append(os.path.abspath(vtu_file))

    status = (
        f"Solved PDE with {max_iterations} iteration(s). "
        f"Found {len(vtu_list)} solutions. "
        "Select iteration below to visualize."
    )
    return vtu_list, status


@app.callback(
    Output("iteration-dropdown", "options"),
    Output("iteration-dropdown", "value"),
    Input("vtu-files", "data")
)
def populate_iteration_dropdown(vtu_list):
    """
    After solving, populate the iteration dropdown with [0..len-1].
    """
    if not vtu_list:
        return [], None
    options = [{"label": f"Iteration {i}", "value": i}
               for i in range(len(vtu_list))]
    return options, 0  # default to iteration 0


def read_vtu_as_base64(path):
    """
    Read a .vtu file from disk and return base64-encoded content.
    """
    if not os.path.exists(path):
        raise FileNotFoundError(f"{path} does not exist.")
    with open(path, "rb") as f:
        data = f.read()
    return base64.b64encode(data).decode("utf-8")


@app.callback(
    Output("geometry-loader", "data"),
    Input("iteration-dropdown", "value"),
    State("vtu-files", "data")
)
def update_geometry_loader(iter_idx, vtu_list):
    """
    When the user picks an iteration in the dropdown,
    load that iteration’s .vtu and feed it to dash_vtk.GeometryLoader.
    """
    if iter_idx is None or not vtu_list:
        return None

    vtu_file = vtu_list[iter_idx]
    encoded_data = read_vtu_as_base64(vtu_file)
    return encoded_data


if __name__ == "__main__":
    app.run_server(debug=True)
