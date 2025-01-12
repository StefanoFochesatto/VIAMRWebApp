import streamlit as st
import viskex
import viskex.firedrake_plotter
from stpyvista import stpyvista
from firedrake import *
from viamr import VIAMR
from viamr.utility import SphereObstacleProblem, SpiralObstacleProblem
import pyvista as pv
import time
pv.start_xvfb()

# Use wide layout
st.set_page_config(
    layout="wide",
    page_title="Obstacle Problem Solver",
    page_icon="🔄"
)

# Initialize session state variables
if "solutions" not in st.session_state:
    st.session_state.solutions = []
if "marks" not in st.session_state:
    st.session_state.marks = []
if "refinement_settings" not in st.session_state:
    st.session_state.refinement_settings = {
        "method": "VCES",
        "vces_upper": 0.65,
        "vces_lower": 0.45,
        "udo_neighbors": 3
    }
if "has_results" not in st.session_state:
    st.session_state.has_results = False
if "solving" not in st.session_state:
    st.session_state.solving = False


def solve_problem_cached(max_iterations, problem, initTriHeight, RefinementMethod, bracket=None, neighbors=None):
    """
    Solve the PDE up to `max_iterations` times, refining each time.
    Return pre-configured plotter objects for solutions and marks.
    """
    progress_bar = st.progress(0)
    status_text = st.empty()

    try:
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
            status_text.text(f"Solving iteration {i+1}/{max_iterations}")
            progress = (i + 1) / max_iterations
            progress_bar.progress(progress)

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

        status_text.text("Calculation completed successfully!")
        time.sleep(1)  # Give users time to see the completion message
        status_text.empty()
        progress_bar.empty()

        return solution_plotters, mark_plotters

    except Exception as e:
        status_text.error(f"An error occurred: {str(e)}")
        progress_bar.empty()
        return None, None


def clear_results():
    st.session_state.solutions = []
    st.session_state.marks = []
    st.session_state.has_results = False
    st.session_state.solving = False
    st.rerun()


# Sidebar and UI elements
with st.sidebar:
    st.title("Obstacle Problem Solver")
    st.markdown("---")

    with st.expander("📝 Problem Configuration", expanded=True):
        problem = st.selectbox(
            "Select Problem Type:",
            options=["Sphere", "Spiral"],
            help="Choose the type of obstacle problem to solve",
            disabled=st.session_state.has_results or st.session_state.solving
        )

        initTriHeight = st.number_input(
            "Initial Triangle Height:",
            min_value=0.1,
            value=0.45,
            step=0.05,
            help="Set the initial height of triangles in the mesh",
            disabled=st.session_state.has_results or st.session_state.solving
        )

        max_iterations = st.number_input(
            "Max Number of Iterations:",
            min_value=1,
            value=1,
            step=1,
            help="Maximum number of refinement iterations to perform",
            disabled=st.session_state.has_results or st.session_state.solving
        )

    with st.expander("⚙️ Refinement Settings", expanded=True):
        new_method = st.selectbox(
            "Refinement Method:",
            options=["VCES", "UDO"],
            index=0 if st.session_state.refinement_settings["method"] == "VCES" else 1,
            help="Choose the method for mesh refinement",
            disabled=st.session_state.has_results or st.session_state.solving
        )

        if st.session_state.has_results or st.session_state.solving:
            st.info("Clear results to modify parameters")

        st.session_state.refinement_settings["method"] = new_method

        if new_method == "VCES":
            vcesupper = st.slider(
                "VCES Upper Bound:",
                min_value=0.5,
                max_value=1.0,
                value=st.session_state.refinement_settings["vces_upper"],
                step=0.01,
                help="Upper bound for VCES refinement",
                disabled=st.session_state.has_results
            )
            vceslower = st.slider(
                "VCES Lower Bound:",
                min_value=0.0,
                max_value=0.5,
                value=st.session_state.refinement_settings["vces_lower"],
                step=0.01,
                help="Lower bound for VCES refinement",
                disabled=st.session_state.has_results or st.session_state.solving
            )
            st.session_state.refinement_settings["vces_upper"] = vcesupper
            st.session_state.refinement_settings["vces_lower"] = vceslower
            bracket = [vceslower, vcesupper]
            neighbors = None
        else:
            neighbors = st.number_input(
                "UDO Neighborhood Depth:",
                min_value=1,
                value=st.session_state.refinement_settings["udo_neighbors"],
                step=1,
                help="Depth of neighborhood for UDO refinement",
                disabled=st.session_state.has_results or st.session_state.solving
            )
            st.session_state.refinement_settings["udo_neighbors"] = neighbors
            bracket = None

    st.markdown("---")
    col1, col2 = st.columns([2, 1])
    with col1:
        solve_button = st.button(
            "🚀 Solve",
            help="Start the simulation with current parameters",
            use_container_width=True,
            disabled=st.session_state.has_results or st.session_state.solving
        )
    with col2:
        if st.button("🔄 Clear", help="Clear current results", use_container_width=True):
            clear_results()

    if solve_button:
        st.session_state.solving = True
        st.session_state.has_results = True
        solution_plotters, mark_plotters = solve_problem_cached(
            max_iterations, problem, initTriHeight,
            new_method, bracket, neighbors
        )
        if solution_plotters and mark_plotters:
            st.session_state.solutions = solution_plotters
            st.session_state.marks = mark_plotters
        st.session_state.solving = False
        st.rerun()


# Main Area
st.title("Visualization")

if st.session_state.solutions and st.session_state.marks:
    solutions = st.session_state.solutions
    marks = st.session_state.marks
    num_solutions = len(solutions)

    iteration_to_view = st.select_slider(
        "Iteration:",
        options=list(range(num_solutions)),
        value=0,
        help="Select which iteration to visualize"
    )

    st.info(
        f"Showing results for iteration {iteration_to_view + 1} of {num_solutions}")

    # Solution visualization
    st.subheader("Solution")
    stpyvista(solutions[iteration_to_view], use_container_width=True,
              key=f"solution_plot_{iteration_to_view}")

    # Mesh visualization
    st.subheader("Mesh")
    stpyvista(marks[iteration_to_view], use_container_width=True,
              key=f"mark_plot_{iteration_to_view}")
else:
    st.info("👈 Configure parameters and click 'Solve' to start the simulation")
