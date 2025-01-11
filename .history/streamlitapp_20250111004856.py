import streamlit as st
import viskex
import viskex.firedrake_plotter
from stpyvista import stpyvista
from firedrake import *
from viamr import VIAMR
from viamr.utility import SphereObstacleProblem, SpiralObstacleProblem
import pyvista as pv
pv.start_xvfb()


# Use wide layout
st.set_page_config(layout="wide")


def solve_problem_cached(max_iterations, problem, initTriHeight, RefinementMethod, bracket=None, neighbors=None):
    """
    Solve the PDE up to `max_iterations` times, refining each time.
    Return pre-configured plotter objects for solutions and marks.
    """

    if problem == "Sphere":
        problem_instance = SphereObstacleProblem(TriHeight=initTriHeight)
        mesh_history = [problem_instance.setInitialMesh()]
    elif problem == "Spiral":
        problem_instance = SpiralObstacleProblem(TriHeight=initTriHeight)
        mesh_history = [problem_instance.setInitialMesh()]

    amr_instance = VIAMR()
    solutions = []
    marks = []
    u = None

    for i in range(max_iterations):
        mesh = mesh_history[i]
        u, lb = problem_instance.solveProblem(mesh=mesh_history[i], u=u)

        if RefinementMethod == "UDO":
            mark = amr_instance.udomark(mesh, u, lb, n=neighbors)
        elif RefinementMethod == "VCES":
            mark = amr_instance.vcesmark(mesh, u, lb, bracket)

        solutions.append(u)
        marks.append(mark)
        mesh = mesh.refine_marked_elements(mark)
        mesh_history.append(mesh)

    # Pre-configure plotters
    camera_position = [(4, 4, 6), (0, 0, 0), (0, 0, 1)]

    solution_plotters = []
    for u in solutions:
        plotter = viskex.firedrake_plotter.FiredrakePlotter.plot_scalar_field(
            u, "Solution", warp_factor=0.5)
        plotter.camera_position = camera_position
        solution_plotters.append(plotter)

    mark_plotters = []
    for mesh in mesh_history:
        plotter = viskex.firedrake_plotter.FiredrakePlotter.plot_mesh(mesh)
        plotter.camera_position = camera_position
        mark_plotters.append(plotter)

    print('Finished Calculations')
    return solution_plotters, mark_plotters


@st.cache_resource
def precompute():
    return solve_problem_cached(2, "Sphere", 0.3, "VCES", bracket=[0.2, 0.8])

# Sidebar and UI elements


if "solutions" not in st.session_state:
    st.session_state.solutions = []
if "marks" not in st.session_state:
    st.session_state.marks = []

with st.sidebar:
    st.title("Adaptation Parameters")

    problem = st.selectbox("Select Problem Type:",
                           options=["Sphere", "Spiral"])
    initTriHeight = st.number_input(
        "Initial Triangle Height:", min_value=.1, value=.45, step=.05)
    max_iterations = st.number_input(
        "Max Number of Iterations:", min_value=1, value=1, step=1)
    RefinementMethod = st.selectbox(
        "Refinement Method:", options=["VCES", "UDO"])

    bracket = None
    neighbors = None

    if RefinementMethod == "VCES":
        vcesupper = st.slider("VCES Upper Bound:", min_value=0.5,
                              max_value=1.0, value=0.65, step=0.01)
        vceslower = st.slider("VCES Lower Bound:", min_value=0.0,
                              max_value=0.5, value=0.45, step=0.01)
        bracket = [vceslower, vcesupper]

    if RefinementMethod == "UDO":
        neighbors = st.number_input(
            "UDO Neighborhood Depth:", min_value=1, value=3, step=1)

    if st.button("Solve"):
        solution_plotters, mark_plotters = solve_problem_cached(
            max_iterations, problem, initTriHeight, RefinementMethod, bracket, neighbors
        )
        st.session_state.solutions = solution_plotters
        st.session_state.marks = mark_plotters

# Main Area
st.title("Obstacle Problem Solver with AMR")

if st.session_state.solutions and st.session_state.marks:

    solutions = st.session_state.solutions
    marks = st.session_state.marks

    num_solutions = len(solutions)
    iteration_to_view = st.selectbox(
        "Select Iteration to View:", options=list(range(num_solutions)), index=0)

    st.subheader("Solution")
    stpyvista(solutions[iteration_to_view], use_container_width=True,
              key=f"solution_plot_{iteration_to_view}")

    st.subheader("Mesh")
    stpyvista(marks[iteration_to_view], use_container_width=True,
              key=f"mark_plot_{iteration_to_view}")
