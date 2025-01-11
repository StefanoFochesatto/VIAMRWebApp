from trame.app import get_server
from trame.widgets import vuetify, vtk as vtk_widgets
from trame.ui.vuetify import SinglePageLayout

from vtkmodules.vtkFiltersSources import vtkConeSource
from vtkmodules.vtkRenderingCore import (
    vtkRenderer,
    vtkRenderWindow,
    vtkRenderWindowInteractor,
    vtkPolyDataMapper,
    vtkActor,
)

# VTK factory initialization
from vtkmodules.vtkInteractionStyle import vtkInteractorStyleSwitch  # noqa
import vtkmodules.vtkRenderingOpenGL2  # noqa


from firedrake import *
from firedrake.output import VTKFile
from viamr import VIAMR
from pyvista.trame.ui import plotter_ui
from viamr.utility import SphereObstacleProblem
from viamr.utility import SpiralObstacleProblem

import pyvista as pv


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
        u.rename('test')
        solutions.append(u)

        # Refine mesh for next iteration
        mesh = mesh.refine_marked_elements(mark)
        mesh_history.append(mesh)

    print('Finished Calculations')
    return solutions, mesh_history


solutions, mesh_history = solve_problem_cached(
    1, "Sphere", 0.3, "VCES", bracket=[0.2, 0.8])

VTKFile('test.pvd').write(solutions[0])


# Read the PVD file
reader = pv.get_reader('test.pvd')
# List available time values
print(reader.time_values)
# Select the active time point
reader.set_active_time_point(0)

# Load the mesh with associated field data
mesh = reader.read()[0]

# Check available fields on the mesh (e.g., to verify your function's presence)
print(mesh.array_names)  # Available field/scalar names

# Ensure specific scalar data is the active scalar
# Replace with the correct field or function name
scalar_name = 'test'
mesh.set_active_scalars(scalar_name)

# Warp the mesh by the active scalar field
# Adjust the factor as needed to scale the warping
warped_mesh = mesh.warp_by_scalar(factor=3)


# Initialize plotter
pl = pv.Plotter()

# Add the mesh, coloring by the active scalar function
pl.add_mesh(warped_mesh, scalars=scalar_name,
            cmap='viridis', show_edges=True)

# Optionally adjust plot settings
# Add a scalar bar with a title
pl.add_scalar_bar(title=scalar_name, n_labels=5)

pl.add_title("Mesh with Scalar Field")
pl.camera_position = 'xy'  # Customize as needed

# Render the plot


# -----------------------------------------------------------------------------
# Trame initialization
# -----------------------------------------------------------------------------

server = get_server(client_type="vue2")
state, ctrl = server.state, server.controller

state.trame__title = "VTK Remote rendering"

# -----------------------------------------------------------------------------
# VTK code
# -----------------------------------------------------------------------------

DEFAULT_RESOLUTION = 6

renderer = vtkRenderer()
renderWindow = vtkRenderWindow()
renderWindow.AddRenderer(renderer)
renderWindow.OffScreenRenderingOn()

renderWindowInteractor = vtkRenderWindowInteractor()
renderWindowInteractor.SetRenderWindow(renderWindow)
renderWindowInteractor.GetInteractorStyle().SetCurrentStyleToTrackballCamera()

cone_source = vtkConeSource()
mapper = vtkPolyDataMapper()
actor = vtkActor()
mapper.SetInputConnection(cone_source.GetOutputPort())
actor.SetMapper(mapper)
renderer.AddActor(actor)
renderer.ResetCamera()
renderWindow.Render()


@state.change("resolution")
def update_cone(resolution=DEFAULT_RESOLUTION, **kwargs):
    cone_source.SetResolution(resolution)
    ctrl.view_update()


def update_reset_resolution():
    state.resolution = DEFAULT_RESOLUTION


# -----------------------------------------------------------------------------
# GUI
# -----------------------------------------------------------------------------

with SinglePageLayout(server) as layout:
    layout.icon.click = ctrl.view_reset_camera
    layout.title.set_text("Cone Application")

    with layout.toolbar:
        vuetify.VSpacer()
        vuetify.VSlider(
            v_model=("resolution", DEFAULT_RESOLUTION),
            min=3,
            max=60,
            step=1,
            hide_details=True,
            dense=True,
            style="max-width: 300px",
        )
        vuetify.VDivider(vertical=True, classes="mx-2")
        with vuetify.VBtn(icon=True, click=update_reset_resolution):
            vuetify.VIcon("mdi-undo-variant")

    with layout.content:
        with vuetify.VContainer(
            fluid=True,
            classes="pa-0 fill-height",
        ):
            view = plotter_ui(pl)

            ctrl.view_update = view.update
            ctrl.view_reset_camera = view.reset_camera

# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------

if __name__ == "__main__":
    server.start()
