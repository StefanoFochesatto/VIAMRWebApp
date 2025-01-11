from pyvista import examples
import streamlit as st
from stpyvista import stpyvista
from firedrake import *
from firedrake.output import VTKFile
from viamr import VIAMR
from viamr.utility import SphereObstacleProblem
from viamr.utility import SpiralObstacleProblem
import threading
from time import sleep
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
        solutions.append(u)

        # Refine mesh for next iteration
        mesh = mesh.refine_marked_elements(mark)
        mesh_history.append(mesh)

    print('Finished Calculations')
    return solutions, mesh_history


solutions, mesh_history = solve_problem_cached(
    1, "Sphere", 0.3, "VCES", bracket=[0.2, 0.8])

VTKFile('test.pvd').write(solutions[0])


reader = pv.get_reader('test.pvd')

reader.time_values


reader.set_active_time_point(0)

mesh = reader.read()[0]
