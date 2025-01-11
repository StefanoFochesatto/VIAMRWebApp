import streamlit as st
import requests
import os
import pyvista as pv
from pyvista import get_reader
from stpyvista import stpyvista
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

pv.start_xvfb()
API_URL = "http://backend:5000"


def init_session_state():
    if "solving" not in st.session_state:
        st.session_state.solving = False
    if "error" not in st.session_state:
        st.session_state.error = None


def solve_problem(params):
    try:
        logger.info("Starting solve request with params:", params)
        st.session_state.solving = True
        st.session_state.error = None

        with st.spinner("Solving problem..."):
            response = requests.post(f"{API_URL}/solve", json=params)
            response.raise_for_status()
            result = response.json()
            logger.info("Received response:", result)

            st.session_state.generated_files = result.get("files", [])
            logger.info("Updated session state with files:",
                        st.session_state.generated_files)
            st.session_state.solving = False
            return True
    except requests.exceptions.RequestException as e:
        logger.error("Request error:", e)
        st.session_state.error = f"Error communicating with backend: {str(e)}"
        if hasattr(e.response, 'json'):
            try:
                error_details = e.response.json()
                st.session_state.error += f"\nDetails: {error_details.get('error', '')}"
            except:
                pass
    except Exception as e:
        logger.error("Unexpected error:", e)
        st.session_state.error = f"Unexpected error: {str(e)}"

    st.session_state.solving = False
    return False


def main():
    st.set_page_config(layout="wide", page_title="Obstacle Problem Solver")
    init_session_state()

    st.title("Obstacle Problem Solver with AMR")

    # Sidebar for parameters
    with st.sidebar:
        st.title("Adaptation Parameters")

        problem = st.selectbox("Select Problem Type:",
                               options=["Sphere", "Spiral"])

        initTriHeight = st.number_input(
            "Initial Triangle Height:",
            min_value=0.1,
            max_value=1.0,
            value=0.45,
            step=0.05,
        )

        max_iterations = st.number_input(
            "Max Number of Iterations:",
            min_value=1,
            max_value=10,
            value=1,
            step=1,
        )

        RefinementMethod = st.selectbox(
            "Refinement Method:",
            options=["VCES", "UDO"]
        )

        bracket = None
        neighbors = None

        if RefinementMethod == "VCES":
            col1, col2 = st.columns(2)
            with col1:
                vceslower = st.number_input(
                    "Lower Bound",
                    min_value=0.0,
                    max_value=0.5,
                    value=0.45,
                    step=0.01
                )
            with col2:
                vcesupper = st.number_input(
                    "Upper Bound",
                    min_value=0.5,
                    max_value=1.0,
                    value=0.65,
                    step=0.01
                )
            bracket = [vceslower, vcesupper]

        if RefinementMethod == "UDO":
            neighbors = st.number_input(
                "UDO Neighborhood Depth:",
                min_value=1,
                max_value=5,
                value=3,
                step=1,
            )

        solve_button = st.button(
            "Solve",
            disabled=st.session_state.solving
        )

    # Main area
    if solve_button:
        payload = {
            "max_iterations": max_iterations,
            "problem": problem,
            "initTriHeight": initTriHeight,
            "RefinementMethod": RefinementMethod,
            "bracket": bracket,
            "neighbors": neighbors
        }
        logger.info("Initiating solve with payload:", payload)
        solve_problem(payload)

    if st.session_state.error:
        st.error(st.session_state.error)

    if st.session_state.get("generated_files"):
        logger.info("Found files in session state:",
                    st.session_state.generated_files)
        pvd_files = st.session_state.generated_files

        if pvd_files:
            logger.info("Available PVD files:", pvd_files)
            iteration_to_view = st.selectbox(
                "Select Iteration to View:",
                options=pvd_files
            )

        if iteration_to_view:
            try:
                file_path = os.path.join("/app/storage", iteration_to_view)
                logger.info(f"Attempting to read file: {file_path}")
                reader = get_reader(file_path)
                reader.set_active_time_point(0)
                mesh = reader.read()[0]

                # Check if mesh is valid
                if mesh.n_points == 0:
                    raise ValueError("Loaded mesh contains no points")

                mesh.set_active_scalars("solution")
                warped_mesh = mesh.warp_by_scalar(factor=3)

                # Configure plotter with specific window size and camera position
                plotter = pv.Plotter(window_size=[800, 600])
                plotter.camera_position = [
                    (4, 4, 6), (0, 0, 0), (0, 0, 1)]  # Fixed camera view

                plotter.add_mesh(
                    warped_mesh,
                    scalars="solution",
                    cmap="viridis",
                    show_edges=True,
                    lighting=True  # Enable lighting for better 3D visualization
                )

                # Add a bounding box for reference
                plotter.add_bounding_box()

                # Render with specific theme
                stpyvista(
                    plotter,
                    key=f"plot_{iteration_to_view}",
                    use_container_width=True,
                    theme="document"
                )
                logger.info("Successfully displayed plot")
            except Exception as e:
                logger.error(
                    f"Error displaying solution: {str(e)}", exc_info=True)
                st.error(f"Error displaying solution: {str(e)}")


if __name__ == "__main__":
    main()
