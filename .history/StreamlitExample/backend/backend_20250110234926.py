from firedrake.output import VTKFile
from firedrake import *
from viamr.utility import SphereObstacleProblem, SpiralObstacleProblem
from viamr import VIAMR
from flask import Flask, request, jsonify
import os

app = Flask(__name__)
STORAGE_PATH = "/app/storage"


@app.route("/solve", methods=["POST"])
def solve_problem():
    data = request.json
    max_iterations = data.get("max_iterations", 1)
    problem_type = data.get("problem", "Sphere")
    initTriHeight = data.get("initTriHeight", 0.3)
    RefinementMethod = data.get("RefinementMethod", "VCES")
    bracket = data.get("bracket", [0.2, 0.8])
    neighbors = data.get("neighbors", 3)

    if not os.path.exists(STORAGE_PATH):
        os.makedirs(STORAGE_PATH)

    if problem_type == "Sphere":
        problem_instance = SphereObstacleProblem(TriHeight=initTriHeight)
        mesh_history = [problem_instance.setInitialMesh()]
    elif problem_type == "Spiral":
        problem_instance = SpiralObstacleProblem(TriHeight=initTriHeight)
        mesh_history = [problem_instance.setInitialMesh()]

    amr_instance = VIAMR()
    solutions = []
    u = None

    for i in range(max_iterations):
        mesh = mesh_history[i]
        u, lb = problem_instance.solveProblem(mesh=mesh, u=u)
        u.rename('solution')
        if RefinementMethod == "UDO":
            mark = amr_instance.udomark(mesh, u, lb, n=neighbors)
        elif RefinementMethod == "VCES":
            mark = amr_instance.vcesmark(mesh, u, lb, bracket)

        solutions.append(u)
        mesh = mesh.refine_marked_elements(mark)
        mesh_history.append(mesh)

        output_file = os.path.join(STORAGE_PATH, f"solution_{i}.pvd")
        VTKFile(output_file).write(u)

    return jsonify({"message": "Solutions generated", "files": os.listdir(STORAGE_PATH)})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
