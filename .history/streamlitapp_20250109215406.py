import streamlit as st
import viskex
import viskex.firedrake_plotter
from stpyvista import stpyvista
from firedrake import *
from viamr import VIAMR
from viamr.utility import SphereObstacleProblem
from viamr.utility import SpiralObstacleProblem


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
        mesh_history = [problem_instance.setInitialMesh()]

    elif problem == "Spiral":
        problem_instance = SpiralObstacleProblem(TriHeight=initTriHeight)
        mesh_history = [problem_instance.setInitialMesh()]

    amr_instance = VIAMR()
    solutions = []
    u = None

    for i in range(max_iterations):
        mesh = mesh_history[i]
        # Solve PDE on current mesh with initial guess u
        u, lb = problem_instance.solveProblem(mesh=mesh_history[i], u=u)

        if RefinementMethod == "UDO":
            mark = amr_instance.udomark(mesh, u, lb, n=neighbors)
        elif RefinementMethod == "VCES":
            mark = amr_instance.vcesmark(mesh, u, lb, bracket)

        # Store the solution and the mark function for this iteration
        solutions.append(u)

        # Refine mesh for next iteration
        mesh = mesh.refine_marked_elements(mark)
        mesh_history.append(mesh)

    print('Finished Calculations')
    return solutions, mesh_history

# Run precomputation on app start if not already cached


@st.cache_resource
def precompute():
    # Precompute with specific parameters
    return solve_problem_cached(2, "Sphere", 0.3, "VCES", bracket=[0.2, 0.8])


# Precompute and store results in session state
if "precomputed_solutions" not in st.session_state or "precomputed_marks" not in st.session_state:
    precomp_sols, precomp_marks = precompute()
    st.session_state.precomputed_solutions = precomp_sols
    st.session_state.precomputed_marks = precomp_marks


# ------------------------------------------------------------------
# SIDEBAR
# ------------------------------------------------------------------
with st.sidebar:
    st.title("Adaptation Parameters")

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
            min_value=0.5,
            max_value=1.0,
            value=0.65,
            step=0.01
        )
        vceslower = st.slider(
            "VCES Lower Bound:",
            min_value=0.0,
            max_value=0.5,
            value=0.45,
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
st.title("Obstacle Problem Solver with AMR")

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
    print("Generating Scalar Plotter Object")
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

    print("Generating stpyvista scalar")
    st.subheader("Solution")
    stpyvista(
        sol_plotter,
        use_container_width=True,
        key=f"solution_plot_{iteration_to_view}"
    )

    # -----------------------------------------
    # Plot the mark function
    # -----------------------------------------
    print("Generating Marking Plotter Object")

    mark_plotter = viskex.firedrake_plotter.FiredrakePlotter.plot_mesh(
        current_mark
    )
    # Match the same camera as the solution, if desired
    mark_plotter.camera_position = sol_plotter.camera_position

    print("Generating stpyvista marking")
    st.subheader("Mesh")
    stpyvista(
        mark_plotter,
        use_container_width=True,
        key=f"mark_plot_{iteration_to_view}"
    )
