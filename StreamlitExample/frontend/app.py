import streamlit as st
import requests
import os
import pyvista as pv
from pyvista import get_reader
from stpyvista import stpyvista
pv.start_xvfb()

API_URL = "http://backend:5000"

st.set_page_config(layout="wide")

st.title("Obstacle Problem Solver with AMR")

# Sidebar
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
        payload = {
            "max_iterations": max_iterations,
            "problem": problem,
            "initTriHeight": initTriHeight,
            "RefinementMethod": RefinementMethod,
            "bracket": bracket,
            "neighbors": neighbors
        }
        response = requests.post(f"{API_URL}/solve", json=payload)
        st.session_state.generated_files = response.json().get("files", [])

# Main area
if "generated_files" in st.session_state and st.session_state.generated_files:
    files = st.session_state.generated_files
    iteration_to_view = st.selectbox(
        "Select Iteration to View:", options=files)

    if iteration_to_view:
        file_path = os.path.join("/app/storage", iteration_to_view)
        reader = get_reader(file_path)
        reader.set_active_time_point(0)
        mesh = reader.read()[0]

        mesh.set_active_scalars("solution")
        warped_mesh = mesh.warp_by_scalar(factor=3)

        plotter = pv.Plotter()
        plotter.add_mesh(warped_mesh, scalars="solution",
                         cmap="viridis", show_edges=True)
        stpyvista(plotter, use_container_width=True)
