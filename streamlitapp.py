import streamlit as st
import viskex
import viskex.firedrake_plotter
from stpyvista import stpyvista
from firedrake import *
from viamr import VIAMR
from viamr.utility import SphereObstacleProblem
# from viamr.utility import SpiralObstacleProblem


# Use wide layout
st.set_page_config(layout="wide")


def solve_problem_cached(max_iterations, problem, initTriHeight, RefinementMethod, bracket=None, neighbors=None):
    """
    Solve the PDE up to `max_iterations` times, refining each time.
    Return two lists:
      - solutions[i]: Firedrake solution at iteration i
      - marks[i]: Firedrake function (CG1) that represents the refinement mark
    """
    # Pick which problem to instantiate
    if problem == "Sphere":
        problem_instance = SphereObstacleProblem(TriHeight=initTriHeight)
    # elif problem == "Spiral":
    #     problem_instance = SpiralObstacleProblem(TriHeight=initTriHeight)

    amr_instance = VIAMR()
    mesh_history = [None]
    solutions = []
    marks = []
    u = None

    for i in range(max_iterations):
        # Solve PDE on current mesh with initial guess u
        u, lb, mesh = problem_instance.solveProblem(mesh=mesh_history[i], u=u)

        # Mark elements for refinement
        CG1, _ = amr_instance.spaces(mesh)
        if RefinementMethod == "UDO":
            mark = amr_instance.udomark(mesh, u, lb, n=neighbors)
        elif RefinementMethod == "VCES":
            mark = amr_instance.vcesmark(mesh, u, lb, bracket)

        # Store the solution and the mark function for this iteration
        solutions.append(u)
        # viskex doesn't plot dg0
        marks.append(Function(CG1).interpolate(mark))

        # Refine mesh for next iteration
        mesh = mesh.refine_marked_elements(mark)
        mesh_history.append(mesh)

    return solutions, marks


# ------------------------------------------------------------------
# SIDEBAR
# ------------------------------------------------------------------
with st.sidebar:
    st.title("Simulation Parameters")

    problem = st.selectbox(
        "Select Problem Type:",
        options=["Sphere", "Spiral"]
    )

    initTriHeight = st.number_input(
        "Initial Triangle Height:",
        min_value=.1,
        value=.45,
        step=.05
    )

    max_iterations = st.number_input(
        "Max Number of Iterations:",
        min_value=1,
        value=1,
        step=1
    )

    RefinementMethod = st.selectbox(
        "Refinement Method:",
        options=["VCES", "UDO"]
    )

    bracket = None
    neighbors = None

    if RefinementMethod == "VCES":
        vcesupper = st.slider(
            "VCES Upper Bound:",
            min_value=0.0,
            max_value=1.0,
            value=0.5,
            step=0.01
        )
        vceslower = st.slider(
            "VCES Lower Bound:",
            min_value=0.0,
            max_value=1.0,
            value=0.5,
            step=0.01
        )
        bracket = [vceslower, vcesupper]

    if RefinementMethod == "UDO":
        neighbors = st.number_input(
            "UDO Neighborhood Depth:",
            min_value=1,
            value=3,
            step=1
        )

    # Button to solve and store solutions in session state
    if st.button("Solve"):
        sols, mrks = solve_problem_cached(
            max_iterations, problem, initTriHeight, RefinementMethod, bracket, neighbors
        )
        st.session_state.solutions = sols
        st.session_state.marks = mrks

# Initialize session_state variables if they don't exist yet
if "solutions" not in st.session_state:
    st.session_state.solutions = []
if "marks" not in st.session_state:
    st.session_state.marks = []

# ------------------------------------------------------------------
# MAIN AREA
# ------------------------------------------------------------------
st.title("Firedrake Solution Solver")

if st.session_state.solutions and st.session_state.marks:
    solutions = st.session_state.solutions
    marks = st.session_state.marks

    # Both lists should have the same length
    num_solutions = len(solutions)

    iteration_to_view = st.selectbox(
        "Select Iteration to View:",
        options=list(range(num_solutions)),
        index=0
    )

    # Retrieve the chosen iteration's solution and mark
    current_solution = solutions[iteration_to_view]
    current_mark = marks[iteration_to_view]

    # -----------------------------------------
    # Plot the solution
    # -----------------------------------------
    sol_plotter = viskex.firedrake_plotter.FiredrakePlotter.plot_scalar_field(
        current_solution,
        "Solution",
        warp_factor=0.5,
    )
    sol_plotter.camera_position = [
        (4, 4, 6),   # camera position
        (0, 0, 0),   # focal point
        (0, 0, 1),   # up direction
    ]

    st.subheader("Solution")
    stpyvista(
        sol_plotter,
        use_container_width=True,
        key=f"solution_plot_{iteration_to_view}"
    )

    # -----------------------------------------
    # Plot the mark function
    # -----------------------------------------
    mark_plotter = viskex.firedrake_plotter.FiredrakePlotter.plot_scalar_field(
        current_mark,
        "Refinement Mark",
        warp_factor=0.5,  # Typically you'd want no warping or very small warping
    )
    # Match the same camera as the solution, if desired
    mark_plotter.camera_position = sol_plotter.camera_position

    st.subheader("Mark Function")
    stpyvista(
        mark_plotter,
        use_container_width=True,
        key=f"mark_plot_{iteration_to_view}"
    )
